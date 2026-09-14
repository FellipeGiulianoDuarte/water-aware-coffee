"""Paper figures, built to the project data-viz procedure (decisions.md item 33).

Run after `uv run wac build --all && uv run wac atlas && uv run wac bands`:
    uv run python scripts/figures.py
Writes docs/figures/fig1_acid_neutralised.png ... fig5_bottled.png (PNG 200 dpi) and SVG twins.

Conventions (from the data-viz references):
- one job per chart; one axis per chart; small multiples instead of a second axis
- categorical identity in fixed slot order: light roast slot 1 (blue), medium slot 2 (orange),
  dark slot 3 (aqua); countries US slot 1, England slot 2, Brazil slot 3 (never on the same chart
  as roasts). Three slots validate all-pairs on the light surface.
- magnitude in one hue (blue ramp); de-emphasis in gray
- 2 px lines, >= 8 px markers with a surface ring, bars <= 24 px with a 2 px surface gap,
  hairline solid grid one step off the surface, text in ink tokens never in series colour
- a legend whenever two or more series; sparse direct labels
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import sys  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib import ticker  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

from water_aware_coffee.atlas.bands import BAND_EDGES, BAND_NAMES  # noqa: E402
from water_aware_coffee.model.grid import Grid, acid_lost_fraction  # noqa: E402
from water_aware_coffee.model.params import ROASTS  # noqa: E402
from water_aware_coffee.model.sensory import AdditiveSensory, rules_table  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
PAPER_MODE = "--paper" in sys.argv  # paper figures: no in-figure titles, captions carry the text
FIG = ROOT / ("paper" if PAPER_MODE else "docs") / "figures"

# Palette instance (references/palette.md): categorical slots 1..3, blue ramp, chrome.
SLOT = ["#2a78d6", "#eb6834", "#1baf7a"]
BLUE = {
    100: "#cde2fb",
    200: "#9ec5f4",
    300: "#6da7ec",
    400: "#3987e5",
    500: "#256abf",
    600: "#184f95",
}
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
DEEMPH = "#c3c2b7"

ROAST_COLOUR = {r.name: SLOT[i] for i, r in enumerate(ROASTS)}
COUNTRY_ORDER = ["US", "GB", "BR"]
COUNTRY_COLOUR = dict(zip(COUNTRY_ORDER, SLOT, strict=True))
COUNTRY_LABEL = {
    "US": "United States (measured, 3,341 cities)",
    "GB": "England (measured, 3 water companies)",
    "BR": "Brazil (alkalinity imputed, 2,441 municipalities)",
}

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
        "font.size": 9.5,
        "axes.titlesize": 10.5,
        "axes.labelsize": 9.5,
        "axes.edgecolor": AXIS,
        "axes.linewidth": 0.8,
        "axes.labelcolor": INK2,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelsize": 8.5,
        "ytick.labelsize": 8.5,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "grid.linestyle": "-",
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "legend.frameon": False,
        "legend.fontsize": 8.5,
    }
)


def _title(ax: plt.Axes, title: str, subtitle: str | None = None) -> None:
    ax.set_title("")
    if PAPER_MODE:
        return
    y = 1.075 if subtitle else 1.02
    ax.text(
        0,
        y,
        title,
        transform=ax.transAxes,
        color=INK,
        fontsize=10.5,
        fontweight="bold",
        va="bottom",
    )
    if subtitle:
        ax.text(0, 1.02, subtitle, transform=ax.transAxes, color=INK2, fontsize=8.3, va="bottom")


def _save(fig: plt.Figure, name: str) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f"{name}.png", dpi=200, bbox_inches="tight", pad_inches=0.15)
    fig.savefig(FIG / f"{name}.svg", bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)


def _rounded_bar(ax: plt.Axes, x: float, height: float, width: float, colour: str) -> None:
    """Bar with a 4 px rounded data end and a square baseline (FancyBboxPatch in data units)."""
    if height <= 0:
        return
    r = min(width * 0.35, height * 0.5)
    patch = FancyBboxPatch(
        (x - width / 2, 0),
        width,
        height,
        boxstyle=f"round,pad=0,rounding_size={r}",
        linewidth=0,
        facecolor=colour,
        mutation_aspect=1,
    )
    ax.add_patch(patch)
    # square the baseline by covering the bottom rounding with a plain rectangle
    ax.add_patch(
        matplotlib.patches.Rectangle(
            (x - width / 2, 0), width, min(r, height), linewidth=0, facecolor=colour
        )
    )


def load_atlas() -> pd.DataFrame:
    w = pd.read_parquet(PROC / "atlas_v0_wide.parquet")
    for c in ["alkalinity_best", "alkalinity_median", "hardness_best", "population", "ph_median"]:
        if c in w.columns:
            w[c] = pd.to_numeric(w[c], errors="coerce").astype("float64")
    return w


# ----------------------------------------------------------------------------------------------
# Figure 1: share of acidity neutralised vs alkalinity, three roasts; population histogram below
# ----------------------------------------------------------------------------------------------
def fig1(w: pd.DataFrame) -> None:
    alk_axis = np.linspace(0, 300, 301)
    grid = Grid(alkalinity_mgl=alk_axis, hardness_mgl=np.array([0.0]))
    fig, (ax, axh) = plt.subplots(
        2,
        1,
        figsize=(7.2, 5.4),
        sharex=True,
        gridspec_kw={"height_ratios": [3.2, 1], "hspace": 0.12},
    )
    handles = []
    for r in ROASTS:
        c = ROAST_COLOUR[r.name]
        central = acid_lost_fraction(r, grid)[:, 0]
        ta_c = r.intrinsic_ta()
        lo = central * ta_c / r.intrinsic_ta("high")
        hi = central * ta_c / r.intrinsic_ta("low")
        ax.fill_between(alk_axis, lo, hi, color=c, alpha=0.10, linewidth=0)
        (h,) = ax.plot(
            alk_axis, central, color=c, linewidth=2, solid_capstyle="round", label=f"{r.name} roast"
        )
        handles.append(h)
        ax.annotate(
            f"{r.name}",
            xy=(alk_axis[-1], central[-1]),
            xytext=(5, 0),
            textcoords="offset points",
            va="center",
            color=INK2,
            fontsize=8.5,
        )
    for e in [e for e in BAND_EDGES if 0 < e < np.inf]:
        ax.axvline(e, color=GRID, linewidth=0.8, zorder=0)
        axh.axvline(e, color=GRID, linewidth=0.8, zorder=0)
    ax.axvline(40, color=AXIS, linewidth=0.8, zorder=0)
    ax.text(42, 0.585, "SCA target", color=MUTED, fontsize=8, va="top")
    ax.set_ylim(0, 0.6)
    ax.set_xlim(0, 300)
    ax.yaxis.set_major_formatter(ticker.PercentFormatter(1.0, decimals=0))
    ax.set_ylabel("share of the brew's acidity neutralised")
    ax.legend(handles=handles, loc="lower right")
    _title(
        ax,
        "Bicarbonate in the water cancels part of the coffee's acidity",
        "Model: neutralised share = protonated fraction × alkalinity ÷ titratable acidity. "
        "Band = titratable acidity range from Batali et al. 2021.",
    )

    tap = w[
        (w["source_id"] != "bottled-labels") & (w["source_id"] != "tapwaterdata-us+epa-syr4-us")
    ]
    tap = tap.dropna(subset=["alkalinity_median", "population"])
    tap = tap[tap["population"] > 0]
    weights = tap["population"] / tap["population"].sum()
    over = float(weights[tap["alkalinity_median"] > 300].sum())
    axh.hist(
        tap["alkalinity_median"],
        bins=60,
        range=(0, 300),
        weights=weights,
        color=DEEMPH,
        edgecolor=SURFACE,
        linewidth=0.6,
    )
    axh.yaxis.set_major_formatter(ticker.PercentFormatter(1.0, decimals=0))
    axh.set_ylabel("people")
    axh.set_xlabel("water alkalinity, mg/L as CaCO3")
    axh.text(
        298,
        axh.get_ylim()[1] * 0.92,
        f"{tap['population'].sum() / 1e6:.0f} M people, US and England utilities with measured alkalinity; "
        f"{over:.0%} above 300",
        ha="right",
        va="top",
        color=MUTED,
        fontsize=8,
    )
    _save(fig, "fig1_acid_neutralised")


# ----------------------------------------------------------------------------------------------
# Figure 2: where real waters sit (alkalinity vs hardness), three countries, band lines
# ----------------------------------------------------------------------------------------------
def fig2(w: pd.DataFrame) -> None:
    d = (
        w[w["source_id"] != "bottled-labels"]
        .dropna(subset=["alkalinity_best", "hardness_best"])
        .copy()
    )
    joined = set(d.loc[d["source_id"] == "tapwaterdata-us+epa-syr4-us", "locality_key"])
    d = d[~((d["source_id"] == "tapwaterdata-us") & d["locality_key"].isin(joined))]
    d = d[(d["alkalinity_best"] > 1) & (d["hardness_best"] > 1)]
    d["imputed"] = d["alkalinity_imputed"].astype(bool)
    pop = d["population"].fillna(d["population"].median())
    size = np.clip(np.sqrt(pop) / 25, 4, 60)
    fig, ax = plt.subplots(figsize=(7.2, 5.6))
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.grid(True, which="major", axis="both", color=GRID, linewidth=0.8)
    for cc in COUNTRY_ORDER:
        g = d[d["country_iso2"] == cc]
        meas = g[~g["imputed"]]
        imp = g[g["imputed"]]
        ax.scatter(
            meas["hardness_best"],
            meas["alkalinity_best"],
            s=size[meas.index],
            color=COUNTRY_COLOUR[cc],
            alpha=0.75,
            linewidths=0.6,
            edgecolors=SURFACE,
            label=COUNTRY_LABEL[cc],
            zorder=3,
        )
        if len(imp):
            ax.scatter(
                imp["hardness_best"],
                imp["alkalinity_best"],
                s=size[imp.index],
                facecolors="none",
                edgecolors=COUNTRY_COLOUR[cc],
                alpha=0.55,
                linewidths=0.7,
                label=None,
                zorder=2,
            )
    for e in [e for e in BAND_EDGES if 0 < e < np.inf]:
        ax.axhline(e, color=AXIS, linewidth=0.8, zorder=1)
    for i, _name in enumerate(BAND_NAMES):
        lo = max(BAND_EDGES[i], 3)
        hi = BAND_EDGES[i + 1] if np.isfinite(BAND_EDGES[i + 1]) else 700
        ax.text(
            1400,
            np.sqrt(lo * hi),
            f"band {i + 1}",
            color=MUTED,
            fontsize=8,
            va="center",
            ha="right",
        )
    ax.scatter(
        [68], [40], marker="*", s=140, color=INK, zorder=5, edgecolors=SURFACE, linewidths=0.8
    )
    ax.annotate(
        "SCA reference water",
        xy=(68, 40),
        xytext=(8, -12),
        textcoords="offset points",
        color=INK2,
        fontsize=8,
    )
    ax.set_xlim(3, 1500)
    ax.set_ylim(3, 700)
    ax.set_xlabel("hardness, mg/L as CaCO3")
    ax.set_ylabel("alkalinity, mg/L as CaCO3")
    for axis in (ax.xaxis, ax.yaxis):
        axis.set_major_formatter(ticker.ScalarFormatter())
        axis.set_minor_formatter(ticker.NullFormatter())
    leg = ax.legend(loc="lower right", handletextpad=0.4)
    for h in leg.legend_handles:
        h.set_alpha(1)
        h.set_sizes([45])
    ax.text(
        3.3,
        600,
        "filled = measured alkalinity   hollow = imputed from hardness   dot area scales with people served",
        color=MUTED,
        fontsize=8,
        va="top",
    )
    _title(
        ax,
        "Tap water runs along one diagonal: alkalinity tracks hardness",
        f"{len(d):,} localities. Horizontal rules are the alkalinity band edges (40, 80, 150, 250 mg/L).",
    )
    _save(fig, "fig2_where_waters_sit")


# ----------------------------------------------------------------------------------------------
# Figure 3: population share per band, per country (grouped bars)
# ----------------------------------------------------------------------------------------------
def fig3() -> None:
    loc = pd.read_parquet(PROC / "bands_v0_localities.parquet")
    share = (
        (
            loc.groupby(["country_iso2", "band"])["weight"].sum()
            / loc.groupby("country_iso2")["weight"].sum()
        )
        .unstack("band")
        .fillna(0.0)
    )
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    x = np.arange(len(BAND_NAMES))
    width = 0.24
    gap = 0.02
    for i, cc in enumerate(COUNTRY_ORDER):
        if cc not in share.index:
            continue
        vals = [float(share.loc[cc].get(b, 0.0)) for b in range(1, 6)]
        xs = x + (i - 1) * (width + gap)
        ax.bar(
            xs,
            vals,
            width=width,
            color=COUNTRY_COLOUR[cc],
            linewidth=0,
            label=COUNTRY_LABEL[cc],
            zorder=3,
        )
        for xi, v in zip(xs, vals, strict=True):
            if v >= 0.05:
                ax.text(xi, v + 0.012, f"{v:.0%}", ha="center", va="bottom", fontsize=8, color=INK2)
    edges = [
        f"{int(BAND_EDGES[i])} to {int(BAND_EDGES[i + 1])}"
        if np.isfinite(BAND_EDGES[i + 1])
        else f"over {int(BAND_EDGES[i])}"
        for i in range(5)
    ]
    grid = Grid(
        alkalinity_mgl=np.array([e for e in BAND_EDGES if 0 < e < np.inf]),
        hardness_mgl=np.array([0.0]),
    )
    lost = acid_lost_fraction(ROASTS[0], grid)[:, 0]
    lost_txt = ["under 6 %", "6 to 12 %", "12 to 23 %", "23 to 39 %", "over 39 %"]
    labels = [f"{e} mg/L\n{n.split(' (')[0]}" for e, n in zip(edges, BAND_NAMES, strict=True)]
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8, color=INK2)
    for xi, lt in zip(x, lost_txt, strict=True):
        ax.text(
            xi,
            -0.20,
            f"{lt} of a light\nroast's acidity lost",
            transform=ax.get_xaxis_transform(),
            ha="center",
            va="top",
            fontsize=7.5,
            color=MUTED,
        )
    ax.set_xlim(-0.6, 4.6)
    ax.set_ylim(0, 0.72)
    ax.yaxis.set_major_formatter(ticker.PercentFormatter(1.0, decimals=0))
    ax.set_ylabel("share of the country's population")
    ax.legend(loc="upper right")
    _title(
        ax,
        "Who brews with which water",
        "Population share by alkalinity band. Bands 1 to 3 'work' for every roast; bands 4 and 5 need compensation.",
    )
    del lost
    _save(fig, "fig3_population_by_band")


# ----------------------------------------------------------------------------------------------
# Figure 4: dial-in rules, two small multiples (sourness lost; extra coffee needed)
# ----------------------------------------------------------------------------------------------
def fig4() -> None:
    sens = AdditiveSensory.from_frost_csv()
    alks = tuple(range(0, 301, 10))
    t = rules_table(sens, alkalinities=alks)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.2, 4.2), gridspec_kw={"wspace": 0.28})
    for r in ROASTS:
        g = t[t["roast"] == r.name]
        c = ROAST_COLOUR[r.name]
        a1.plot(
            g["alkalinity_mgl"],
            g["sourness_change_points"],
            color=c,
            linewidth=2,
            label=f"{r.name} roast",
        )
        a2.fill_between(
            g["alkalinity_mgl"],
            g["dose_change_percent_chemistry"],
            g["dose_change_percent_sensory"],
            color=c,
            alpha=0.10,
            linewidth=0,
        )
        a2.plot(g["alkalinity_mgl"], g["dose_change_percent_chemistry"], color=c, linewidth=2)
        a2.plot(
            g["alkalinity_mgl"], g["dose_change_percent_sensory"], color=c, linewidth=1, alpha=0.7
        )
    for ax in (a1, a2):
        ax.axvline(40, color=AXIS, linewidth=0.8, zorder=0)
        ax.set_xlim(0, 300)
        ax.set_xlabel("water alkalinity, mg/L as CaCO3")
    a1.axhline(0, color=AXIS, linewidth=0.8, zorder=0)
    a1.set_ylabel("predicted change in sourness, 0 to 100 panel scale")
    a1.legend(loc="lower left")
    _title(
        a1,
        "What the water does",
        "Versus the SCA target of 40 mg/L; 3.6 points per meq/L (Batali 2021).",
    )
    a2.axhline(0, color=AXIS, linewidth=0.8, zorder=0)
    a2.set_ylabel("extra coffee needed to compensate, percent of dose")
    for r in ROASTS:
        a2.plot([], [], color=ROAST_COLOUR[r.name], linewidth=2, label=f"{r.name} roast")
    a2.legend(loc="lower right")
    a2.set_ylim(-15, 75)
    a2.axvspan(150, 300, color=GRID, alpha=0.4, linewidth=0, zorder=0)
    _title(
        a2,
        "What it costs to brew it back",
        "Thick: restore titratable acidity. Thin: restore predicted sourness (Frost 2020).",
    )
    a2.text(
        155,
        72,
        "above 150 mg/L,\nblend the water instead",
        color=INK2,
        fontsize=8.3,
        ha="left",
        va="top",
    )
    _save(fig, "fig4_dialin_rules")


# ----------------------------------------------------------------------------------------------
# Figure 5: bottled waters, dot strip per country, alkalinity on a log axis
# ----------------------------------------------------------------------------------------------
def fig5(w: pd.DataFrame) -> None:
    b = w[w["source_id"] == "bottled-labels"].dropna(subset=["alkalinity_median"]).copy()
    b["alk"] = b["alkalinity_median"].clip(lower=1)
    order = ["BR", "US", "GB", "DE", "FR", "IT", "PT"]
    names = {
        "BR": "Brazil",
        "US": "United States",
        "GB": "United Kingdom",
        "DE": "Germany",
        "FR": "France",
        "IT": "Italy",
        "PT": "Portugal",
    }
    order = [c for c in order if c in set(b["country_iso2"])]
    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    ax.set_xscale("log")
    ax.grid(False)
    rng = np.random.default_rng(0)
    counts: dict[str, int] = {}
    for i, cc in enumerate(order):
        g = b[b["country_iso2"] == cc]
        counts[cc] = len(g)
        y = i + rng.uniform(-0.18, 0.18, len(g))
        ax.scatter(
            g["alk"],
            y,
            s=28,
            color=SLOT[0],
            alpha=0.8,
            linewidths=0.8,
            edgecolors=SURFACE,
            zorder=3,
        )
        # label the extremes sparingly, above the dot
        lo = g.loc[g["alk"].idxmin()]
        hi = g.loc[g["alk"].idxmax()]
        for row in (lo, hi):
            ax.annotate(
                str(row["utility"]),
                xy=(row["alk"], i),
                xytext=(0, 9),
                textcoords="offset points",
                va="bottom",
                ha="center",
                color=INK2,
                fontsize=7.5,
            )
    for e in [e for e in BAND_EDGES if 0 < e < np.inf]:
        ax.axvline(e, color=GRID, linewidth=0.8, zorder=0)
    ax.axvline(40, color=AXIS, linewidth=0.8, zorder=0)
    ax.axvspan(1, 15, color=BLUE[100], alpha=0.35, zorder=0, linewidth=0)
    ax.axvspan(25, 60, color=BLUE[100], alpha=0.35, zorder=0, linewidth=0)
    for xpos, txt in (
        (3.9, "diluents (under 15)"),
        (39, "reference-like (25 to 60)"),
        (380, "as flat as hard tap water (over 150)"),
    ):
        ax.text(xpos, -0.62, txt, color=INK2, fontsize=8, ha="center", va="bottom")
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([f"{names[c]}  ({counts[c]})" for c in order], color=INK2)
    ax.set_ylim(-0.95, len(order) - 0.4)
    ax.invert_yaxis()
    ax.set_xlim(1, 1000)
    ax.xaxis.set_major_formatter(ticker.ScalarFormatter())
    ax.xaxis.set_minor_formatter(ticker.NullFormatter())
    ax.set_xlabel("alkalinity from the label, mg/L as CaCO3 (bicarbonate × 0.82)")
    ax.tick_params(axis="y", length=0)
    _title(
        ax,
        "Bottled waters span the same range as tap water",
        f"{len(b)} supermarket products with bicarbonate or alkalinity on the label; count per country in brackets; extremes named.",
    )
    _save(fig, "fig5_bottled")


def main() -> None:
    w = load_atlas()
    fig1(w)
    fig2(w)
    fig3()
    fig4()
    fig5(w)
    print("wrote fig1..fig5 to", FIG)


if __name__ == "__main__":
    main()
