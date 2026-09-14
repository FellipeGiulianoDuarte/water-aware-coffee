# UC Davis Coffee Center drip-brew sensory data (transcribed)

Machine-readable tables transcribed from three papers by the UC Davis Coffee
Center group. They are inputs for a response-surface model of drip coffee
(sensory intensity and consumer liking as functions of brew strength and
extraction yield).

Sources (PDF and supporting-information files are held privately, not in this
repository):

- **Frost2020** — Frost, S. C., Ristenpart, W. D., Guinard, J.-X. (2020).
  Effects of brew strength, brew yield, and roast on the sensory quality of
  drip brewed coffee. *Journal of Food Science* 85(8), 2530–2543.
  doi:10.1111/1750-3841.15326. Supporting information (docx): Supplemental A,
  B, C.
- **Cotter2021** — Cotter, A. R., Batali, M. E., Ristenpart, W. D., Guinard,
  J.-X. (2021). Consumer preferences for black coffee are spread over a wide
  range of brew strengths and extraction yields. *Journal of Food Science*
  86(1), 194–205. doi:10.1111/1750-3841.15561. Supporting information (docx):
  Tables S1–S4, Figures S1–S2.
- **Guinard2023** — Guinard, J.-X., Frost, S., Batali, M., Cotter, A., Lim,
  L. X., Ristenpart, W. D. (2023). A new Coffee Brewing Control Chart relating
  sensory properties and consumer liking to brew strength, extraction yield,
  and brew ratio. *Journal of Food Science* 88, 2168–2177.
  doi:10.1111/1750-3841.16531. This paper is a graphical synthesis of
  Frost2020, Batali et al. 2020 and Cotter2021; it prints **no numeric
  tables** and no regression coefficients, so no CSV is derived from it.

Transcription date: 2026-09-14. The docx supporting-information tables were
parsed programmatically from `word/document.xml`; the main-paper tables were
transcribed from the PDF text layer. Nothing was read off a figure: every
number in these CSVs appears as a printed number in a table or in the body
text of the paper, and the `source_table` / `source` column of each row names
where.

## Definitions used across all files

- **TDS** — total dissolved solids of the brew, mass percent, measured with a
  VST digital refractometer on room-temperature coffee.
- **PE** — percent extraction (extraction yield), `PE = TDS × m_brew / m_dry_grounds`
  (Frost2020 Eq. 1; Cotter2021 Eq. 1).
- **Target levels** in both designs: TDS 1.00 / 1.25 / 1.50 %, PE 16 / 20 /
  24 %. Cotter2021 adds brew temperature (BT) 87 / 90 / 93 °C. The level words
  Low / Medium / High used in Cotter2021 Tables S2–S3 map to those values
  (Cotter2021 Table 1).
- **Coded response-surface variables** (Frost2020 Eq. 2–3; the same coding
  is the natural one for Cotter2021 although that paper does not print it):
  `x1 = (PE − 20) / 4` and `x2 = (TDS − 1.25) / 0.25`, so each design level
  is −1, 0 or +1. Frost2020 models: first order
  `E(Y) = b0 + b1·x1 + b2·x2` (Eq. 4a); second order
  `E(Y) = b0 + b1·x1 + b2·x2 + b12·x1·x2 + b11·x1² + b22·x2²` (Eq. 4b).
  Column names `b1_x1`, `b2_x2`, `b12`, `b11`, `b22` in the coefficient files
  follow this exactly.
- **Descriptive-analysis scale** (Frost2020): 15 cm unstructured line scale,
  converted to a 0–100 scale for analysis. Values in
  `frost2020_sensory_means.csv` are on that 0–100 scale. Panel: 12 trained
  judges, 3 sensory replicates, 27 brews (258 individual brews evaluated in
  total).
- **Liking scale** (Cotter2021): 9-point hedonic scale (1 = dislike
  extremely, 9 = like extremely). JAR questions: 5-point just-about-right
  scales for serving temperature, flavor intensity, acidity, mouthfeel.
  Consumers: n = 118 black-coffee drinkers, each tasted all 27 coffees over 3
  sessions.

## Coffee, roast and water

**Frost2020.** One green, wet-washed *Coffea arabica* from a single
cooperative in Siguatepeque, Comayagua, Honduras (imported by Royal Coffee,
Oakland, CA), roasted on a Loring S35 to three levels by extending
development time (Frost2020 Table 2):

| Roast | Initial mass kg | Final mass kg | Roast loss % | Initial temp °C | Final temp °C | First-crack temp °C | First crack s | Development s | Overall s |
|---|---|---|---|---|---|---|---|---|---|
| Light | 29.5 | 25.3 | 14.2 | 240.8 | 218.9 | 206.1 | 631 | 92 | 723 |
| Medium | 31.7 | 26.9 | 15.1 | 240.7 | 222.2 | 205.6 | 661 | 138 | 799 |
| Dark | 31.7 | 26.7 | 15.8 | 236.9 | 229.4 | 205.6 | 662 | 171 | 883 |

Brewer: Curtis G4 Single 1.0 Gal (G4TP1S63A3100). Brew water mass 3075 g and
water temperature 90.5 °C fixed for all brews. **The brew-water mineral
recipe is not stated in Frost2020** (only the refractometer zero used
deionized water). Grinder: Mahlkönig Guatemala Lab; grind settings 3 / 4 / 5
correspond to median particle sizes of roughly 750 / 950 / 1100 µm ("fine" /
"medium" / "coarse" in the paper's own wording). Per-brew brew ratio, grind
and pulsing are in `frost2020_brew_parameters.csv`. Cups served at ~100 mL,
cooled to 65 °C.

**Cotter2021.** One medium-roast, wet-processed Honduran coffee (Royal
Coffee); roast conditions are in Batali, Ristenpart & Guinard (2020,
*Scientific Reports* 10:16450), not in Cotter2021. Same Curtis G4 brewer
model, flat-bottom basket with paper filter. **Brew water recipe (stated):**
deionized water dosed with 1.16 g CaSO4·2H2O, 4.97 g MgSO4, 3.26 g NaHCO3 and
2.57 g KHCO3 per 100 L, equilibrated with ambient CO2 to a stable pH near 7
(the SCA water standard). 2.934 L of water per brew. Consumers waited 90 s
before the first sip; first-sip temperatures averaged 63.0 °C (low BT) to
65.2 °C (high BT).

## Files

### `frost2020_sensory_means.csv` — 288 rows

Source: **Frost2020 Supplemental B, "Mean attribute intensity by factor"**
(32 attributes × 9 factor levels). These are **main-effect (marginal)
means**: each row is the mean over all brews sharing one factor level (for
example roast = Light averages the 9 light-roast brews × 3 replicates × 12
judges). The paper and its SI **do not report the 27 per-brew means**; per-brew
values exist only as points in Figure 6 (interaction means, two factors at a
time) and as fitted contours in Figures 8–10, and were not read off.

| Column | Meaning / origin |
|---|---|
| `roast` | Light / Medium / Dark when `varied_factor = roast`, else `all` (averaged over roasts) |
| `tds_percent` | 1.00 / 1.25 / 1.50 when `varied_factor = tds`, else `all` |
| `pe_percent` | 16 / 20 / 24 when `varied_factor = pe`, else `all` |
| `attribute` | Attribute name exactly as printed in Supplemental B (marker asterisks removed) |
| `attribute_key` | snake_case version of `attribute` for joins |
| `mean_intensity` | Mean on the 0–100 descriptive scale, Supplemental B |
| `n_or_se_if_given` | Empty: Supplemental B gives neither n nor SE |
| `lsd_group` | Fisher LSD letter printed next to the mean (identical letters within an attribute × factor = not significantly different). Empty when no letter was printed |
| `fisher_lsd_main_effect` | Fisher least significant difference for the main effect (Supplemental B column "LSD"); `n.s.` when the factor was not significant; empty where the SI left the cell blank (Black Pepper Aroma) |
| `varied_factor` | roast / tds / pe — which factor this marginal mean varies |
| `significant_interaction` | From the SI asterisks on the attribute name: `roast_x_tds` (*), `roast_x_pe` (**), both separated by `;` |
| `source_table` | `Frost2020_SI Supplemental B` |

Transcription notes: Supplemental B prints "Bitterness ... 37.8" for the
medium roast with no LSD letter (presumably a dropped "b"); left empty as
printed. The SI names the attribute "Broth Flavor" where the main-paper
lexicon (Table 3) says "Brothy flavor"; the SI spelling is kept.

### `frost2020_rsm_coefficients.csv` — header only, 0 rows

Frost2020 prints **no regression coefficients, R² or p-values** for any of
its response surfaces, in the main text, tables or SI (Supplemental C is a 3-D
rendering of Figure 8). The surfaces exist only as contour plots (Figures
8–10). The file is kept with the requested header so downstream code has a
stable path; fill it only if the authors' fitted coefficients become
available.

### `frost2020_rsm_fits_reported.csv` — 46 rows

Which (attribute, roast) combinations Frost2020 reports as having a
significant response-surface fit, and what the text says about model order.
Source: section 3.3 text plus the panel lists of Figures 8, 9 and 10 (panel
titles only, no values read from the contours).

| Column | Meaning |
|---|---|
| `attribute`, `attribute_key` | Attribute named in the figure panel / text |
| `roast_or_pooled` | Light / Medium / Dark, or `pooled (roast removed as blocking factor)` for Figure 10 |
| `significant_fit_reported` | always `yes` (only reported fits are listed) |
| `model_order` | `first`, `second`, or `not_stated` |
| `model_order_source` | The sentence in the paper that states the order; empty when `not_stated` |
| `figure` | Figure 8 (all three roasts), 9 (some roasts), 10 (pooled) |

Text-stated facts recorded here: citrus flavor and sourness were linear for
light and medium roast and second-order for dark roast; the seven Figure 9
attributes were "fit with linear response surfaces"; flavor persistence on
the light roast has a stationary point at 22.6 % PE and 1.37 % TDS (hence
second order). Figure 9 labels the medium-roast panel "Black Pepper Flv."
and the text says "black pepper flavor", although the lexicon (Table 3) and
Supplemental B only contain *black pepper aroma*; the panel label is kept as
printed.

### `frost2020_anova_f_ratios_3factor.csv` — 192 rows

Source: **Frost2020 Supplemental A**, three-factor ANOVA (Coffee = the 27
brews, Judge, Rep and their two-way interactions) for the 32 attributes.
Columns: `attribute`, `attribute_key`, `factor`, `df`, `f_ratio`,
`significant_p_lt_0_05` (from the SI asterisk), `source_table`. The
five-factor ANOVA of main-paper Table 4 was **not** transcribed: its PDF text
layer scrambles the asterisk row alignment and the values could not be
attributed to columns reliably.

### `frost2020_brew_parameters.csv` — 27 rows

Source: **Frost2020 Table 1**. Columns: `coffee_code` (e.g. `L-1.25-20`),
`roast`, `target_tds_percent`, `target_pe_percent`, `duty_cycle_percent`,
`n_cycles` (water pulsing), `brew_ratio_g_water_per_g_coffee`,
`grind_setting`, `source_table`. Measured TDS/PE per brew are shown only in
Figure 4 and were not read off.

### `cotter2021_liking.csv` — 81 rows

Source: **Cotter2021 Table S2** (whole sample, n = 118; 27 rows) and
**Table S3** (Cluster 1, n = 51, and Cluster 2, n = 67; 27 rows each). These
are **two-way interaction cell means**: liking averaged over the third factor
(for example TDS = Low × PE = Medium averages the three brew temperatures).
The 27 individual brew means are **not tabulated** anywhere in the paper or
SI (they appear only as points in Figures 4, 7 and 8), so this file contains
no rows with all three factors set.

| Column | Meaning / origin |
|---|---|
| `tds_level`, `pe_level`, `bt_level` | Low / Medium / High, or `all` when averaged over that factor |
| `tds_percent`, `pe_percent`, `brew_temp_c` | Target value for the level (Cotter2021 Table 1), or `all` |
| `group` | `all` (whole sample), `cluster1`, `cluster2` |
| `n_consumers` | 118 / 51 / 67 (Cotter2021 Figure 8 caption, Table S4 header) |
| `mean_liking_9pt` | "Average Overall Liking" (estimated marginal mean from the `emmeans` package), 9-point hedonic scale |
| `se`, `lower_cl`, `upper_cl` | As printed (standard error and confidence-limit columns) |
| `interaction` | `TDS:PE`, `TDS:BT` or `PE:BT` — which SI block the row comes from |
| `grouping_1_name`, `grouping_1`, `grouping_2_name`, `grouping_2` | The two post-hoc letter columns, with their printed header ("X/Y Groups" = groupings of factor X within each level of factor Y) |
| `source_table` | `Cotter2021_SI Table S2` or `Table S3` |

Cluster-size note: section 3.3 of the main text says the two segments had
"57 and 61 consumers", but Figure 6, Figure 8, Figure S2 and Table S4 all
give n = 51 (Cluster 1) and n = 67 (Cluster 2), and 67/118 = 57 %, 51/118 =
43 % match Guinard2023. The tabulated values 51 / 67 are used.

Cluster-label note: in Cotter2021, **Cluster 1 (n = 51) is the saddle-shaped
surface** (two liking peaks near 6.8: high TDS + low PE, and medium TDS +
high PE) and **Cluster 2 (n = 67) is the dome** (peak ~6.3 at low TDS, PE
16–20 %). Guinard2023 Figure 3 and its text label the 57 % dome segment
"Cluster 1" and the 43 % saddle segment "Cluster 2", i.e. the labels are
swapped relative to Cotter2021. `group` in this file follows Cotter2021.

### `cotter2021_liking_anova.csv` — 22 rows

Source: the ANOVA blocks of **Table S2** (whole-sample mixed model,
`Liking~(TDS+PE+BT)^2+(1|Judge)+(1|Judge:Week)+(1|Judge:TDS)`, with
numerator and denominator df) and **Table S3** (fixed model
`Liking~(TDS+PE+BT+Cluster)^4`, df only). Columns: `model`, `formula`,
`term`, `sum_sq`, `mean_sq`, `num_df`, `den_df` (empty for Table S3),
`f_value`, `p_value`, `source_table`.

### `cotter2021_rsm_coefficients.csv` — header only, 0 rows

Cotter2021 fitted second-order surfaces of liking vs **measured** TDS and PE
for the whole sample, Cluster 1 and Cluster 2 (section 2.7.3, Figure 8), but
**prints no coefficients, R² or p-values**. The only numeric statements about
the surfaces are in the text: Cluster 1 two peaks each near 6.8; Cluster 2
peak ~6.3 at low TDS and PE 16–20 %; whole sample peak ~6.0 in the region
TDS 1.1–1.3 % and PE 19–24 % (section 3.4) / 19–23 % (section 4). Guinard2023
adds that the dome (Cotter Cluster 2) "peaked at 18 % extraction".

### `cotter2021_jar_penalty_text_values.csv` — 19 rows

The just-about-right and penalty-analysis numbers that the main text quotes
from Figure 11 and Figure S2 (both figure-only). Columns: `cluster`,
`factor`, `level` (`all` for the penalty rows, which pool all 27 coffees),
`jar_question`, `response`, `percent_of_responses`, `hedonic_penalty_9pt`
(mean liking of JAR raters minus mean liking of the non-JAR raters; `<0.4`
kept as printed), `source`. The full per-level JAR distributions of Figure 11
were **not** read off the figure.

### `cotter2021_brew_parameters.csv` — 27 rows

Source: **Cotter2021 Table S1**, one row per target (TDS, PE, BT) profile:
ground coffee mass, grind setting (smaller = finer), brew length, water
on/off pulse times and cycle count, water volume (2.934 L, from the caption),
and the mean ± 2 SD over the 6 replicate batches of measured TDS, calculated
PE, batch temperature, serving temperature and first-sip temperature (the
"±" values are split into `*_mean_*` and `*_2sd` columns). These measured
TDS/PE means are the coordinates the authors used for their response
surfaces.

## What is available and what is not

| Quantity | Frost2020 | Cotter2021 |
|---|---|---|
| Per-brew (27) attribute or liking means | **Not published** (figures only) | **Not published** (figures only) |
| Marginal means by factor level | Yes — all 32 attributes (`frost2020_sensory_means.csv`) | Only as two-way cell means (`cotter2021_liking.csv`); one-way means are in Figures 4 and 7 only |
| Response-surface coefficients | **None printed** | **None printed** |
| Which fits were significant + model order | Yes, partial (`frost2020_rsm_fits_reported.csv`) | Text only: second-order for all three groups |
| ANOVA F-ratios / p-values | Supplemental A transcribed; main-paper Table 4 not | Tables S2, S3 transcribed |
| JAR percentages | n/a | Text-quoted values only |
| Brew parameters per brew | Table 1 transcribed | Table S1 transcribed (with measured TDS/PE) |
| Brew water recipe | Not stated | Stated (see above) |

Frost2020 attributes with a reported response-surface fit for **all three
roasts**: burnt wood/ash flavor, citrus flavor, sourness, bitterness,
sweetness, thickness, flavor persistence. For **some roasts**: astringency
(light, dark), earthy flavor (light, medium), fermented flavor (light),
rubber flavor (light, medium), black pepper "flavor" (medium), blueberry
flavor (medium), brown spice flavor (medium), dark chocolate flavor (medium),
roasted flavor (medium). **Pooled over roast** (13): sourness, citrus,
astringency, bitterness, fermented, roasted, rubber, burnt wood/ash, dried
fruit, flavor persistence, thickness, earthy, sweetness. Attributes with no
significant fit at any roast (the remaining 16 of 32) have only the marginal
means.

## Licence

The numbers in these CSVs are measured means, regression/ANOVA statistics
and experimental settings transcribed from the copyrighted papers listed
above (Frost2020 and Cotter2021 are © Institute of Food Technologists /
Wiley; Guinard2023 is CC BY-NC-ND 4.0). They are facts about the experiments,
not the papers' text, figures or expression, and are provided here for
research use with citation of the original papers. The papers themselves and
their supporting-information files are not redistributed. If you reuse these
tables, cite the original articles, not this repository, as the data source.
