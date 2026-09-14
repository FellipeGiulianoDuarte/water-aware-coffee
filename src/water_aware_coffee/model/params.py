"""Parameter values for the grid model, with provenance.

v1 (2026-09-14): titratable acidity from Batali, Cotter, Frost, Ristenpart & Guinard 2021,
ACS Food Sci. Technol. 1(4):559-569, DOI 10.1021/acsfoodscitech.0c00078, Table 1 and
Supplemental Figure 1 (full text obtained via CAPES; private/papers/Batali2021.pdf).

- Drip coffee (Curtis G4 brewer), 258 brews over TDS 1.0 / 1.25 / 1.5 percent × extraction 16 / 20 /
  24 percent × three roasts of one Honduran washed Arabica. Roast bins defined by development time
  after first crack (no Agtron given); the same coffees as Frost et al. 2020.
- TA titrated with 0.1 M NaOH to pH 8.2, reported as mL per 50 mL brew: 1 mL = 2 meq/L.
- Table 1 roast means (over the whole TDS × PE grid, so effectively TDS 1.25 percent,
  PE 20 percent):
  light 6.23 mL (12.46 meq/L), medium 5.68 mL (11.36 meq/L), dark 4.89 mL (9.78 meq/L).
  Mean brew pH 4.93 / 5.01 / 5.14.
- TA is linear in TDS (R 0.75 to 0.97) and nearly flat in extraction yield (about -1 mL over
  PE 15 to 25 percent for light and dark); Supplemental Figure 1 contours at TDS 1.25 percent span
  roughly light 5.75 to 6.5 mL, medium 5.2 to 6.0 mL, dark 4.6 to 5.2 mL across PE 16 to 24.
  Those spans set the low / high parameters below.
- Brew water (their section 2.1, per litre of RO water: 0.0116 g CaSO4·2H2O, 0.0497 g MgSO4,
  0.0326 g NaHCO3, 0.0257 g KHCO3) computes to alkalinity 0.645 meq/L = 32.3 mg/L as CaCO3 and
  hardness 48 mg/L as CaCO3 (86 percent magnesium). The measured TA therefore already lost
  about 0.6 meq/L to bicarbonate; RoastParams.ref_water_alkalinity_mgl adds it back.

Compared with the v0 immersion-derived values (12 / 11 / 7.5 meq/L), light and medium agree and
dark was underestimated by about 25 percent: drip dark roast keeps 78 percent of the light roast's
acidity, not 62 percent.
"""

from __future__ import annotations

from water_aware_coffee.model.grid import CationParams, RoastParams

REFERENCE_TDS_PERCENT = 1.25
REFERENCE_EY = 0.20
BATALI_WATER_ALKALINITY_MGL = 32.3
BATALI_SOURCE = (
    "Batali2021 Table 1 and Supplemental Figure 1 (drip, TDS 1.25 %, PE 20 %, endpoint pH 8.2); "
    "see docs/literature/titratable_acidity_by_roast.md"
)

LIGHT = RoastParams(
    name="light",
    ta_ref_meq_l=12.46,
    ta_low=11.5,
    ta_high=13.0,
    ey_ref=REFERENCE_EY,
    brew_ph=4.93,
    agtron=(0, 0),  # not reported; roast defined by development time after first crack
    source=BATALI_SOURCE,
    ref_water_alkalinity_mgl=BATALI_WATER_ALKALINITY_MGL,
)
MEDIUM = RoastParams(
    name="medium",
    ta_ref_meq_l=11.36,
    ta_low=10.4,
    ta_high=12.0,
    ey_ref=REFERENCE_EY,
    brew_ph=5.01,
    agtron=(0, 0),
    source=BATALI_SOURCE,
    ref_water_alkalinity_mgl=BATALI_WATER_ALKALINITY_MGL,
)
DARK = RoastParams(
    name="dark",
    ta_ref_meq_l=9.78,
    ta_low=9.2,
    ta_high=10.4,
    ey_ref=REFERENCE_EY,
    brew_ph=5.14,
    agtron=(0, 0),
    source=BATALI_SOURCE,
    ref_water_alkalinity_mgl=BATALI_WATER_ALKALINITY_MGL,
)
ROASTS = (LIGHT, MEDIUM, DARK)

# Cation term: no quantitative extraction magnitude is available from the literature. Hendon 2014
# gives binding energies, not yield changes; Bratthäll 2024 finds no acid-extraction effect at
# 100 ppm. Central 0. Upper bound: a 5 percent extraction-yield increase per meq/L of divalent
# cations (about 2.5 percent per 25 mg/L as CaCO3), a generous reading of practitioner claims;
# flagged as an assumption, not a measurement.
CATIONS = CationParams(beta_central=0.0, beta_low=0.0, beta_high=0.05, ca_weight=0.7)
