"""Task 5: additive sensory model and dial-in rules.

Data: Frost, Ristenpart & Guinard 2020 (J. Food Science 85:2530) marginal means of trained-panel
intensities (0 to 100) for 32 attributes at each level of roast (light / medium / dark), TDS
(1.0 / 1.25 / 1.5 percent) and extraction (16 / 20 / 24 percent), transcribed from their
Supplemental B into data/external/ucdavis/frost2020_sensory_means.csv. The design is balanced, so
an additive model is exactly the sum of factor effects around the grand mean:

    intensity(attribute, roast, TDS, PE) = grand + e_roast + e_TDS(TDS) + e_PE(PE)

with e_TDS and e_PE linearly interpolated between the three levels (linear extrapolation outside,
flagged). No interaction terms: Batali et al. 2021 Figure 5A fits sourness as a first-order plane,
and decisions.md item 30 accepts main effects only.

Dial-in logic (Task 3b), all in the model's own currency of titratable acidity (TA, meq/L):

1. Water alkalinity above the reference (40 mg/L as CaCO3) neutralises
   Δmeq = f(pH) × (alk − 40) / 50.04 of the brew's acid.
2. Batali et al. 2021 calibrate sourness against TA: 3.61 sourness points per meq/L.
3. Two ways to size the strength compensation, reported as a range:
   (a) chemistry: TA is proportional to TDS (Batali Figure 3A), slope TA_intrinsic / 1.25 per
       percent TDS, so ΔTDS = Δmeq / slope restores the lost acid;
   (b) sensory: Frost's sourness-versus-TDS slope (about 21 points per percent TDS) gives the
       ΔTDS that restores the predicted sourness loss directly.
   (b) is about 1.8 times (a): the Batali sourness-per-meq calibration comes from roast means,
   and roast changes which acids are present, not only how much; so per meq of alkalinity the
   sensory route asks for more strength. At fixed extraction TDS scales with the coffee-to-water
   ratio, so ΔTDS / 1.25 is the fractional dose increase. Side effects come from the additive model.
4. Alternatively, lowering extraction raises sourness (Frost: -0.83 points per percent PE) but
   also lowers bitterness; the PE route is reported with its own side effects. In practice PE is
   lowered by a coarser grind or shorter contact time, and realistic moves are 2 to 4 points, so
   this route only partly compensates above about 100 mg/L alkalinity.
5. Dilution: alkalinity is linear in mixing, so blending the tap water with a fraction
   x = 1 - 40 / alk of zero-alkalinity water (distilled, reverse-osmosis, or a bottled water of
   near-zero bicarbonate) brings it to the reference. Above about 150 mg/L this is the cheapest
   lever; it also lowers hardness by the same fraction.

Everything is linear and stated; magnitudes carry the uncertainties of the inputs (±20 percent is
a fair reading).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from water_aware_coffee.model.grid import (
    SOURNESS_SLOPE_PER_MEQ,
    RoastParams,
    bicarbonate_protonated_fraction,
)
from water_aware_coffee.model.params import REFERENCE_TDS_PERCENT, ROASTS
from water_aware_coffee.units import EQ_CACO3

REPO_ROOT = Path(__file__).resolve().parents[3]
FROST_CSV = REPO_ROOT / "data" / "external" / "ucdavis" / "frost2020_sensory_means.csv"
REF_ALKALINITY_MGL = 40.0
TDS_LEVELS = (1.0, 1.25, 1.5)
PE_LEVELS = (16.0, 20.0, 24.0)
ROAST_LEVELS = ("light", "medium", "dark")
KEY_ATTRIBUTES = (
    "Sourness",
    "Bitterness",
    "Sweetness",
    "Thickness",
    "Citrus Flavor",
    "Astringency",
)


@dataclass
class AdditiveSensory:
    grand: dict[str, float]
    roast_effect: dict[str, dict[str, float]]  # attribute -> roast -> effect
    tds_effect: dict[str, np.ndarray]  # attribute -> effects at TDS_LEVELS
    pe_effect: dict[str, np.ndarray]  # attribute -> effects at PE_LEVELS

    @classmethod
    def from_frost_csv(cls, path: Path = FROST_CSV) -> AdditiveSensory:
        df = pd.read_csv(path, dtype=str)
        df["mean_intensity"] = pd.to_numeric(df["mean_intensity"], errors="coerce")
        grand: dict[str, float] = {}
        roast_effect: dict[str, dict[str, float]] = {}
        tds_effect: dict[str, np.ndarray] = {}
        pe_effect: dict[str, np.ndarray] = {}
        for attr, g in df.groupby("attribute"):
            sub_r = g[g["varied_factor"] == "roast"]
            sub_t = g[g["varied_factor"] == "tds"]
            sub_p = g[g["varied_factor"] == "pe"]
            r = pd.Series(
                sub_r["mean_intensity"].to_numpy(), index=sub_r["roast"].str.lower().to_numpy()
            )
            t = pd.Series(
                sub_t["mean_intensity"].to_numpy(),
                index=pd.to_numeric(sub_t["tds_percent"], errors="coerce").to_numpy(),
            )
            pe = pd.Series(
                sub_p["mean_intensity"].to_numpy(),
                index=pd.to_numeric(sub_p["pe_percent"], errors="coerce").to_numpy(),
            )
            if len(r) != 3 or len(t) != 3 or len(pe) != 3:
                continue
            gm = float(r.mean())
            grand[str(attr)] = gm
            roast_effect[str(attr)] = {str(k): float(v - gm) for k, v in r.items()}
            tds_effect[str(attr)] = np.array([t.loc[x] - gm for x in TDS_LEVELS], dtype=float)
            pe_effect[str(attr)] = np.array([pe.loc[x] - gm for x in PE_LEVELS], dtype=float)
        return cls(grand, roast_effect, tds_effect, pe_effect)

    def attributes(self) -> list[str]:
        return sorted(self.grand)

    def predict(self, attribute: str, roast: str, tds: float, pe: float) -> float:
        e_t = float(np.interp(tds, TDS_LEVELS, self.tds_effect[attribute]))
        e_p = float(np.interp(pe, PE_LEVELS, self.pe_effect[attribute]))
        # np.interp clamps outside the range; extend linearly instead using the end slopes.
        e_t = _extrapolate(tds, TDS_LEVELS, self.tds_effect[attribute], e_t)
        e_p = _extrapolate(pe, PE_LEVELS, self.pe_effect[attribute], e_p)
        return self.grand[attribute] + self.roast_effect[attribute][roast] + e_t + e_p

    def slope_per_tds(self, attribute: str) -> float:
        """Points per percent TDS (least-squares over the three levels)."""
        return float(np.polyfit(TDS_LEVELS, self.tds_effect[attribute], 1)[0])

    def slope_per_pe(self, attribute: str) -> float:
        """Points per percent extraction yield."""
        return float(np.polyfit(PE_LEVELS, self.pe_effect[attribute], 1)[0])


def _extrapolate(x: float, xs: tuple[float, ...], ys: np.ndarray, clamped: float) -> float:
    if x < xs[0]:
        slope = (ys[1] - ys[0]) / (xs[1] - xs[0])
        return float(ys[0] + slope * (x - xs[0]))
    if x > xs[-1]:
        slope = (ys[-1] - ys[-2]) / (xs[-1] - xs[-2])
        return float(ys[-1] + slope * (x - xs[-1]))
    return clamped


@dataclass
class DialIn:
    roast: str
    alkalinity_mgl: float
    acid_neutralised_meq: float  # relative to reference water (can be negative)
    sourness_change_points: float  # predicted, before compensation
    tds_delta_percent: float  # TDS change that restores the acid balance (chemistry route, a)
    tds_delta_percent_sensory: float  # TDS change that restores predicted sourness (Frost slope, b)
    dose_change_fraction: float  # coffee dose change at fixed water and extraction, route (a)
    dose_change_fraction_sensory: float  # same for route (b)
    side_effects_tds_route: dict[str, float]  # attribute -> change in points from the TDS change
    pe_delta_percent: float  # extraction change that restores sourness instead
    side_effects_pe_route: dict[str, float]
    dilution_fraction_zero_alk_water: float  # share of zero-alkalinity water to reach reference
    note: str


def dial_in(
    alkalinity_mgl: float,
    roast: RoastParams,
    sensory: AdditiveSensory,
    tds: float = REFERENCE_TDS_PERCENT,
    pe: float = 20.0,
) -> DialIn:
    f = bicarbonate_protonated_fraction(roast.brew_ph)
    d_meq = f * (alkalinity_mgl - REF_ALKALINITY_MGL) / EQ_CACO3
    sour_change = -SOURNESS_SLOPE_PER_MEQ * d_meq
    ta_slope = roast.intrinsic_ta() / REFERENCE_TDS_PERCENT  # meq/L per percent TDS
    d_tds = d_meq / ta_slope
    dose = d_tds / tds
    tds_slope_sour = sensory.slope_per_tds("Sourness")
    d_tds_sens = -sour_change / tds_slope_sour if tds_slope_sour else float("nan")
    dose_sens = d_tds_sens / tds
    side_tds = {
        a: sensory.predict(a, roast.name, tds + d_tds, pe) - sensory.predict(a, roast.name, tds, pe)
        for a in KEY_ATTRIBUTES
        if a in sensory.grand
    }
    pe_slope = sensory.slope_per_pe("Sourness")  # negative: lower PE, more sour
    # We need +(-sour_change) points back; ΔPE = needed / slope, negative when water flattens.
    d_pe = -sour_change / pe_slope if pe_slope != 0 else float("nan")
    side_pe = {
        a: sensory.predict(a, roast.name, tds, pe + d_pe) - sensory.predict(a, roast.name, tds, pe)
        for a in KEY_ATTRIBUTES
        if a in sensory.grand
    }
    dilution = max(0.0, 1.0 - REF_ALKALINITY_MGL / alkalinity_mgl) if alkalinity_mgl > 0 else 0.0
    if abs(d_meq) < 0.05:
        note = "within 2.5 mg/L of reference alkalinity: no compensation needed"
    elif d_meq > 0:
        note = (
            "water flattens acidity: raise strength (more coffee or finer grind at the same PE) "
            "or lower extraction (coarser grind, shorter contact)"
        )
    else:
        note = "water is softer than reference: coffee will taste sharper; the reverse moves apply"
    return DialIn(
        roast=roast.name,
        alkalinity_mgl=alkalinity_mgl,
        acid_neutralised_meq=d_meq,
        sourness_change_points=sour_change,
        tds_delta_percent=d_tds,
        tds_delta_percent_sensory=d_tds_sens,
        dose_change_fraction=dose,
        dose_change_fraction_sensory=dose_sens,
        side_effects_tds_route=side_tds,
        pe_delta_percent=d_pe,
        side_effects_pe_route=side_pe,
        dilution_fraction_zero_alk_water=dilution,
        note=note,
    )


def rules_table(
    sensory: AdditiveSensory, alkalinities: tuple[float, ...] = (20, 40, 80, 150, 250)
) -> pd.DataFrame:
    rows = []
    for r in ROASTS:
        for a in alkalinities:
            d = dial_in(float(a), r, sensory)
            rows.append(
                {
                    "roast": r.name,
                    "alkalinity_mgl": a,
                    "acid_neutralised_meq_vs_ref": d.acid_neutralised_meq,
                    "sourness_change_points": d.sourness_change_points,
                    "tds_delta_percent_chemistry": d.tds_delta_percent,
                    "tds_delta_percent_sensory": d.tds_delta_percent_sensory,
                    "dose_change_percent_chemistry": 100 * d.dose_change_fraction,
                    "dose_change_percent_sensory": 100 * d.dose_change_fraction_sensory,
                    "bitterness_side_effect_tds_route": d.side_effects_tds_route.get(
                        "Bitterness", float("nan")
                    ),
                    "pe_delta_percent": d.pe_delta_percent,
                    "bitterness_side_effect_pe_route": d.side_effects_pe_route.get(
                        "Bitterness", float("nan")
                    ),
                    "dilution_share_zero_alkalinity_water": d.dilution_fraction_zero_alk_water,
                }
            )
    return pd.DataFrame(rows)
