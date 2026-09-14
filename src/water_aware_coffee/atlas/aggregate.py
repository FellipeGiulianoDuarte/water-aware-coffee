"""Collapse long-format measurements into per-locality summaries.

Input: the interim measurement tables (data/interim/<source>.parquet), already validated.
Output: one row per (source_id, locality_key, quantity) with median, p10, p90, n, share of
unit-assumed rows, share below detection, and period covered; then a wide table with one row per
locality holding hardness, calcium, magnesium, alkalinity, sodium, pH medians, plus hardness derived
from Ca and Mg where both exist.

Only finished water is aggregated. A locality key is locality_code when present, else locality.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from water_aware_coffee.units import CA_TO_CACO3, MG_TO_CACO3

QUANTITIES = ["hardness", "calcium", "magnesium", "alkalinity", "sodium", "ph"]


def load_interim(interim_dir: Path, sources: list[str] | None = None) -> pd.DataFrame:
    files = sorted(interim_dir.glob("*.parquet"))
    if sources:
        files = [f for f in files if f.stem in sources]
    if not files:
        raise FileNotFoundError(f"no interim parquet files in {interim_dir}")
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)


def summarise_long(df: pd.DataFrame, finished_only: bool = True) -> pd.DataFrame:
    d = df[df["water_type"] == "finished"] if finished_only else df
    d = d.copy()
    d["locality_key"] = d["locality_code"].where(d["locality_code"].notna(), d["locality"])
    g = d.groupby(["source_id", "country_iso2", "admin1", "locality_key", "quantity"], dropna=False)
    out = g.agg(
        locality=("locality", "first"),
        utility=("utility", "first"),
        median=("value", "median"),
        p10=("value", lambda s: s.quantile(0.10)),
        p90=("value", lambda s: s.quantile(0.90)),
        n=("value", "size"),
        share_unit_assumed=("unit_assumed", "mean"),
        share_below_detection=("below_detection", "mean"),
        share_measured=("measured", "mean"),
        period_start=("period_start", "min"),
        period_end=("period_end", "max"),
        latitude=("latitude", "median"),
        longitude=("longitude", "median"),
    )
    return out.reset_index()


def to_wide(summary: pd.DataFrame) -> pd.DataFrame:
    """One row per locality; columns <quantity>_median, <quantity>_n, <quantity>_unit_assumed."""
    idx = ["source_id", "country_iso2", "admin1", "locality_key"]
    wide = summary.pivot_table(
        index=idx,
        columns="quantity",
        values=["median", "n", "share_unit_assumed"],
        aggfunc="first",
    )
    wide.columns = pd.Index([f"{col[1]}_{col[0]}" for col in wide.columns.to_list()])
    meta = summary.groupby(idx, dropna=False).agg(
        locality=("locality", "first"),
        utility=("utility", "first"),
        latitude=("latitude", "first"),
        longitude=("longitude", "first"),
        period_start=("period_start", "min"),
        period_end=("period_end", "max"),
    )
    wide = meta.join(wide).reset_index()
    for q in QUANTITIES:
        for stat in ("median", "n", "share_unit_assumed"):
            col = f"{q}_{stat}"
            if col not in wide.columns:
                wide[col] = pd.NA
    # Hardness derived from ions where both exist; keep the reported value alongside.
    both = wide["calcium_median"].notna() & wide["magnesium_median"].notna()
    wide["hardness_from_ions"] = pd.NA
    wide.loc[both, "hardness_from_ions"] = (
        wide.loc[both, "calcium_median"].astype(float) * CA_TO_CACO3
        + wide.loc[both, "magnesium_median"].astype(float) * MG_TO_CACO3
    )
    # Best hardness: from ions when available (no unit ambiguity), else reported.
    wide["hardness_best"] = wide["hardness_from_ions"].where(both, wide["hardness_median"])
    wide["hardness_best_basis"] = pd.Series("from_ions", index=wide.index).where(both, "reported")
    wide.loc[wide["hardness_best"].isna(), "hardness_best_basis"] = pd.NA
    return wide


def build_atlas_v0(interim_dir: Path, out_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = load_interim(interim_dir)
    long = summarise_long(df)
    wide = to_wide(long)
    out_dir.mkdir(parents=True, exist_ok=True)
    long.to_parquet(out_dir / "atlas_v0_long.parquet", index=False)
    wide.to_parquet(out_dir / "atlas_v0_wide.parquet", index=False)
    return long, wide
