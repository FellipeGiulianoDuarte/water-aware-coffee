"""Loader for TapWaterData US water hardness (source id "tapwaterdata-us").

Reads data/raw/us/tapwaterdata/water-hardness.csv: one row per US city, hardness only, three
tiers in the "tier" column:

- T1: utility-reported hardness from Consumer Confidence Reports. Utility name and PWSID are inside
  the free-text "source" column ("Utility-reported water quality data — NAME (PWSID XX1234567)").
- T2: computed by TapWaterData from utility-reported Ca and Mg (inputs not published).
- T3: median of ambient Water Quality Portal samples in the city's county (not tap water).

Every row becomes one hardness measurement. T1 and T2 are finished water, value_type "typical";
T3 is water_type "unknown", measured=False, value_type "median" with n_samples = nSamples.
The dataset documents hardness as "mg/L as calcium carbonate", so original_unit is passed as
"mg/L as CaCO3" (not ambiguous).
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from water_aware_coffee.provenance import SourceType, ValueType, WaterType
from water_aware_coffee.sources import register
from water_aware_coffee.sources.base import SourceFile, frame_from_records
from water_aware_coffee.units import Quantity

log = logging.getLogger(__name__)

SOURCE_ID = "tapwaterdata-us"
URL = "https://www.tapwaterdata.com/data/water-hardness.csv"
LICENSE = (
    "CC BY 4.0 (TapWaterData Water Hardness Dataset, 2026, "
    "https://www.tapwaterdata.com/water-hardness)"
)
REL_DIR = Path("us") / "tapwaterdata"
FILE_NAME = "water-hardness.csv"
DOWNLOAD_DATE_FILE = "download_date.txt"

ORIGINAL_PARAMETER_NAME = "hardness_mg_l"
ORIGINAL_UNIT = "mg/L as CaCO3"  # documented by the dataset page: "mg/L as calcium carbonate"

# PWSID: two-letter state code + 7 alphanumerics (Delaware uses e.g. "DE00A0757"), always
# written as "(PWSID XX1234567)" in the source text. "PWSID null" does not match.
PWSID_RE = re.compile(r"PWSID ([A-Z]{2}[A-Z0-9]{7})\b")
# "Utility-reported water quality data — NAME (PWSID XX1234567)"; the PWSID part is optional.
UTILITY_RE = re.compile(r"^Utility-reported water quality data — (.+?)(?:\s*\(PWSID [^)]*\))?\s*$")

WATER_TYPE_BY_TIER = {
    "T1": WaterType.FINISHED.value,
    "T2": WaterType.FINISHED.value,
    "T3": WaterType.UNKNOWN.value,
}


def _download_date(directory: Path) -> date | None:
    """Parse download_date.txt ("downloaded_utc=2026-09-14T14:30:44Z") if present."""
    f = directory / DOWNLOAD_DATE_FILE
    if not f.exists():
        return None
    m = re.search(r"(\d{4}-\d{2}-\d{2})", f.read_text())
    return datetime.strptime(m.group(1), "%Y-%m-%d").date() if m else None


def _count_comment_lines(path: Path) -> int:
    """Number of leading lines starting with '#'. Data rows may contain '#', so pandas'
    comment= option cannot be used."""
    n = 0
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.startswith("#"):
                break
            n += 1
    return n


def read_raw(path: Path) -> pd.DataFrame:
    """Read the CSV with the leading '#' comment block skipped and text columns as str."""
    skip = _count_comment_lines(path)
    return pd.read_csv(
        path,
        skiprows=skip,
        dtype={
            "slug": str,
            "city": str,
            "state": str,
            "stateCode": str,
            "category": str,
            "tier": str,
            "source": str,
            "sourceDate": str,
            "disputed": str,
        },
        encoding="utf-8",
    )


def _utility_name(source: str | float, tier: str) -> str | None:
    """Utility name from the free-text 'source' column, T1 rows only."""
    if tier != "T1" or not isinstance(source, str):
        return None
    m = UTILITY_RE.match(source)
    if m:
        name = m.group(1).strip()
        return name or None
    # A handful of T1 rows cite a report instead ("City of X Department ..., 2026 Water Quality
    # Report ..."): keep the publisher part before the first comma.
    if source.startswith("Computed from"):
        return None
    return source.split(",")[0].strip() or None


def _fmt(x: float) -> str:
    return "na" if pd.isna(x) else f"{x:g}"


@register(SOURCE_ID)
def load(raw_dir: Path) -> pd.DataFrame:
    path = raw_dir / REL_DIR / FILE_NAME
    src = SourceFile.from_path(
        SOURCE_ID, path, URL, LICENSE, download_date=_download_date(path.parent)
    )
    df = read_raw(path)
    n_raw = len(df)

    value = pd.to_numeric(df["hardness_mg_l"], errors="coerce")
    missing = value.isna()
    if missing.any():
        log.info("%s: dropping %d rows with no hardness_mg_l", SOURCE_ID, int(missing.sum()))
    df = df.loc[~missing].copy()
    value = value.loc[~missing]

    tier = df["tier"].fillna("").str.strip()
    is_t1 = tier == "T1"
    is_t3 = tier == "T3"

    pwsid = pd.Series(
        df["source"].where(is_t1, None).astype("string").str.extract(PWSID_RE, expand=False),
        index=df.index,
    )
    utility = pd.Series(
        [_utility_name(s, t) for s, t in zip(df["source"], tier, strict=True)],
        index=df.index,
        dtype="object",
    )
    n_samples = pd.to_numeric(df["nSamples"], errors="coerce").where(is_t3, np.nan)
    n_samples = n_samples.where(n_samples >= 1, np.nan)

    disputed = df["disputed"].fillna("").str.strip().str.lower().isin({"true", "1", "yes"})
    notes = (
        "tier="
        + tier
        + "; category="
        + df["category"].fillna("").astype(str)
        + "; disputed="
        + disputed.map({True: "True", False: "False"})
        + "; range="
        + df["range_min"].map(_fmt)
        + "-"
        + df["range_max"].map(_fmt)
    )

    records = pd.DataFrame(
        {
            "source_row_locator": "file:"
            + FILE_NAME
            + ";line:"
            + df.index.astype(str)
            + ";slug:"
            + df["slug"].fillna("").astype(str),
            "country_iso2": "US",
            "admin1": df["stateCode"].where(df["stateCode"].notna(), None),
            "locality": df["city"].fillna(df["slug"]).astype(str),
            "locality_code": df["slug"].where(df["slug"].notna(), None),
            "utility": utility,
            "utility_code": pwsid.astype("object").where(pwsid.notna(), None),
            "latitude": pd.to_numeric(df["lat"], errors="coerce"),
            "longitude": pd.to_numeric(df["lng"], errors="coerce"),
            "water_type": tier.map(WATER_TYPE_BY_TIER).fillna(WaterType.UNKNOWN.value),
            "source_type": SourceType.UNKNOWN.value,
            "softened": None,
            "period_start": pd.NaT,
            "period_end": pd.to_datetime(df["sourceDate"], errors="coerce", format="%Y-%m-%d"),
            "quantity": Quantity.HARDNESS.value,
            "value_type": np.where(is_t3, ValueType.MEDIAN.value, ValueType.TYPICAL.value),
            "n_samples": n_samples,
            "measured": ~is_t3,
            "below_detection": False,
            "original_parameter_name": ORIGINAL_PARAMETER_NAME,
            "original_value": value.astype(float),
            "original_unit": ORIGINAL_UNIT,
            "notes": notes,
        },
        index=df.index,
    )
    log.info(
        "%s: %d raw rows, %d emitted; T1 rows %d, of which %d with a PWSID",
        SOURCE_ID,
        n_raw,
        len(records),
        int(is_t1.sum()),
        int(pwsid.notna().sum()),
    )
    return frame_from_records(records.reset_index(drop=True), src)
