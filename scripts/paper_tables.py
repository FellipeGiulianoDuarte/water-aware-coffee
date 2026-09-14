"""Generate the paper's tables as Markdown from data/processed/*.csv so nothing is typed by hand.

Run after `wac atlas && wac bands`:  uv run python scripts/paper_tables.py
Writes paper/tables/*.md (included from paper/paper.qmd) and copies the figures into paper/figures/.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pandas as pd

from water_aware_coffee.atlas.bands import BAND_EDGES
from water_aware_coffee.model.params import ROASTS
from water_aware_coffee.model.sensory import AdditiveSensory, rules_table

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
OUT = ROOT / "paper" / "tables"


def md_table(df: pd.DataFrame, caption: str, label: str) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(str(v) for v in r.tolist()) + " |")
    lines.append("")
    lines.append(f": {caption} {{#tbl-{label}}}")
    return "\n".join(lines) + "\n"


def sources_table() -> str:
    w = pd.read_parquet(PROC / "atlas_v0_wide.parquet")
    w["alk"] = pd.to_numeric(w["alkalinity_median"], errors="coerce")
    w["hard"] = pd.to_numeric(w["hardness_best"], errors="coerce")
    rows = []
    names = {
        "sisagua-br": ("Brazil, SISAGUA semestral control (Ministério da Saúde)", "CC BY"),
        "tapwaterdata-us": ("United States, TapWaterData compiled city hardness", "CC BY 4.0"),
        "epa-syr4-us": (
            "United States, EPA Six-Year Review 4 finished-water monitoring 2012 to 2019",
            "public domain",
        ),
        "tapwaterdata-us+epa-syr4-us": (
            "United States, the two above joined on utility id",
            "derived",
        ),
        "uk-stream": (
            "England, water-industry open-data hub (Wessex, Southern, Yorkshire)",
            "CC BY 4.0",
        ),
        "uk-ni-water": ("Northern Ireland Water customer-tap results", "OGL v3"),
        "bottled-labels": (
            "Bottled waters, label compositions (7 countries)",
            "CC BY 4.0 compilation",
        ),
    }
    order = [
        "sisagua-br",
        "tapwaterdata-us",
        "epa-syr4-us",
        "tapwaterdata-us+epa-syr4-us",
        "uk-stream",
        "uk-ni-water",
        "bottled-labels",
    ]
    for sid in order:
        g = w[w["source_id"] == sid]
        if len(g) == 0:
            continue
        name, lic = names.get(str(sid), (str(sid), ""))
        rows.append(
            {
                "source": name,
                "localities": f"{len(g):,}",
                "with hardness": f"{int(g['hard'].notna().sum()):,}",
                "with alkalinity": f"{int(g['alk'].notna().sum()):,}",
                "licence": lic,
            }
        )
    df = pd.DataFrame(rows)
    return md_table(
        df,
        "Sources in atlas v0. A locality is a city, utility, small area, municipality or bottled product; counts are after aggregation to one row per locality.",
        "sources",
    )


def params_table() -> str:
    rows = []
    for r in ROASTS:
        rows.append(
            {
                "roast": r.name,
                "titratable acidity, meq/L (measured, TDS 1.25 %)": f"{r.ta_ref_meq_l:.2f}",
                "range": f"{r.ta_low:.1f} to {r.ta_high:.1f}",
                "intrinsic (brew water alkalinity added back)": f"{r.intrinsic_ta():.2f}",
                "brew pH": f"{r.brew_ph:.2f}",
                "protonated share of bicarbonate": f"{1 / (1 + 10 ** (r.brew_ph - 6.35)):.3f}",
            }
        )
    return md_table(
        pd.DataFrame(rows),
        "Model parameters per roast bin, from Batali et al. (2021) Table 1 and Supplemental Figure 1. The brew water in that study had 32 mg/L alkalinity as CaCO~3~ (computed from the printed recipe).",
        "params",
    )


def bands_table() -> str:
    s = pd.read_csv(PROC / "bands_v0_summary.csv")
    rows = []
    for _, r in s.iterrows():
        within = ast.literal_eval(r["share_of_each_country_in_this_band"])
        rows.append(
            {
                "band (mg/L as CaCO~3~)": r["name"].split(" (")[1].rstrip(")"),
                "name": r["name"].split(" (")[0],
                "localities": f"{int(r['localities']):,}",
                "share of people, all": f"{r['population_share']:.0%}",
                "share of people, measured only": f"{r['population_share_measured_only']:.0%}",
                "US": f"{within.get('US', 0):.0%}",
                "England": f"{within.get('GB', 0):.0%}",
                "Brazil (imputed)": f"{within.get('BR', 0):.0%}",
                "median alkalinity": f"{r['alkalinity_median']:.0f}",
                "median hardness": f"{r['hardness_median']:.0f}",
            }
        )
    return md_table(
        pd.DataFrame(rows),
        "Alkalinity bands and who brews with them. Population-weighted; 'measured only' excludes Brazil, whose alkalinity is imputed. Country columns give the share of that country's population in the band.",
        "bands",
    )


def matching_table() -> str:
    m = pd.read_csv(PROC / "matching_bands_v0.csv")
    piv = m.pivot(index="band", columns="roast", values="relative_residual_at_median")
    lab = m.pivot(index="band", columns="roast", values="label_at_median")
    rows = []
    for b in piv.index:
        row = {"band": int(b)}
        for roast in ("light", "medium", "dark"):
            row[f"{roast} roast"] = f"{piv.loc[b, roast]:.2f} ({lab.loc[b, roast]})"
        rows.append(row)
    return md_table(
        pd.DataFrame(rows),
        "Matching table v0: residual acidity at each band's median water relative to the SCA reference water (40 mg/L alkalinity, 68 mg/L hardness). 0.75 to 1.25 = works; 0.5 to 0.75 = compensate; below 0.5 = fights.",
        "matching",
    )


def rules_table_md() -> str:
    sens = AdditiveSensory.from_frost_csv()
    t = rules_table(sens, alkalinities=(20, 40, 80, 120, 150, 200, 250))
    t = t[t["roast"] == "light"]
    rows = []
    for _, r in t.iterrows():
        rows.append(
            {
                "alkalinity, mg/L": f"{r['alkalinity_mgl']:.0f}",
                "acid neutralised vs reference, meq/L": f"{r['acid_neutralised_meq_vs_ref']:+.2f}",
                "predicted sourness change (0 to 100)": f"{r['sourness_change_points']:+.1f}",
                "extra coffee, chemistry to sensory estimate": f"{r['dose_change_percent_chemistry']:+.0f} to {r['dose_change_percent_sensory']:+.0f} %",
                "bitterness side effect": f"{r['bitterness_side_effect_tds_route']:+.1f}",
                "or blend with zero-alkalinity water": f"{100 * r['dilution_share_zero_alkalinity_water']:.0f} %",
            }
        )
    return md_table(
        pd.DataFrame(rows),
        "Dial-in rules v0 for a light roast at TDS 1.25 % and 20 % extraction. Medium and dark roasts differ by under 10 % in every column (full table in the repository).",
        "rules",
    )


def bottled_table() -> str:
    w = pd.read_parquet(PROC / "atlas_v0_wide.parquet")
    b = w[w["source_id"] == "bottled-labels"].copy()
    b["alk"] = pd.to_numeric(b["alkalinity_median"], errors="coerce")
    b = b.dropna(subset=["alk"])
    roles = [
        ("diluent (under 15)", b["alk"] < 15),
        ("bright (15 to 25)", (b["alk"] >= 15) & (b["alk"] < 25)),
        ("reference-like (25 to 60)", (b["alk"] >= 25) & (b["alk"] <= 60)),
        ("moderate (60 to 150)", (b["alk"] > 60) & (b["alk"] <= 150)),
        ("as flat as hard tap water (over 150)", b["alk"] > 150),
    ]
    rows = []
    for name, mask in roles:
        g = b[mask]
        by = g.groupby("country_iso2").size()
        rows.append(
            {
                "role (alkalinity, mg/L as CaCO~3~)": name,
                "products": len(g),
                **{c: int(by.get(c, 0)) for c in ["BR", "US", "GB", "DE", "FR", "IT", "PT"]},
            }
        )
    return md_table(
        pd.DataFrame(rows),
        f"Bottled waters by brewing role, {len(b)} products with bicarbonate or alkalinity printed on the label.",
        "bottled",
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "sources.md").write_text(sources_table())
    (OUT / "params.md").write_text(params_table())
    (OUT / "bands.md").write_text(bands_table())
    (OUT / "matching.md").write_text(matching_table())
    (OUT / "rules.md").write_text(rules_table_md())
    (OUT / "bottled.md").write_text(bottled_table())
    # Paper figures are rendered without in-figure titles by `python scripts/figures.py --paper`.
    edges = [e for e in BAND_EDGES if 0 < e < float("inf")]
    print("tables written:", sorted(p.name for p in OUT.glob("*.md")), "band edges", edges)


if __name__ == "__main__":
    main()
