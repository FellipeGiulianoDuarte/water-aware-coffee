"""Task 3 plots and effect-size table.

Run after `uv run wac build --all && uv run wac atlas`:
    uv run python scripts/plot_task3_grid.py
Writes docs/figures/task3_acid_neutralised.png, docs/figures/task3_grid.png, docs/task3_results.md.

Colours follow the project data-viz palette: categorical slots 1 to 3 (blue, orange, aqua) for
light / medium / dark roast, one-hue sequential for magnitude, text in ink tokens.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from water_aware_coffee.model.grid import (  # noqa: E402
    CationParams,
    Grid,
    acid_lost_fraction,
    relative_residual,
)
from water_aware_coffee.model.params import CATIONS, ROASTS  # noqa: E402
from water_aware_coffee.units import EQ_CACO3  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ATLAS = ROOT / "data" / "processed" / "atlas_v0_wide.parquet"
FIG = ROOT / "docs" / "figures"
OUT_MD = ROOT / "docs" / "task3_results.md"

SERIES = {"light": "#2a78d6", "medium": "#eb6834", "dark": "#1baf7a"}
INK = "#0b0b0b"
INK2 = "#52514e"
GRIDC = "#e6e5e1"
SURFACE = "#fcfcfb"
SCA_ALK = 40.0

plt.rcParams.update(
    {
        "font.size": 10,
        "axes.edgecolor": INK2,
        "axes.labelcolor": INK,
        "xtick.color": INK2,
        "ytick.color": INK2,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
    }
)


def load_waters() -> pd.DataFrame:
    w = pd.read_parquet(ATLAS)
    w = w.rename(columns={"alkalinity_median": "alk", "hardness_best": "hard"})
    w["alk"] = pd.to_numeric(w["alk"], errors="coerce")
    w["hard"] = pd.to_numeric(w["hard"], errors="coerce")
    return w


def fig_neutralised(waters: pd.DataFrame) -> None:
    alk_axis = np.linspace(0, 300, 301)
    grid = Grid(alkalinity_mgl=alk_axis, hardness_mgl=np.array([0.0]))
    fig, (ax, axh) = plt.subplots(
        2, 1, figsize=(8.5, 6.2), sharex=True, gridspec_kw={"height_ratios": [3, 1], "hspace": 0.08}
    )
    for r in ROASTS:
        c = SERIES[r.name]
        central = acid_lost_fraction(r, grid)[:, 0]
        lo = r.brew_ph  # same pH for band; band comes from TA range
        f = central * r.ta_ref_meq_l  # neutralised meq/L
        band_low = f / r.ta_high
        band_high = f / r.ta_low
        ax.fill_between(alk_axis, band_low, band_high, color=c, alpha=0.15, linewidth=0)
        ax.plot(alk_axis, central, color=c, linewidth=2)
        # direct label at the right end
        ax.annotate(
            f"{r.name} roast (TA {r.ta_ref_meq_l:g} meq/L)",
            xy=(alk_axis[-1], central[-1]),
            xytext=(4, 0),
            textcoords="offset points",
            va="center",
            color=INK,
            fontsize=9,
        )
        del lo
    ax.axvline(SCA_ALK, color=INK2, linewidth=1, linestyle=":")
    ax.text(SCA_ALK + 3, 0.97, "SCA target 40 mg/L", color=INK2, fontsize=8, va="top")
    for y, lab in ((0.25, "a quarter of the acidity gone"), (0.5, "half gone")):
        ax.axhline(y, color=GRIDC, linewidth=1, zorder=0)
        ax.text(298, y + 0.012, lab, color=INK2, fontsize=8, ha="right")
    ax.set_ylim(0, 1.0)
    ax.set_xlim(0, 300)
    ax.set_ylabel("share of brew titratable acidity neutralised")
    ax.set_title(
        "How much of a coffee's acidity does the water's bicarbonate cancel?\n"
        "Model: neutralised = f(pH) × alkalinity / titratable acidity; bands = literature TA range",
        loc="left",
        color=INK,
        fontsize=11,
    )
    ax.grid(axis="y", color=GRIDC, linewidth=0.8)
    ax.set_axisbelow(True)

    alk = waters["alk"].dropna()
    alk = alk[(alk >= 0) & (alk <= 300)]
    axh.hist(alk, bins=60, range=(0, 300), color="#9c9b96", edgecolor=SURFACE, linewidth=0.5)
    axh.set_ylabel("localities")
    axh.set_xlabel("water alkalinity, mg/L as CaCO3 (finished water, locality median)")
    axh.grid(axis="y", color=GRIDC, linewidth=0.8)
    axh.set_axisbelow(True)
    n_total = int(waters["alk"].notna().sum())
    n_over = int((waters["alk"] > 300).sum())
    axh.text(
        298,
        axh.get_ylim()[1] * 0.9,
        f"{n_total:,} localities with alkalinity (US utilities 2012-2019, UK small areas); "
        f"{n_over:,} above 300 not shown",
        ha="right",
        va="top",
        color=INK2,
        fontsize=8,
    )
    fig.subplots_adjust(left=0.09, right=0.78, top=0.88, bottom=0.1)
    fig.savefig(FIG / "task3_acid_neutralised.png", dpi=160)
    plt.close(fig)


def fig_grid(waters: pd.DataFrame) -> None:
    grid = Grid(alkalinity_mgl=np.linspace(0, 300, 121), hardness_mgl=np.linspace(0, 400, 121))
    both = waters.dropna(subset=["alk", "hard"])
    both = both[(both["alk"] <= 300) & (both["hard"] <= 400)]
    fig, axes = plt.subplots(2, 3, figsize=(12, 7.2), sharex=True, sharey=True)
    cmap = matplotlib.colormaps["Blues_r"]
    levels = np.linspace(0.0, 1.5, 16)
    for row, (label, cat) in enumerate(
        (
            ("cation term = 0 (central)", CationParams(0.0, 0.0, 0.0)),
            (f"cation term at upper bound (β={CATIONS.beta_high:g}/meq)", CATIONS),
        )
    ):
        for col, r in enumerate(ROASTS):
            ax = axes[row, col]
            which = "central" if row == 0 else "high"
            rel = relative_residual(r, grid, cat, which=which)
            X, Y = np.meshgrid(grid.hardness_mgl, grid.alkalinity_mgl)
            cf = ax.contourf(X, Y, rel, levels=levels, cmap=cmap, extend="both")
            cs = ax.contour(
                X,
                Y,
                rel,
                levels=[0.5, 0.75, 1.0],
                colors=[INK2, INK2, INK],
                linewidths=[0.8, 0.8, 1.4],
            )
            ax.clabel(cs, fmt={0.5: "0.5", 0.75: "0.75", 1.0: "1.0"}, fontsize=8, colors=INK)
            ax.scatter(
                both["hard"], both["alk"], s=4, color="#e34948", alpha=0.35, linewidths=0, zorder=3
            )
            ax.scatter([68], [40], marker="*", s=90, color=INK, zorder=4)
            if row == 0:
                ax.set_title(f"{r.name} roast", color=SERIES[r.name], fontsize=11, loc="left")
            if col == 0:
                ax.set_ylabel(f"{label}\n\nalkalinity, mg/L as CaCO3", color=INK)
            if row == 1:
                ax.set_xlabel("hardness, mg/L as CaCO3")
            ax.grid(color=GRIDC, linewidth=0.6)
            ax.set_axisbelow(True)
    cbar = fig.colorbar(cf, ax=axes, shrink=0.8, pad=0.02)
    cbar.set_label("residual acidity relative to SCA reference water (★ 40 alk / 68 hard)")
    fig.suptitle(
        "Residual acidity across the alkalinity × hardness grid. Red dots: "
        f"{len(both):,} real localities with both values (finished water). Contours at 0.5, 0.75, 1.0.",
        x=0.01,
        ha="left",
        color=INK,
        fontsize=11,
    )
    fig.savefig(FIG / "task3_grid.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def results_table(waters: pd.DataFrame) -> str:
    alk = waters["alk"].dropna()
    lines = [
        "# Task 3 results: is the alkalinity effect big enough to matter?",
        "",
        "Generated by scripts/plot_task3_grid.py from data/processed/atlas_v0_wide.parquet and",
        "src/water_aware_coffee/model/params.py. Figures: docs/figures/task3_acid_neutralised.png,",
        "docs/figures/task3_grid.png.",
        "",
        f"Localities with a finished-water alkalinity median: {len(alk):,} "
        f"(by source: {waters.dropna(subset=['alk']).groupby('source_id').size().to_dict()}).",
        f"Alkalinity distribution, mg/L as CaCO3: p10 {alk.quantile(0.1):.0f}, p25 {alk.quantile(0.25):.0f}, "
        f"median {alk.median():.0f}, p75 {alk.quantile(0.75):.0f}, p90 {alk.quantile(0.9):.0f}.",
        "",
        "Share of the brew's titratable acidity neutralised by the water (central TA per roast bin,",
        "bicarbonate protonation fraction at the bin's brew pH):",
        "",
        "| roast | TA central (meq/L) | neutralised at SCA 40 mg/L | at median water | at p75 water | at p90 water |"
        " share of localities losing > 25 % | > 50 % |",
        "|---|---|---|---|---|---|---|---|",
    ]
    from water_aware_coffee.model.grid import bicarbonate_protonated_fraction as fprot

    for r in ROASTS:
        f = fprot(r.brew_ph)

        def lost(a: float, f: float = f, ta: float = r.ta_ref_meq_l) -> float:
            return f * (a / EQ_CACO3) / ta

        lost_all = alk.map(lambda a, r=r, f=f: f * (a / EQ_CACO3) / r.ta_ref_meq_l)
        lines.append(
            f"| {r.name} | {r.ta_ref_meq_l:g} | {lost(SCA_ALK):.0%} | {lost(alk.median()):.0%} | "
            f"{lost(alk.quantile(0.75)):.0%} | {lost(alk.quantile(0.9)):.0%} | "
            f"{(lost_all > 0.25).mean():.0%} | {(lost_all > 0.5).mean():.0%} |"
        )
    lines += [
        "",
        "Reading: at the SCA target the water removes roughly a sixth of a light roast's acidity; at the",
        "median real water it removes more; and for the roughly one quarter of localities above the p75",
        "the light-roast column approaches or passes one half. The dark-roast column is systematically",
        "higher because dark roasts start with less acid: the same water flattens a dark roast more, in",
        "relative terms, but a dark roast has less brightness to lose.",
        "",
        "Caveats that apply to every number above: TA values are derived from immersion-brew papers",
        "titrated to pH 8.2 and scaled to 1.25 percent TDS (docs/literature/titratable_acidity_by_roast.md);",
        "US alkalinity is 2012 to 2019 and its CaCO3 basis is assumed; UK Southern Water alkalinity basis",
        "is assumed; the model is stoichiometric with no measured coffee data on the alkalinity slope.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    waters = load_waters()
    fig_neutralised(waters)
    fig_grid(waters)
    OUT_MD.write_text(results_table(waters))
    print(OUT_MD.read_text())


if __name__ == "__main__":
    main()
