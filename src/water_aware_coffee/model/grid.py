"""Alkalinity × hardness grid model for three roast levels (Task 3).

Residual acidity
----------------
Coffee acids are neutralised by the water's bicarbonate. In milliequivalents per litre of brew:

    residual = TA_brew(roast, EY) - f_neutralised(pH_brew) * alkalinity_water

- TA_brew is the titratable acidity of the brew in meq/L. It scales with strength (TDS), and TDS
  scales with extraction yield at fixed ratio, so TA_brew = TA_ref * (EY / EY_ref) to first order.
- alkalinity_water in meq/L = mg/L as CaCO3 / 50.04.
- f_neutralised: the fraction of bicarbonate that is protonated at the brew pH. Carbonic acid pKa1
  is 6.35 at 25 °C; at brew pH 4.8 to 5.3, 92 to 97 percent of bicarbonate has accepted a proton,
  so the 1:1 subtraction is nearly exact and the correction is small. Kept explicit so the
  assumption is visible.

Extraction shift (secondary, bounded, includes zero)
----------------------------------------------------
Hendon et al. 2014 predicted that Mg2+ and Ca2+ increase extraction of some coffee compounds;
Bratthäll et al. 2024 measured no such effect on organic acids at 100 ppm. We model a
multiplicative shift on extraction yield: EY = EY_0 * (1 + beta * (Mg_meq + ca_weight * Ca_meq)),
with beta in a range whose lower bound is 0. Default beta is 0 (central) with the range reported
alongside. This feeds TA_brew through the EY dependence. Everything here is a parameter; nothing
is hidden in the code.

The grid function returns residual acidity for every (alkalinity, hardness) cell and roast bin, for
central, low and high parameter sets, so the plot can show the uncertainty band, not just a line.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import numpy.typing as npt

from water_aware_coffee.units import EQ_CACO3

FArray = npt.NDArray[np.float64]

CARBONIC_PKA1 = 6.35


@dataclass(frozen=True)
class RoastParams:
    """Titratable acidity of a reference brew for one roast bin.

    ta_ref_meq_l: TA of the brew in meq/L at the reference recipe (ratio, EY) in low-alkalinity
        water.
    ta_low / ta_high: plausible range (literature spread).
    ey_ref: extraction yield (fraction, e.g. 0.20) at which ta_ref was measured.
    brew_ph: typical brew pH for the bin, used only for the bicarbonate protonation fraction.
    agtron: (low, high) Agtron range that defines the bin, for documentation.
    source: citation key in literature.md.
    """

    name: str
    ta_ref_meq_l: float
    ta_low: float
    ta_high: float
    ey_ref: float
    brew_ph: float
    agtron: tuple[int, int]
    source: str


@dataclass(frozen=True)
class CationParams:
    """Extraction shift per meq/L of divalent cations. beta=0 means no effect."""

    beta_central: float = 0.0
    beta_low: float = 0.0
    beta_high: float = 0.0
    ca_weight: float = 1.0  # Ca effect relative to Mg (Hendon: Ca somewhat weaker)
    source: str = "Hendon2014 vs Bratthall2024; see open-questions.md item 1"


@dataclass
class Grid:
    alkalinity_mgl: FArray = field(default_factory=lambda: np.linspace(0, 300, 61))
    hardness_mgl: FArray = field(default_factory=lambda: np.linspace(0, 400, 81))
    mg_fraction_of_hardness: float = (
        0.25  # share of hardness (as CaCO3) that is Mg; typical 0.15 to 0.35
    )


def bicarbonate_protonated_fraction(ph: float) -> float:
    """Fraction of HCO3- converted to H2CO3 at a given pH (single-pKa approximation)."""
    return float(1.0 / (1.0 + 10.0 ** (ph - CARBONIC_PKA1)))


def alkalinity_meq(alkalinity_mgl_caco3: FArray | float) -> FArray:
    return np.asarray(alkalinity_mgl_caco3, dtype=float) / EQ_CACO3


def hardness_meq(hardness_mgl_caco3: FArray | float) -> FArray:
    return np.asarray(hardness_mgl_caco3, dtype=float) / EQ_CACO3


def extraction_multiplier(
    hardness_mgl: FArray, mg_fraction: float, cations: CationParams, which: str = "central"
) -> FArray:
    beta = {
        "central": cations.beta_central,
        "low": cations.beta_low,
        "high": cations.beta_high,
    }[which]
    h = hardness_meq(hardness_mgl)
    mg = h * mg_fraction
    ca = h * (1.0 - mg_fraction)
    return 1.0 + beta * (mg + cations.ca_weight * ca)


def residual_acidity(
    roast: RoastParams,
    grid: Grid,
    cations: CationParams,
    ey: float | None = None,
    which: str = "central",
) -> FArray:
    """Residual acidity (meq/L) on the grid. Shape: (len(alkalinity), len(hardness)).

    which: "central" uses ta_ref and beta_central; "low" uses ta_low and beta_low (least acid);
    "high" uses ta_high and beta_high (most acid).
    """
    ta = {"central": roast.ta_ref_meq_l, "low": roast.ta_low, "high": roast.ta_high}[which]
    ey = roast.ey_ref if ey is None else ey
    ey_scale = ey / roast.ey_ref
    mult = extraction_multiplier(grid.hardness_mgl, grid.mg_fraction_of_hardness, cations, which)
    ta_brew = ta * ey_scale * mult[None, :]  # (1, H)
    neutralised = bicarbonate_protonated_fraction(roast.brew_ph) * alkalinity_meq(
        grid.alkalinity_mgl
    )
    return ta_brew - neutralised[:, None]


def relative_residual(
    roast: RoastParams,
    grid: Grid,
    cations: CationParams,
    reference_alkalinity_mgl: float = 40.0,
    reference_hardness_mgl: float = 68.0,
    which: str = "central",
) -> FArray:
    """Residual acidity divided by the residual in a reference water (default: SCA-style
    40 mg/L alkalinity, 68 mg/L hardness). 1.0 means 'tastes as acidic as in reference water'."""
    r = residual_acidity(roast, grid, cations, which=which)
    ref_grid = Grid(
        alkalinity_mgl=np.array([reference_alkalinity_mgl]),
        hardness_mgl=np.array([reference_hardness_mgl]),
        mg_fraction_of_hardness=grid.mg_fraction_of_hardness,
    )
    ref = float(residual_acidity(roast, ref_grid, cations, which=which)[0, 0])
    out: FArray = r / ref
    return out


def acid_lost_fraction(roast: RoastParams, grid: Grid) -> FArray:
    """Share of the brew's titratable acidity neutralised by the water, on the grid (0 to >1).

    Independent of the cation term. This is the cleanest single number for 'how much does this water
    flatten this roast'.
    """
    neutralised = bicarbonate_protonated_fraction(roast.brew_ph) * alkalinity_meq(
        grid.alkalinity_mgl
    )
    return np.broadcast_to(
        (neutralised / roast.ta_ref_meq_l)[:, None],
        (len(grid.alkalinity_mgl), len(grid.hardness_mgl)),
    ).copy()
