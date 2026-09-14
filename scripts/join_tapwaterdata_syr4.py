"""Join test: TapWaterData T1 hardness (per city, PWSID parsed from the source text) against EPA
SYR4 finished-water alkalinity (per PWSID, sample level).

Run after `uv run wac build tapwaterdata-us epa-syr4-us`:

    uv run python scripts/join_tapwaterdata_syr4.py

Prints how many T1 cities carry a PWSID, how many of those PWSIDs have finished-water alkalinity
in SYR4, the median hardness and alkalinity of the joined set, and a 5-row example.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

INTERIM = Path(__file__).resolve().parents[1] / "data" / "interim"


def main() -> None:
    twd_path = INTERIM / "tapwaterdata-us.parquet"
    syr_path = INTERIM / "epa-syr4-us.parquet"
    for p in (twd_path, syr_path):
        if not p.exists():
            sys.exit(f"missing {p}; run `uv run wac build tapwaterdata-us epa-syr4-us` first")
    twd = pd.read_parquet(twd_path)
    syr = pd.read_parquet(syr_path)

    t1 = twd[twd["notes"].str.startswith("tier=T1") & (twd["quantity"] == "hardness")]
    t1_pw = t1[t1["utility_code"].notna()]
    print(f"TapWaterData T1 hardness rows (cities): {len(t1):,}")
    print(f"  with a PWSID parsed from the source text: {len(t1_pw):,}")
    print(f"  distinct PWSIDs among them: {t1_pw['utility_code'].nunique():,}")

    alk = syr[(syr["quantity"] == "alkalinity") & (syr["water_type"] == "finished")]
    n_alk_pw = alk["utility_code"].nunique()
    print(f"SYR4 finished-water alkalinity rows: {len(alk):,} at {n_alk_pw:,} PWSIDs")

    # One alkalinity figure per PWSID: median over all finished-water samples 2012-2019.
    alk_by_pw = (
        alk.groupby("utility_code")
        .agg(
            alkalinity_median=("value", "median"),
            alkalinity_n=("value", "size"),
            alkalinity_last=("period_end", "max"),
            syr4_system_name=("utility", "first"),
        )
        .reset_index()
    )
    joined = t1_pw.merge(alk_by_pw, on="utility_code", how="inner")
    pw_hit = joined["utility_code"].nunique()
    print(
        f"T1 PWSIDs that appear in SYR4 finished-water alkalinity: {pw_hit:,} "
        f"({pw_hit / t1_pw['utility_code'].nunique():.1%} of distinct T1 PWSIDs); "
        f"{len(joined):,} T1 cities covered ({len(joined) / len(t1):.1%} of T1 cities)"
    )
    print(f"Median hardness of joined cities: {joined['value'].median():.1f} mg/L as CaCO3")
    print(
        f"Median alkalinity (per-PWSID medians) of joined cities: "
        f"{joined['alkalinity_median'].median():.1f} mg/L as CaCO3"
    )
    print(f"Median alkalinity samples per joined PWSID: {joined['alkalinity_n'].median():.0f}")
    ratio = joined["alkalinity_median"] / joined["value"]
    print(
        f"Alkalinity / hardness ratio: median {ratio.median():.2f}, "
        f"IQR {ratio.quantile(0.25):.2f}-{ratio.quantile(0.75):.2f}"
    )

    cols = {
        "locality": "city",
        "admin1": "state",
        "utility": "utility (TapWaterData)",
        "utility_code": "PWSID",
        "value": "hardness mg/L CaCO3",
        "alkalinity_median": "alkalinity median mg/L CaCO3",
        "alkalinity_n": "alk samples",
        "alkalinity_last": "last alk sample",
    }
    example = (
        joined.sort_values("alkalinity_n", ascending=False).head(5)[list(cols)].rename(columns=cols)
    )
    example["last alk sample"] = example["last alk sample"].dt.date
    with pd.option_context("display.width", 200, "display.max_columns", 20):
        print("\nExample (5 joined cities with the most alkalinity samples):")
        print(example.to_string(index=False))


if __name__ == "__main__":
    main()
