"""Water regimes as fixed alkalinity bands (decisions.md item 29).

Bands are round numbers in mg/L as CaCO3, chosen for brewers, not fitted. For each band edge we
report the share of a light roast's acidity the model says is neutralised, so the bands can be
read against the mechanism. A "softened" flag marks water where hardness has been removed but
alkalinity kept (ion-exchange softeners): hardness below 30 while alkalinity above 60.

The Gaussian-mixture analysis in regimes.py remains available as an alternative view.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from water_aware_coffee.atlas.regimes import (
    REF_ALK,
    REF_HARD,
    clustering_frame,
    label_rule,
    wmedian,
)
from water_aware_coffee.model.grid import (
    CationParams,
    Grid,
    RoastParams,
    acid_lost_fraction,
    relative_residual,
)
from water_aware_coffee.model.params import CATIONS, LIGHT, ROASTS

BAND_EDGES = (0.0, 40.0, 80.0, 150.0, 250.0, np.inf)
BAND_NAMES = (
    "very low alkalinity (0 to 40)",
    "low alkalinity (40 to 80)",
    "moderate alkalinity (80 to 150)",
    "high alkalinity (150 to 250)",
    "very high alkalinity (over 250)",
)
SOFTENED_MAX_HARDNESS = 30.0
SOFTENED_MIN_ALKALINITY = 60.0


def assign_band(alk: pd.Series) -> pd.Series:
    idx = np.digitize(alk.to_numpy(dtype=float), BAND_EDGES[1:-1], right=False)
    return pd.Series(idx + 1, index=alk.index, name="band")


def softened_flag(alk: pd.Series, hard: pd.Series) -> pd.Series:
    return (hard < SOFTENED_MAX_HARDNESS) & (alk > SOFTENED_MIN_ALKALINITY)


def band_frame(wide: pd.DataFrame) -> pd.DataFrame:
    """Localities with hardness and measured-or-imputed alkalinity, with band and softened flag."""
    d = clustering_frame(wide)
    d["band"] = assign_band(d["alk"])
    d["band_name"] = d["band"].map(dict(enumerate(BAND_NAMES, start=1)))
    d["softened"] = softened_flag(d["alk"], d["hard"])
    return d


def edge_acid_loss(roast: RoastParams = LIGHT) -> pd.DataFrame:
    """Share of the roast's acidity neutralised at each finite band edge."""
    edges = [e for e in BAND_EDGES if np.isfinite(e) and e > 0]
    grid = Grid(alkalinity_mgl=np.array(edges), hardness_mgl=np.array([0.0]))
    lost = acid_lost_fraction(roast, grid)[:, 0]
    return pd.DataFrame({"alkalinity_edge_mgl": edges, f"acid_lost_share_{roast.name}": lost})


def band_summary(d: pd.DataFrame) -> pd.DataFrame:
    total_w = d["weight"].sum()
    rows = []
    for b in range(1, len(BAND_NAMES) + 1):
        g = d[d["band"] == b]
        if len(g) == 0:
            continue
        by_country = (g.groupby("country_iso2")["weight"].sum() / g["weight"].sum()).round(3)
        within_country = {
            cc: float(
                g.loc[g["country_iso2"] == cc, "weight"].sum()
                / d.loc[d["country_iso2"] == cc, "weight"].sum()
            )
            for cc in sorted(d["country_iso2"].unique())
        }
        measured = g[~g["alkalinity_imputed"].astype(bool)]
        top = g.sort_values("weight", ascending=False).head(5)
        rows.append(
            {
                "band": b,
                "name": BAND_NAMES[b - 1],
                "localities": len(g),
                "population_share": g["weight"].sum() / total_w,
                "population_share_measured_only": (
                    measured["weight"].sum()
                    / d.loc[~d["alkalinity_imputed"].astype(bool), "weight"].sum()
                ),
                "alkalinity_median": wmedian(g["alk"], g["weight"]),
                "alkalinity_p10": wmedian(g["alk"], g["weight"], 0.1),
                "alkalinity_p90": wmedian(g["alk"], g["weight"], 0.9),
                "hardness_median": wmedian(g["hard"], g["weight"]),
                "share_softened": float((g["softened"] * g["weight"]).sum() / g["weight"].sum()),
                "share_imputed_alkalinity": g["alkalinity_imputed"].astype(bool).mean(),
                "population_share_by_country_within_band": by_country.to_dict(),
                "share_of_each_country_in_this_band": {
                    k: round(v, 3) for k, v in within_country.items()
                },
                "examples_by_population": "; ".join(
                    f"{loc} ({cc})"
                    for loc, cc in zip(top["locality"], top["country_iso2"], strict=True)
                ),
            }
        )
    return pd.DataFrame(rows)


def band_matching(summary: pd.DataFrame, cations: CationParams = CATIONS) -> pd.DataFrame:
    """Band × roast: relative residual acidity at the band's population-weighted median water,
    at its p10 and p90 alkalinity, and at the band edges."""
    rows = []
    for _, reg in summary.iterrows():
        b = int(reg["band"])
        lo_edge, hi_edge = BAND_EDGES[b - 1], BAND_EDGES[b]
        for r in ROASTS:

            def rel(
                alk: float, hard: float, which: str = "central", roast: RoastParams = r
            ) -> float:
                g = Grid(alkalinity_mgl=np.array([alk]), hardness_mgl=np.array([hard]))
                return float(relative_residual(roast, g, cations, REF_ALK, REF_HARD, which)[0, 0])

            central = rel(reg["alkalinity_median"], reg["hardness_median"])
            rows.append(
                {
                    "band": b,
                    "band_name": reg["name"],
                    "roast": r.name,
                    "relative_residual_at_median": central,
                    "relative_residual_at_p10_alk": rel(
                        reg["alkalinity_p10"], reg["hardness_median"]
                    ),
                    "relative_residual_at_p90_alk": rel(
                        reg["alkalinity_p90"], reg["hardness_median"]
                    ),
                    "relative_residual_at_lower_edge": rel(
                        max(lo_edge, 1.0), reg["hardness_median"]
                    ),
                    "relative_residual_at_upper_edge": (
                        rel(hi_edge, reg["hardness_median"]) if np.isfinite(hi_edge) else np.nan
                    ),
                    "relative_residual_param_low": min(
                        rel(reg["alkalinity_median"], reg["hardness_median"], "low"),
                        rel(reg["alkalinity_median"], reg["hardness_median"], "high"),
                    ),
                    "relative_residual_param_high": max(
                        rel(reg["alkalinity_median"], reg["hardness_median"], "low"),
                        rel(reg["alkalinity_median"], reg["hardness_median"], "high"),
                    ),
                    "label_at_median": label_rule(central),
                    "label_at_upper_edge": (
                        label_rule(rel(hi_edge, reg["hardness_median"]))
                        if np.isfinite(hi_edge)
                        else "n/a"
                    ),
                }
            )
    return pd.DataFrame(rows)


def build_bands(
    wide: pd.DataFrame, out_dir: Path
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    d = band_frame(wide)
    summary = band_summary(d)
    match = band_matching(summary)
    out_dir.mkdir(parents=True, exist_ok=True)
    d[
        [
            "source_id",
            "country_iso2",
            "admin1",
            "locality_key",
            "locality",
            "alk",
            "hard",
            "alkalinity_imputed",
            "weight",
            "population_known",
            "band",
            "band_name",
            "softened",
        ]
    ].to_parquet(out_dir / "bands_v0_localities.parquet", index=False)
    summary.to_csv(out_dir / "bands_v0_summary.csv", index=False)
    match.to_csv(out_dir / "matching_bands_v0.csv", index=False)
    edge_acid_loss().to_csv(out_dir / "bands_v0_edges.csv", index=False)
    return d, summary, match
