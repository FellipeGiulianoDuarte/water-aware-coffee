"""Loader for US EPA Six-Year Review 4 compliance monitoring data (source id "epa-syr4-us").

Reads data/raw/us/epa_syr/syr4_dbp_related-parameters.zip directly (never the extracted folder,
so provenance points at the downloaded archive) and takes two tab-delimited members:

- "SYR4_DBP_Related Parameters/TOTAL ALKALINITY.TXT"  -> quantity alkalinity
- "SYR4_DBP_Related Parameters/PH.txt"                -> quantity ph

Landing page: https://www.epa.gov/dwsixyearreview/six-year-review-4-compliance-monitoring-data-2012-2019

Both members share 29 columns (PWSID, SYSTEM_NAME, STATE_CODE, RETAIL_POPULATION_SERVED,
SOURCE_WATER_TYPE, SAMPLING_POINT_TYPE, SOURCE_TYPE_CODE, SAMPLE_COLLECTION_DATE, DETECT,
DETECTION_LIMIT_VALUE, DETECTION_LIMIT_UNIT, DETECTION_LIMIT_CODE, VALUE, UNIT, ...).

Water type: any row flagged RW (SOURCE_TYPE_CODE or SAMPLING_POINT_TYPE) is "source"; otherwise
SOURCE_TYPE_CODE == "FN" or SAMPLING_POINT_TYPE in {EP, DS} is "finished"; the rest is dropped.

Below detection: DETECT == "0" rows have an empty VALUE. They are kept with value = the detection
limit and below_detection=True when a positive limit in a compatible unit exists; otherwise dropped.

Units: alkalinity UNIT is "MG/L" with no basis stated; the row is flagged unit_assumed=True (as
CaCO3, the EPA convention). pH UNIT is blank -> original_unit None.

Rows the schema cannot hold are dropped and counted in the log: negative alkalinity, pH outside
0..14, non-numeric VALUE with DETECT == "1".
"""

from __future__ import annotations

import logging
import re
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import IO

import pandas as pd

from water_aware_coffee.provenance import SourceType, ValueType, WaterType
from water_aware_coffee.sources import register
from water_aware_coffee.sources.base import SourceFile, frame_from_records
from water_aware_coffee.units import Quantity, conversion_factor

log = logging.getLogger(__name__)

SOURCE_ID = "epa-syr4-us"
LANDING_URL = (
    "https://www.epa.gov/dwsixyearreview/six-year-review-4-compliance-monitoring-data-2012-2019"
)
URL = "https://www.epa.gov/system/files/other-files/2024-03/syr4_dbp_related-parameters.zip"
LICENSE = "US federal government work, public domain"
REL_DIR = Path("us") / "epa_syr"
ZIP_NAME = "syr4_dbp_related-parameters.zip"
SOURCES_FILE = "SOURCES.txt"  # "<file> <url> downloaded_utc=YYYY-MM-DDTHH:MMZ" per line

ALKALINITY_MEMBER = "TOTAL ALKALINITY.TXT"
PH_MEMBER = "PH.txt"

ALKALINITY_NOTE = (
    "EPA SYR4 TOTAL ALKALINITY in MG/L; basis assumed as CaCO3 (EPA convention), not stated in file"
)
ALKALINITY_BLANK_UNIT_NOTE = "UNIT blank on below-detection row; assumed MG/L as CaCO3"

SOURCE_TYPE_BY_CODE = {
    "SW": SourceType.SURFACE.value,
    "SWP": SourceType.SURFACE.value,  # purchased surface water
    "GW": SourceType.GROUND.value,
    "GWP": SourceType.GROUND.value,  # purchased ground water
    "GU": SourceType.GROUND.value,  # ground water under the direct influence of surface water
    "GUP": SourceType.GROUND.value,
}

# Detection-limit units compatible with the quantity; blank means "same as VALUE unit".
LIMIT_UNITS_OK = {
    Quantity.ALKALINITY: {"", "MG/L"},
    Quantity.PH: {"", "PH", "SU", "UNITS"},
}

TEXT_ENCODING = "cp1252"  # PH.txt has non-UTF-8 bytes (0x96 en dash) in SYSTEM_NAME


def _download_date(directory: Path) -> date | None:
    f = directory / SOURCES_FILE
    if not f.exists():
        return None
    for line in f.read_text().splitlines():
        if line.startswith(ZIP_NAME):
            m = re.search(r"downloaded_utc=(\d{4}-\d{2}-\d{2})", line)
            if m:
                return datetime.strptime(m.group(1), "%Y-%m-%d").date()
    return None


def _find_member(zf: zipfile.ZipFile, basename: str) -> str:
    for name in zf.namelist():
        if name.rsplit("/", 1)[-1].lower() == basename.lower():
            return name
    raise FileNotFoundError(f"{basename!r} not found in {zf.filename}: {zf.namelist()}")


def read_member(fh: IO[bytes]) -> pd.DataFrame:
    """Read one tab-delimited SYR4 member with every column as str ('' for empty)."""
    return pd.read_csv(
        fh,
        sep="\t",
        dtype=str,
        keep_default_na=False,
        encoding=TEXT_ENCODING,
        encoding_errors="replace",
    )


def _records(df: pd.DataFrame, quantity: Quantity, member: str) -> pd.DataFrame:
    """Measurement records (schema columns minus the SourceFile constants) for one member."""
    n_raw = len(df)
    stc = df["SOURCE_TYPE_CODE"].str.strip().str.upper()
    spt = df["SAMPLING_POINT_TYPE"].str.strip().str.upper()
    is_source = (stc == "RW") | (spt == "RW")
    is_finished = ~is_source & ((stc == "FN") | spt.isin(["EP", "DS"]))
    keep_wt = is_source | is_finished

    value = pd.to_numeric(df["VALUE"], errors="coerce")
    below = df["DETECT"].str.strip() == "0"
    limit = pd.to_numeric(df["DETECTION_LIMIT_VALUE"], errors="coerce")
    limit_unit = df["DETECTION_LIMIT_UNIT"].str.strip().str.upper()
    limit_ok = below & (limit > 0) & limit_unit.isin(LIMIT_UNITS_OK[quantity])
    value = value.where(~below, limit)
    if quantity is Quantity.PH:
        in_range = value.between(0, 14)
    else:
        in_range = value >= 0

    drop_no_limit = keep_wt & below & ~limit_ok
    drop_nonnumeric = keep_wt & ~below & value.isna()
    drop_range = keep_wt & value.notna() & ~in_range & ~(below & ~limit_ok)
    keep = keep_wt & ~drop_no_limit & ~drop_nonnumeric & ~drop_range
    log.info(
        "%s %s: %d raw rows, %d emitted (%d finished, %d source); dropped %d not finished/source, "
        "%d below detection without usable limit, %d non-numeric VALUE, %d out of range",
        SOURCE_ID,
        member,
        n_raw,
        int(keep.sum()),
        int((keep & is_finished).sum()),
        int((keep & is_source).sum()),
        int((~keep_wt).sum()),
        int(drop_no_limit.sum()),
        int(drop_nonnumeric.sum()),
        int(drop_range.sum()),
    )
    log.info(
        "%s %s: SOURCE_WATER_TYPE codes seen %s",
        SOURCE_ID,
        member,
        df["SOURCE_WATER_TYPE"].str.strip().value_counts().to_dict(),
    )

    d = df.loc[keep]
    value = value.loc[keep]
    below = below.loc[keep]
    is_source = is_source.loc[keep]
    limit_unit = limit_unit.loc[keep]

    unit_raw = d["UNIT"].str.strip()
    if quantity is Quantity.PH:
        original_unit = pd.Series([None] * len(d), index=d.index, dtype="object")
        factor = pd.Series(1.0, index=d.index)
        unit_assumed = pd.Series(False, index=d.index)
        unit_note = pd.Series("", index=d.index)
    else:
        # Below-detection rows have UNIT blank; fall back to the detection-limit unit.
        unit_str = unit_raw.where(unit_raw != "", limit_unit)
        blank = unit_str == ""
        original_unit = unit_str.where(~blank, None).astype("object")
        distinct = {u: conversion_factor(quantity, u) for u in unit_str[~blank].unique()}
        factor = unit_str.map(distinct).fillna(1.0).astype(float)
        unit_assumed = pd.Series(True, index=d.index)
        unit_note = pd.Series(
            ALKALINITY_NOTE + blank.map({True: "; " + ALKALINITY_BLANK_UNIT_NOTE, False: ""}),
            index=d.index,
        )

    state = d["STATE_CODE"].str.strip().str.upper()
    state = state.where(state != "", d["PWSID"].str[:2].str.upper())
    system_name = d["SYSTEM_NAME"].str.strip()
    pwsid = d["PWSID"].str.strip()
    source_water = d["SOURCE_WATER_TYPE"].str.strip().str.upper()

    notes = (
        unit_note
        + unit_note.map(lambda s: "; " if s else "")
        + "population="
        + d["RETAIL_POPULATION_SERVED"].str.strip()
        + "; sampling_point="
        + d["SAMPLING_POINT_TYPE"].str.strip()
        + "; source_type_code="
        + d["SOURCE_TYPE_CODE"].str.strip()
        + "; source_water_type="
        + source_water
        + below.map({True: "; below_detection_limit_code=", False: ""})
        + d["DETECTION_LIMIT_CODE"].str.strip().where(below, "")
    )

    return pd.DataFrame(
        {
            "source_row_locator": f"file:{member};line:" + d.index.astype(str),
            "country_iso2": "US",
            "admin1": state.where(state != "", None),
            "locality": system_name.where(system_name != "", pwsid),
            "locality_code": None,
            "utility": system_name.where(system_name != "", None),
            "utility_code": pwsid.where(pwsid != "", None),
            "latitude": None,
            "longitude": None,
            "water_type": is_source.map(
                {True: WaterType.SOURCE.value, False: WaterType.FINISHED.value}
            ),
            "source_type": source_water.map(SOURCE_TYPE_BY_CODE).fillna(SourceType.UNKNOWN.value),
            "softened": None,
            "period_start": pd.to_datetime(d["SAMPLE_COLLECTION_DATE"], format="%d-%b-%y"),
            "period_end": pd.to_datetime(d["SAMPLE_COLLECTION_DATE"], format="%d-%b-%y"),
            "quantity": quantity.value,
            "value_type": ValueType.SAMPLE.value,
            "n_samples": None,
            "measured": True,
            "below_detection": below,
            "original_parameter_name": d["ANALYTE_NAME"].str.strip(),
            "original_value": value.astype(float),
            "original_unit": original_unit,
            "conversion_factor": factor,
            "unit_assumed": unit_assumed,
            "notes": notes,
        },
        index=d.index,
    )


@register(SOURCE_ID)
def load(raw_dir: Path) -> pd.DataFrame:
    path = raw_dir / REL_DIR / ZIP_NAME
    src = SourceFile.from_path(
        SOURCE_ID, path, URL, LICENSE, download_date=_download_date(path.parent)
    )
    parts: list[pd.DataFrame] = []
    with zipfile.ZipFile(path) as zf:
        for basename, quantity in (
            (ALKALINITY_MEMBER, Quantity.ALKALINITY),
            (PH_MEMBER, Quantity.PH),
        ):
            member = _find_member(zf, basename)
            with zf.open(member) as fh:
                raw = read_member(fh)
            parts.append(_records(raw, quantity, member.rsplit("/", 1)[-1]))
    records = pd.concat(parts, ignore_index=True)
    return frame_from_records(records, src)
