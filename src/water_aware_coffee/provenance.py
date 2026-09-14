"""Per-row provenance schema for every measurement that enters the atlas.

One row = one measurement of one quantity at one place for one period, in the project's target
unit, with enough information to trace it back to the exact source file and to redo the conversion.

Rules:
- `value` is always in `TARGET_UNIT[quantity]` (see units.py). The original number and unit are kept
  in `original_value` / `original_unit`, and `conversion_factor` links them: value == original_value
  * conversion_factor (within float tolerance).
- `unit_assumed` is True when the source unit was ambiguous (e.g. bare "mg/L" for hardness) and the
  loader assumed "as CaCO3". Downstream code can filter or down-weight those rows.
- `value_type` says what kind of number this is: a single sample, or an aggregate the source already
  computed (mean / median / min / max) over `n_samples` samples in [period_start, period_end].
- `water_type` separates finished (treated, at-tap or leaving the plant) from source water.
  Only finished water describes what people brew with.
- `measured` is False for values the source itself marks as estimated or modeled.
"""

from __future__ import annotations

from enum import StrEnum

import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

from water_aware_coffee.units import Quantity


class ValueType(StrEnum):
    SAMPLE = "sample"  # one measured sample
    DECLARED = "declared"  # label / brand-site value; analysis date often unknown
    MEAN = "mean"
    MEDIAN = "median"
    MIN = "min"
    MAX = "max"
    TYPICAL = "typical"  # source says "typical" / "average" without defining it
    RANGE_MID = "range_mid"  # midpoint of a published range; keep min/max in notes


class WaterType(StrEnum):
    FINISHED = "finished"  # treated water as supplied (tap, distribution, plant outlet)
    SOURCE = "source"  # raw / ambient water before treatment
    BOTTLED = "bottled"  # packaged water as sold; values as declared on label or brand site
    UNKNOWN = "unknown"


class SourceType(StrEnum):
    SURFACE = "surface"
    GROUND = "ground"
    MIXED = "mixed"
    DESALINATED = "desalinated"
    UNKNOWN = "unknown"


class MeasurementSchema(pa.DataFrameModel):
    """Long-format table: one row per (place, period, quantity) measurement."""

    # --- identity of the source ---
    source_id: Series[str] = pa.Field(
        description="Short id matching docs/sources.md, e.g. 'sisagua-br'"
    )
    source_url: Series[str] = pa.Field(description="Landing or direct URL the file came from")
    source_file: Series[str] = pa.Field(description="File name under data/raw/<source_id>/")
    source_file_sha256: Series[str] = pa.Field(str_length={"min_value": 64, "max_value": 64})
    download_date: Series[pd.Timestamp] = pa.Field(coerce=True)
    source_row_locator: Series[str] = pa.Field(
        description="How to find the row again: row index, primary key, or query string"
    )
    source_license: Series[str] = pa.Field(description="License string as stated by the publisher")

    # --- where ---
    country_iso2: Series[str] = pa.Field(str_length={"min_value": 2, "max_value": 2})
    admin1: Series[str] = pa.Field(nullable=True, description="State / region / UF")
    locality: Series[str] = pa.Field(
        description="City, municipality, or supply-zone name as published"
    )
    locality_code: Series[str] = pa.Field(
        nullable=True, description="Official code if any: IBGE, FIPS, postcode district, zone id"
    )
    utility: Series[str] = pa.Field(nullable=True, description="Water company / system name")
    utility_code: Series[str] = pa.Field(nullable=True, description="PWSID, company code, etc.")
    latitude: Series[float] = pa.Field(nullable=True, ge=-90, le=90)
    longitude: Series[float] = pa.Field(nullable=True, ge=-180, le=180)

    # --- what water ---
    water_type: Series[str] = pa.Field(isin=[w.value for w in WaterType])
    source_type: Series[str] = pa.Field(isin=[s.value for s in SourceType])
    softened: Series[bool] = pa.Field(nullable=True, description="True if the utility softens")

    # --- when ---
    period_start: Series[pd.Timestamp] = pa.Field(coerce=True, nullable=True)
    period_end: Series[pd.Timestamp] = pa.Field(coerce=True, nullable=True)

    # --- what was measured ---
    quantity: Series[str] = pa.Field(isin=[q.value for q in Quantity])
    value: Series[float] = pa.Field(description="In TARGET_UNIT[quantity]")
    unit: Series[str] = pa.Field(description="Must equal TARGET_UNIT[quantity]")
    value_type: Series[str] = pa.Field(isin=[v.value for v in ValueType])
    n_samples: Series[float] = pa.Field(
        nullable=True, ge=1, description="Samples behind an aggregate"
    )
    measured: Series[bool] = pa.Field(description="False if source flags the value as estimated")
    below_detection: Series[bool] = pa.Field(
        description="True if reported as '<LOD'; value is the LOD"
    )

    # --- how it was converted ---
    original_parameter_name: Series[str] = pa.Field(description="Verbatim from the source")
    original_value: Series[float]
    original_unit: Series[str] = pa.Field(nullable=True, description="Verbatim from the source")
    conversion_factor: Series[float]
    unit_assumed: Series[bool] = pa.Field(
        description="True if the loader had to assume the 'as' basis"
    )

    notes: Series[str] = pa.Field(nullable=True)

    class Config:
        strict = True
        coerce = True

    @pa.dataframe_check
    @classmethod
    def value_matches_conversion(cls, df: pd.DataFrame) -> Series[bool]:
        expected = df["original_value"] * df["conversion_factor"]
        return Series[bool]((df["value"] - expected).abs() <= 1e-6 * expected.abs().clip(lower=1.0))

    @pa.dataframe_check
    @classmethod
    def period_ordered(cls, df: pd.DataFrame) -> Series[bool]:
        both = df["period_start"].notna() & df["period_end"].notna()
        ok = ~both | (df["period_start"] <= df["period_end"])
        return Series[bool](ok)

    @pa.dataframe_check
    @classmethod
    def ph_in_range(cls, df: pd.DataFrame) -> Series[bool]:
        is_ph = df["quantity"] == Quantity.PH.value
        return Series[bool](~is_ph | df["value"].between(0, 14))

    @pa.dataframe_check
    @classmethod
    def concentrations_nonnegative(cls, df: pd.DataFrame) -> Series[bool]:
        is_ph = df["quantity"] == Quantity.PH.value
        return Series[bool](is_ph | (df["value"] >= 0))


COLUMNS: list[str] = list(MeasurementSchema.to_schema().columns)


def validate(df: pd.DataFrame) -> pd.DataFrame:
    """Validate and coerce a measurement table.

    Raises pandera.errors.SchemaErrors listing every problem at once.
    """
    return MeasurementSchema.validate(df, lazy=True)
