"""Parameter values for the grid model, with provenance.

Every number here comes from docs/literature/titratable_acidity_by_roast.md (section 9) and is
derived, not measured, for drip coffee. All readable sources are immersion brews titrated to
pH 8.2, scaled proportionally to 1.25 percent TDS on the assumption that TA is proportional to
TDS through the origin. Uncertainty is about ±20 percent on the central values. Treat these as
v0 parameters to be replaced when Batali et al. 2021 (ACS Food Sci. Technol.) drip data is
obtained.

Brew pH per bin: Rao, Fuller & Grim 2020 (hot immersion, DI water) 4.80 / 5.04 / 5.39 and
Yeager 2021 4.81 to 4.94 / 4.95 to 5.08 / 5.38 to 5.48.
"""

from __future__ import annotations

from water_aware_coffee.model.grid import CationParams, RoastParams

REFERENCE_TDS_PERCENT = 1.25
REFERENCE_EY = 0.20

LIGHT = RoastParams(
    name="light",
    ta_ref_meq_l=12.0,
    ta_low=10.0,
    ta_high=14.0,
    ey_ref=REFERENCE_EY,
    brew_ph=4.85,
    agtron=(56, 68),
    source="Yeager2021 Table 3.2 (whole bean Agtron 56-59), Anokye-Bempah2024, Rao2018; "
    "see docs/literature",
)
MEDIUM = RoastParams(
    name="medium",
    ta_ref_meq_l=11.0,
    ta_low=9.0,
    ta_high=12.0,
    ey_ref=REFERENCE_EY,
    brew_ph=5.05,
    agtron=(45, 55),
    source="Yeager2021 Table 3.2 (whole bean Agtron ~49); Rao2020 medium",
)
DARK = RoastParams(
    name="dark",
    ta_ref_meq_l=7.5,
    ta_low=5.5,
    ta_high=9.0,
    ey_ref=REFERENCE_EY,
    brew_ph=5.4,
    agtron=(30, 40),
    source="Yeager2021 Table 3.2 (whole bean Agtron 37-38); Anokye-Bempah2024 second crack; "
    "Rao2020 dark",
)
ROASTS = (LIGHT, MEDIUM, DARK)

# Cation term: no quantitative extraction magnitude is available from the literature. Hendon 2014
# gives binding energies, not yield changes; Bratthäll 2024 finds no acid-extraction effect at
# 100 ppm.
# Central 0. Upper bound: a 5 percent extraction-yield increase per meq/L of divalent cations
# (about 2.5 percent per 25 mg/L as CaCO3), a generous reading of practitioner claims; flagged as
# an assumption, not a measurement.
CATIONS = CationParams(beta_central=0.0, beta_low=0.0, beta_high=0.05, ca_weight=0.7)
