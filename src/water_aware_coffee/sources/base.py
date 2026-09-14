"""Shared helpers for source loaders.

A loader's job: read raw file(s), pick the rows for our quantities, convert units, and emit the
long-format measurement table with every provenance column filled. `MeasurementBuilder` fills the
constant per-file columns (source id, URL, file name, sha256, download date, license) so a loader
only supplies what varies per row.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from water_aware_coffee.provenance import COLUMNS, validate
from water_aware_coffee.units import TARGET_UNIT, Quantity, conversion_factor, is_ambiguous

REPO_ROOT = Path(__file__).resolve().parents[3]
RAW_DIR = REPO_ROOT / "data" / "raw"
INTERIM_DIR = REPO_ROOT / "data" / "interim"


def sha256_of(path: Path, chunk: int = 1 << 20) -> str:
    """sha256 of a file, cached next to it as <name>.sha256 so 200 MB files are hashed once."""
    cache = path.with_name(path.name + ".sha256")
    if cache.exists() and cache.stat().st_mtime >= path.stat().st_mtime:
        return cache.read_text().strip()
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    digest = h.hexdigest()
    cache.write_text(digest)
    return digest


def download_date_of(path: Path) -> date:
    """Download date: from a sidecar <name>.meta.json {"download_date": "YYYY-MM-DD"} if present,
    else the file's modification date."""
    meta = path.with_name(path.name + ".meta.json")
    if meta.exists():
        d = json.loads(meta.read_text()).get("download_date")
        if d:
            return date.fromisoformat(d)
    return date.fromtimestamp(path.stat().st_mtime)


@dataclass
class SourceFile:
    """Constant provenance for one raw file."""

    source_id: str
    path: Path
    url: str
    license: str
    sha256: str = field(default="")
    download_date: date = field(default_factory=date.today)

    def __post_init__(self) -> None:
        if not self.sha256:
            self.sha256 = sha256_of(self.path)

    @classmethod
    def from_path(
        cls, source_id: str, path: Path, url: str, license: str, download_date: date | None = None
    ) -> SourceFile:
        """Build with sha256 computed and download date from sidecar or file mtime unless given."""
        return cls(
            source_id=source_id,
            path=path,
            url=url,
            license=license,
            download_date=download_date or download_date_of(path),
        )


@dataclass
class MeasurementBuilder:
    """Accumulates rows for one SourceFile and emits a validated DataFrame."""

    src: SourceFile
    rows: list[dict[str, Any]] = field(default_factory=list)

    def add(
        self,
        *,
        quantity: Quantity,
        original_value: float,
        original_unit: str | None,
        original_parameter_name: str,
        locator: str,
        country_iso2: str,
        locality: str,
        water_type: str,
        source_type: str,
        value_type: str,
        measured: bool = True,
        below_detection: bool = False,
        admin1: str | None = None,
        locality_code: str | None = None,
        utility: str | None = None,
        utility_code: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        softened: bool | None = None,
        period_start: Any = None,
        period_end: Any = None,
        n_samples: float | None = None,
        unit_assumed: bool | None = None,
        factor_override: float | None = None,
        notes: str | None = None,
    ) -> None:
        """Add one measurement. Unit conversion happens here.

        `factor_override` lets a loader supply the factor when the source unit string is missing or
        wrong but the basis is known from documentation (then set unit_assumed accordingly).
        """
        if factor_override is not None:
            factor = factor_override
        else:
            factor = conversion_factor(quantity, original_unit)
        if unit_assumed is None:
            unit_assumed = is_ambiguous(original_unit) and quantity is not Quantity.PH
        self.rows.append(
            {
                "source_id": self.src.source_id,
                "source_url": self.src.url,
                "source_file": self.src.path.name,
                "source_file_sha256": self.src.sha256,
                "download_date": pd.Timestamp(self.src.download_date),
                "source_row_locator": locator,
                "source_license": self.src.license,
                "country_iso2": country_iso2,
                "admin1": admin1,
                "locality": locality,
                "locality_code": locality_code,
                "utility": utility,
                "utility_code": utility_code,
                "latitude": latitude,
                "longitude": longitude,
                "water_type": water_type,
                "source_type": source_type,
                "softened": softened,
                "period_start": pd.Timestamp(period_start) if period_start is not None else pd.NaT,
                "period_end": pd.Timestamp(period_end) if period_end is not None else pd.NaT,
                "quantity": quantity.value,
                "value": float(original_value) * factor,
                "unit": TARGET_UNIT[quantity],
                "value_type": value_type,
                "n_samples": n_samples,
                "measured": measured,
                "below_detection": below_detection,
                "original_parameter_name": original_parameter_name,
                "original_value": float(original_value),
                "original_unit": original_unit,
                "conversion_factor": factor,
                "unit_assumed": unit_assumed,
                "notes": notes,
            }
        )

    def frame(self, do_validate: bool = True) -> pd.DataFrame:
        df = pd.DataFrame(self.rows, columns=COLUMNS)
        return validate(df) if do_validate else df


def frame_from_records(records: pd.DataFrame, src: SourceFile) -> pd.DataFrame:
    """Vectorised alternative to MeasurementBuilder for large sources.

    `records` must already hold the per-row columns: everything in COLUMNS except the source_* and
    download_date constants, `value`, `unit` and `conversion_factor`. This fills the constants,
    computes `conversion_factor` from (quantity, original_unit) unless that column is already
    present, computes `value` and `unit`, and validates.
    """
    df = records.copy()
    df["source_id"] = src.source_id
    df["source_url"] = src.url
    df["source_file"] = src.path.name
    df["source_file_sha256"] = src.sha256
    df["download_date"] = pd.Timestamp(src.download_date)
    df["source_license"] = src.license
    if "conversion_factor" not in df.columns:
        key = list(zip(df["quantity"], df["original_unit"].fillna(""), strict=True))
        uniq = {k: conversion_factor(Quantity(k[0]), k[1] or None) for k in set(key)}
        df["conversion_factor"] = [uniq[k] for k in key]
    if "unit_assumed" not in df.columns:
        df["unit_assumed"] = [
            is_ambiguous(u) and q != Quantity.PH.value
            for q, u in zip(df["quantity"], df["original_unit"], strict=True)
        ]
    df["value"] = df["original_value"].astype(float) * df["conversion_factor"].astype(float)
    df["unit"] = df["quantity"].map(lambda q: TARGET_UNIT[Quantity(q)])
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = None
    return validate(df[COLUMNS])


def parse_decimal_comma(s: pd.Series) -> pd.Series:
    """'42,4' -> 42.4 ; non-numeric -> NaN."""
    return pd.to_numeric(
        s.astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
        errors="coerce",
    )
