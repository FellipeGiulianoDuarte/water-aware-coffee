"""Loader for the curated bottled-water table (data/external/bottled/bottled_waters_v0.csv).

Each row is one product with values as printed on the label or brand site. We emit calcium,
magnesium, sodium, pH, alkalinity (from bicarbonate in mg/L HCO3, or from a printed
"as CaCO3" alkalinity), and hardness where a single "as CaCO3" value is printed. Ranges
("18 - 200") are skipped and counted. value_type is "declared": labels report a typical
analysis, not a sample, and the analysis date is often absent.

Provenance per row: the product's source URL and the provenance flag from the curation
(brand_site, label_photo_official, official_regulator, third_party).
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from water_aware_coffee.provenance import ValueType, WaterType
from water_aware_coffee.sources import register
from water_aware_coffee.sources.base import SourceFile, frame_from_records
from water_aware_coffee.units import Quantity

SOURCE_ID = "bottled-labels"
LICENSE = "Compilation CC BY 4.0 (this project); label compositions are facts required by law"
URL = "data/external/bottled/bottled_waters_v0.csv (see SOURCES.md for per-row URLs)"

_NUM = re.compile(r"^\s*(-?\d+(?:[.,]\d+)?)\s*$")
_CACO3_SINGLE = re.compile(r"as\s*CaCO3\)?\s*:\s*(-?\d+(?:[.,]\d+)?)\s*$", re.I)
_SINGLE_AFTER_COLON = re.compile(r":\s*(-?\d+(?:[.,]\d+)?)\s*$")


def _num(x: object) -> float | None:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    m = _NUM.match(str(x))
    return float(m.group(1).replace(",", ".")) if m else None


def _printed_caco3(x: object) -> float | None:
    """A printed 'Alkalinity, Total as CaCO3: 92' or 'Hardness, Total: 36' single value."""
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    s = str(x)
    m = _CACO3_SINGLE.search(s) or _SINGLE_AFTER_COLON.search(s)
    return float(m.group(1).replace(",", ".")) if m else None


def table_path(raw_dir: Path) -> Path:
    return raw_dir.parent / "external" / "bottled" / "bottled_waters_v0.csv"


@register(SOURCE_ID)
def load(raw_dir: Path) -> pd.DataFrame:
    path = table_path(raw_dir)
    src = SourceFile.from_path(SOURCE_ID, path, URL, LICENSE)
    df = pd.read_csv(path, dtype=str)
    recs: list[dict[str, object]] = []
    for i, row in df.iterrows():
        base: dict[str, object] = {
            "source_row_locator": f"row:{i};brand={row['brand']};product={row['product_name']}",
            "country_iso2": row["country_of_sale"],
            "admin1": row.get("source_location"),
            "locality": f"{row['brand']} | {row['product_name']}",
            "locality_code": None,
            "utility": row["brand"],
            "utility_code": None,
            "latitude": None,
            "longitude": None,
            "water_type": WaterType.BOTTLED.value,
            "source_type": "unknown",
            "softened": None,
            "period_start": pd.NaT,
            "period_end": pd.NaT,
            "value_type": ValueType.DECLARED.value,
            "n_samples": None,
            "measured": row.get("provenance_flag") != "third_party",
            "below_detection": False,
            "notes": (
                f"provenance={row.get('provenance_flag')}; url={row.get('source_url')}; "
                f"water_type_label={row.get('water_type')}; carbonation={row.get('carbonation')}; "
                f"label_date={row.get('analysis_or_label_date')}"
            ),
        }
        simple = [
            (Quantity.CALCIUM, "calcium_mg_l", "mg/L", "Cálcio / Calcium"),
            (Quantity.MAGNESIUM, "magnesium_mg_l", "mg/L", "Magnésio / Magnesium"),
            (Quantity.SODIUM, "sodium_mg_l", "mg/L", "Sódio / Sodium"),
            (Quantity.PH, "ph", None, "pH"),
        ]
        for q, col, unit, name in simple:
            v = _num(row.get(col))
            if v is not None:
                recs.append(
                    base
                    | {
                        "quantity": q.value,
                        "original_parameter_name": name,
                        "original_value": v,
                        "original_unit": unit,
                    }
                )
        bic = _num(row.get("bicarbonate_mg_l"))
        if bic is not None:
            recs.append(
                base
                | {
                    "quantity": Quantity.BICARBONATE.value,
                    "original_parameter_name": "Bicarbonato / Bicarbonate",
                    "original_value": bic,
                    "original_unit": "mg/L HCO3",
                }
            )
            recs.append(
                base
                | {
                    "quantity": Quantity.ALKALINITY.value,
                    "original_parameter_name": "Bicarbonato / Bicarbonate (alkalinity derived)",
                    "original_value": bic,
                    "original_unit": "mg/L HCO3",
                    "unit_assumed": False,
                }
            )
        else:
            alk = _printed_caco3(row.get("alkalinity_as_printed"))
            if alk is not None:
                recs.append(
                    base
                    | {
                        "quantity": Quantity.ALKALINITY.value,
                        "original_parameter_name": str(row.get("alkalinity_as_printed")),
                        "original_value": alk,
                        "original_unit": "mg/L as CaCO3",
                        "unit_assumed": False,
                    }
                )
        hard = _printed_caco3(row.get("hardness_as_printed"))
        if hard is not None:
            recs.append(
                base
                | {
                    "quantity": Quantity.HARDNESS.value,
                    "original_parameter_name": str(row.get("hardness_as_printed")),
                    "original_value": hard,
                    "original_unit": "mg/L as CaCO3",
                    "unit_assumed": False,
                }
            )
    records = pd.DataFrame(recs)
    if "unit_assumed" in records.columns:
        records["unit_assumed"] = records["unit_assumed"].fillna(False).astype(bool)
    return frame_from_records(records, src)
