"""Rank waters by closeness to the SCA reference water (40 mg/L alkalinity, 68 mg/L hardness).

Criterion (stated, not fitted): distance = |ln(alk/40)| + 0.5 * |ln(hard/68)|. Alkalinity counts
double because it drives the modelled effect; hardness enters through the bounded cation term and
as a scale-forming nuisance. A distance of 0.25 means alkalinity within about 28 percent of the
reference at matching hardness. "Best" therefore means "brews closest to the reference for a light
or medium roast"; it is not a quality judgement of the water and it is not what the majority
preference cluster would choose (see the paper's discussion).

Run after `wac atlas`:  uv run python scripts/rankings.py
Writes docs/rankings.md and paper/tables/bottled_reference.md.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
REF_ALK, REF_HARD = 40.0, 68.0
COUNTRY = {
    "BR": "Brazil",
    "US": "United States",
    "GB": "United Kingdom",
    "DE": "Germany",
    "FR": "France",
    "IT": "Italy",
    "PT": "Portugal",
}


def distance(alk: pd.Series, hard: pd.Series) -> pd.Series:
    d = np.abs(np.log(alk / REF_ALK))
    h = np.abs(np.log(hard / REF_HARD)).fillna(0.0)  # no hardness: alkalinity only
    return d + 0.5 * h


def load() -> pd.DataFrame:
    w = pd.read_parquet(PROC / "atlas_v0_wide.parquet")
    w["alk"] = pd.to_numeric(w["alkalinity_best"], errors="coerce")
    w["alk_measured"] = pd.to_numeric(w["alkalinity_median"], errors="coerce")
    w["hard"] = pd.to_numeric(w["hardness_best"], errors="coerce")
    w["pop"] = pd.to_numeric(w["population"], errors="coerce")
    w["imputed"] = w["alkalinity_imputed"].astype(bool)
    w = w[(w["alk"] > 0)]
    w["distance"] = distance(w["alk"], w["hard"])
    return w


def fmt(x: float, nd: int = 0) -> str:
    return "" if pd.isna(x) else f"{x:.{nd}f}"


def bottled_tables(w: pd.DataFrame) -> tuple[str, str]:
    b = w[
        (w["source_id"] == "bottled-labels") & w["alk_measured"].notna() & w["hard"].notna()
    ].copy()

    def _bp(loc: str) -> str:
        brand, _, product = loc.partition(" | ")
        return product if product.lower().startswith(brand.lower()) else f"{brand}: {product}"

    b["brand_product"] = b["locality"].map(_bp)
    lines_doc = [
        "## Bottled waters closest to the reference, by country",
        "",
        "Distance = |ln(alkalinity/40)| + 0.5·|ln(hardness/68)|; smaller is closer. Label values, not samples.",
        "",
    ]
    lines_paper = [
        "| country | product | alkalinity | hardness | pH | distance |",
        "|---|---|---|---|---|---|",
    ]
    for cc in ["BR", "US", "GB", "DE", "FR", "IT", "PT"]:
        g = b[b["country_iso2"] == cc].sort_values("distance")
        if len(g) == 0:
            continue
        lines_doc += [
            f"### {COUNTRY[cc]}",
            "",
            "| rank | product | alkalinity mg/L as CaCO3 | hardness mg/L as CaCO3 | pH | distance |",
            "|---|---|---|---|---|---|",
        ]
        for i, (_, r) in enumerate(g.head(8).iterrows(), start=1):
            lines_doc.append(
                f"| {i} | {r['brand_product']} | {r['alk']:.0f} | {fmt(r['hard'])} | {fmt(pd.to_numeric(r.get('ph_median'), errors='coerce'), 1)} | {r['distance']:.2f} |"
            )
        for _, r in g.head(3).iterrows():
            lines_paper.append(
                f"| {COUNTRY[cc]} | {r['brand_product']} | {r['alk']:.0f} | {fmt(r['hard'])} | {fmt(pd.to_numeric(r.get('ph_median'), errors='coerce'), 1)} | {r['distance']:.2f} |"
            )
        worst = g.sort_values("alk", ascending=False).head(3)
        lines_doc += [
            "",
            "Highest alkalinity (flattest for light roasts): "
            + "; ".join(f"{r['brand_product']} ({r['alk']:.0f})" for _, r in worst.iterrows()),
            "",
        ]
    lines_paper += [
        "",
        ": Bottled waters closest to the reference water in each country of sale, by the distance |ln(alkalinity/40)| + 0.5·|ln(hardness/68)|; values from labels. {#tbl-bottled-reference}",
    ]
    return "\n".join(lines_doc) + "\n", "\n".join(lines_paper) + "\n"


def tap_tables(w: pd.DataFrame) -> str:
    t = w[(w["source_id"] != "bottled-labels") & (w["source_id"] != "tapwaterdata-us")].copy()
    lines = [
        "## Tap water closest to the reference, by country",
        "",
        "Localities with at least 50,000 people served (or residents). Measured alkalinity unless marked imputed.",
        "Distance as above. US rows are utilities joined to their largest city; England rows are small areas of about 1,500 people, so the England list is by water company instead.",
        "",
    ]
    # US
    usj = t[(t["source_id"] == "tapwaterdata-us+epa-syr4-us") & t["hard"].notna()].copy()
    # several cities share one utility: keep the largest-population city per utility
    usj = usj.sort_values("pop", ascending=False).drop_duplicates("utility_code")
    us = usj[usj["pop"] >= 50000].sort_values("distance")
    lines += [
        "### United States (utilities, measured, 2012 to 2019 alkalinity)",
        "",
        "| rank | city (utility) | people served | alkalinity | hardness | distance |",
        "|---|---|---|---|---|---|",
    ]
    for i, (_, r) in enumerate(us.head(15).iterrows(), start=1):
        lines.append(
            f"| {i} | {r['locality']}, {r['admin1']} ({r['utility']}) | {r['pop']:,.0f} | {r['alk']:.0f} | {fmt(r['hard'])} | {r['distance']:.2f} |"
        )
    big = usj[usj["pop"] >= 500000].sort_values("distance")
    lines += [
        "",
        "Largest US utilities (over 500,000 served), closest first:",
        "",
        "| city (utility) | people served | alkalinity | hardness | band |",
        "|---|---|---|---|---|",
    ]
    for _, r in big.head(25).iterrows():
        band = int(np.digitize(r["alk"], [40, 80, 150, 250]) + 1)
        lines.append(
            f"| {r['locality']}, {r['admin1']} ({r['utility']}) | {r['pop']:,.0f} | {r['alk']:.0f} | {fmt(r['hard'])} | {band} |"
        )
    # Brazil
    br = t[(t["country_iso2"] == "BR") & (t["pop"] >= 50000) & t["hard"].notna()].sort_values(
        "distance"
    )
    lines += [
        "",
        "### Brazil (municipalities; alkalinity IMPUTED from hardness and source type, error band ×/÷1.7)",
        "",
        "| rank | municipality | residents | alkalinity (imputed) | hardness (measured) | distance |",
        "|---|---|---|---|---|---|",
    ]
    for i, (_, r) in enumerate(br.head(15).iterrows(), start=1):
        lines.append(
            f"| {i} | {r['locality']}, {r['admin1']} | {r['pop']:,.0f} | {r['alk']:.0f} | {fmt(r['hard'])} | {r['distance']:.2f} |"
        )
    bigbr = t[(t["country_iso2"] == "BR") & (t["pop"] >= 1000000)].sort_values("distance")
    lines += [
        "",
        "Brazilian cities over 1 million residents, closest first (imputed alkalinity):",
        "",
        "| municipality | residents | alkalinity (imputed) | hardness | band |",
        "|---|---|---|---|---|",
    ]
    for _, r in bigbr.iterrows():
        band = int(np.digitize(r["alk"], [40, 80, 150, 250]) + 1)
        lines.append(
            f"| {r['locality']}, {r['admin1']} | {r['pop']:,.0f} | {r['alk']:.0f} | {fmt(r['hard'])} | {band} |"
        )
    # England by utility
    gb = t[(t["country_iso2"] == "GB") & t["alk_measured"].notna()].copy()
    if len(gb):
        gu = gb.groupby("utility").apply(
            lambda g: pd.Series(
                {
                    "areas": len(g),
                    "alk_median": np.average(g["alk"], weights=g["pop"].fillna(1500)),
                    "hard_median": np.nanmedian(g["hard"]),
                }
            )
        )
        gu["distance"] = distance(gu["alk_median"], gu["hard_median"])
        lines += [
            "",
            "### England and Northern Ireland (by water company, population-weighted mean of small areas)",
            "",
            "| company | small areas | alkalinity | hardness | distance |",
            "|---|---|---|---|---|",
        ]
        for name, r in gu.sort_values("distance").iterrows():
            lines.append(
                f"| {name} | {int(r['areas'])} | {r['alk_median']:.0f} | {fmt(r['hard_median'])} | {r['distance']:.2f} |"
            )
    return "\n".join(lines) + "\n"


def main() -> None:
    w = load()
    doc_b, paper_b = bottled_tables(w)
    doc_t = tap_tables(w)
    head = [
        "# Rankings: waters closest to the SCA reference (40 mg/L alkalinity, 68 mg/L hardness as CaCO3)",
        "",
        "Generated by scripts/rankings.py from data/processed/atlas_v0_wide.parquet.",
        "",
        '"Closest to the reference" means the water brews a light or medium roast most like the model\'s reference; it is the',
        "preference of the acidity-liking minority cluster in Cotter et al. 2021, not a universal quality ranking. The majority",
        "cluster, which dislikes sourness, would rank higher-alkalinity waters better for light roasts.",
        "",
    ]
    (ROOT / "docs" / "rankings.md").write_text("\n".join(head) + "\n" + doc_b + "\n" + doc_t)
    (ROOT / "paper" / "tables" / "bottled_reference.md").write_text(paper_b)
    print("wrote docs/rankings.md and paper/tables/bottled_reference.md")


if __name__ == "__main__":
    main()
