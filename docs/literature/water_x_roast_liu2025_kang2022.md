# Water type × roast level in brewed coffee — extraction of Liu et al. 2025 and Kang, Piao & Ko 2022

Purpose: record what these two papers measured and found about brewing-water mineral content (alkalinity, hardness, TDS) crossed with roast level, and state what each does and does not support in our model. Our model: residual acidity = brew titratable acidity minus the protonated share of the brewing water's alkalinity; cation (Ca, Mg, Na) effects are treated as secondary.

Date of extraction: 2026-09-14. Sources read in full: `private/papers/Liu2025.pdf` (10 pages), `private/papers/Liu2025_SI_1.docx`, `Liu2025_SI_2.docx`, `Liu2025_SI_3.docx` (text pulled from `word/document.xml`), `private/papers/Kang2022.pdf` (7 pages). Every number below is transcribed as printed. Where a value exists only as a bar or line in a figure, it is marked "read from figure" with the axis range; treat those as ±3 % of axis span.

Access legend: FULL TEXT = read from the PDF or supplementary file itself.

---

## 1. Liu et al. 2025 — FULL TEXT

### 1.1 Citation
Liu, Y., Lin, J., Hu, S., Wang, G., Yang, C., Zhang, Z., Ren, D., Yi, L., Li, S. (2025). Exploring the impacts and mechanisms of water on the taste extractions and perceptions of coffee brews: A case study in filter brewing. *Journal of Food Composition and Analysis* 146, 107987. DOI 10.1016/j.jfca.2025.107987. Received 10 March 2025, accepted 1 July 2025, online 3 July 2025. Affiliations: Kunming University of Science and Technology; Kunming Gemmy Food Co., LTD (the water supplier). Funding includes "Gemmy 'Coffee Brewing Water' Development and Mechanism Investigation [Grant No. 2024KF2]". Declaration of competing interest: "I have nothing to declare." Data: "available on request."

### 1.2 Waters (Table 1, p. 5; methods in Supplementary materials 1)
Three waters, all from Kunming Gemmy Food Co.: natural source water (NSW) from a volcanic spring in Pingbian Miao Autonomous County, Yunnan (103°35'E–103°48'E, 22°28'N–23°01'N, altitude 1600 m); the same water after the company's industrial purification but before ultra-filtration (BFW, "before filtration water"); and after ultra-filtration (AFW, "after filtration water"). Panelists judged all three "tasteless".

Table 1 — "Physiochemical indexes of different water samples" (mean ± SD, n = 3; different letters = significant difference at p < 0.05 within a row):

| Index | AFW | BFW | NSW |
|---|---|---|---|
| pH | 6.64 ± 0.01 c | 6.97 ± 0.01 b | 7.15 ± 0.01 a |
| Alkalinity (mg/L as CaCO3) | 32.44 ± 5.4 b | 50.44 ± 3.12 a | 52.24 ± 3.12 a |
| Hardness (mg/L as CaCO3) | 21.62 ± 6.24 b | 65.46 ± 3.75 a | 69.96 ± 5.12 a |
| Hardness level (WHO) | Soft | Moderately hard | Moderately hard |

Not reported: Ca, Mg, Na, K individually; TDS; conductivity. The paper only says the spring water has an "abundance of mineral cations" and, for the simulation, sets CaCO3 at "20 mg/L for AFW, 70 mg/L for NSW" (Section 2.14), i.e. it treats hardness as calcium carbonate.

Alkalinity method (SI 1, section 1): 50 mL sample, 4 drops of 0.5 g/L methyl orange, titrated with 0.05 mol/L HCl "until the endpoint (yellow to orange)". Result as CaCO3 with the factor 50.04 (equivalent weight of CaCO3). This is a total-alkalinity titration to the methyl-orange endpoint (about pH 4.4), so it counts bicarbonate and carbonate.
Hardness method (SI 1, section 2): EDTA (0.01 mol/L Na2EDTA) titration with Eriochrome Black T in NH4Cl–NH4OH buffer, result as CaCO3 with factor 100.09. Total hardness (Ca + Mg).
Authors' comparison with the guidelines they cite (Section 3.1): pH "6–8 in SCAA, 6.5–8 in SCAE" met by all three; alkalinity "40–70 ppm CaCO3 in SCAA, 40–75 in SCAE" and hardness "50–175 ppm CaCO3 in SCAA, 75–250 ppm CaCO3 in SCAE" were "much lower than the requirements" for AFW.

### 1.3 Coffees and roast levels
"Superior dark and light roasted coffee beans (Coffea arabica L.) were purchased from a local supermarket", green beans from Lincang city, Yunnan. Roast level is the retailer's label; no Agtron, colour, roast temperature or time is given. Abbreviations DRC (dark roasted coffee) and LRC (light roasted coffee). Particle size (Fig. 3E, laser diffraction, 0.01–2500 µm range): both distributions peak near 1000 nm on the printed axis (read from figure; the axis label says "Particle size (nm)" with range 0–2500, which is inconsistent with the "fine-medium" grind described in the text and with the SEM scale bars; treat as unresolved).

### 1.4 Brewing (Section 2.3)
Grinder: Mongdio (China), "fine-medium". Filter brewing with a KOUPHIN filter paper and brewing chamber: 15 g ground coffee, 240 g boiling water "poured into and flowed through the coffee grains", brew collected "within 2 min". Ratio 1:16. Six brews: DRC-AFW, DRC-BFW, DRC-NSW, LRC-AFW, LRC-BFW, LRC-NSW. Sensory evaluation "immediately after the collection".

### 1.5 What was measured
Chemical, on the brews:
- Chlorogenic acids and lactones (9 subgroups), caffeine, trigonelline, theobromine, nicotinamide by HPLC-QqQ-MS/MS (Section 2.7; MS transitions in SI 2 Table A.1). Reported only as relative "peak area values" in a colour heat map (Fig. 1, scale "Very low" to "Very high"); no concentrations, no table of values.
- Seven organic acids by HPLC-QqQ-MS/MS (Section 2.8): citric, fumaric, lactic, malic, nicotinic, quinic, succinic. Same relative heat-map presentation in Fig. 1.
- Not measured on the brews: pH, titratable acidity, TDS, extraction yield. Water retention (%) and draining speed (g/s) of the grounds were measured (Table 2).
Mechanistic, on spent-ground protein extracts (CPE): fluorescence (Fig. 4A–H), circular dichroism (Fig. 4I), 500 ns molecular dynamics of proteins A0A6P6TKT8 and A0A6P6TRT9 with 3-O-caffeoylquinic acid, citric acid and caffeine in "AFW-like" (CaCO3 20 mg/L) and "NSW-like" (CaCO3 70 mg/L) boxes at pH 7.0 (Figs 5–6).
Sensory (Sections 2.9, 3.2.2): 11 healthy volunteers (4 men, 7 women, 18–35 years), trained to rate caffeine and citric acid in water at 200 / 400 / 600 mg/L as low / medium / high. In the formal test they rated "bitterness/acidity degrees (low/medium/high)" for each brew, in triplicate. The reported statistic is the "taste recognition percentage": the percentage of the 11 panelists that assigned a given level to a given sample. Comparisons are only within a coffee across the three waters (DRC-AFW vs DRC-BFW vs DRC-NSW; LRC-AFW vs LRC-BFW vs LRC-NSW) — never across roasts.

### 1.6 Main results

(a) Brew acidity vs water alkalinity / hardness — sensory only (Fig. 2, p. 6). Bar heights read from figure; panel A y-axis 0–90 %, panel B y-axis 0–80 %; letters as printed above the bars (different letter = p < 0.05, n = 3, within one taste level and one coffee).

Dark roast (Fig. 2A):

| Rating | AFW (soft, alk 32.44) | BFW (alk 50.44) | NSW (alk 52.24) |
|---|---|---|---|
| Low acidity | ~45 a | ~40 a | ~13 b |
| Medium acidity | ~32 ab | ~45 a | ~23 b |
| High acidity | ~23 b | ~13 b | ~63 a |
| Low bitterness | ~50 a | ~32 b | ~18 c |
| Medium bitterness | ~27 b | ~27 b | ~45 a |
| High bitterness | ~23 a | ~40 a | ~37 a |

Light roast (Fig. 2B):

| Rating | AFW | BFW | NSW |
|---|---|---|---|
| Low acidity | ~45 a | ~18 b | ~36 a |
| Medium acidity | ~36 a | ~45 a | ~18 b |
| High acidity | ~18 b | ~36 b | ~45 a |
| Low bitterness | ~14 c | ~36 b | ~50 a |
| Medium bitterness | ~23 c | ~45 a | ~32 b |
| High bitterness | ~64 a | ~18 b | ~18 b |

Authors' reading (Section 3.2.2, verbatim): "DRC-NSW, DRC-BFW and DRC-AFW exhibited statistically high, medium and low acidity, respectively. Meanwhile, LRC-AFW, LRC-BFW and LRC-NSW exhibited statistically high, medium and low bitterness, respectively. Both DRC and LRC brews didn't exhibit significant and recognizable differences in their first dominant taste perceptions." (First dominant taste: bitterness for DRC, acidity for LRC.)
Direction of the effect: the water with the highest alkalinity and hardness (NSW) gave the highest perceived acidity in the dark roast and also the most "high acidity" votes in the light roast (~45 %, letter a, vs AFW ~18 %, letter b). The softest, lowest-alkalinity water (AFW) gave the lowest perceived acidity in the dark roast and the most "low acidity" votes in the light roast. This is the opposite of what bicarbonate neutralisation alone would predict.
Chemical side (Fig. 1 heat maps, qualitative): "In DRC and LRC, NSW and AFW exhibited the highest extraction efficiencies toward the majority of the taste compounds, respectively." In Fig. 1A (dark roast) the NSW column is the reddest for all seven organic acids and all chlorogenic-acid subgroups; in Fig. 1B (light roast) the AFW column is reddest. The authors attribute the higher acidity of DRC-NSW to more organic acid extracted, not to any pH or buffering mechanism.

(b) Roast × water interaction: no factorial test was run (one-way ANOVA within each coffee). Descriptively, the ranking of waters by extraction flips with roast: NSW extracts most from dark roast, AFW extracts most from light roast (Fig. 1). The sensory effect on the secondary taste follows the extraction: acidity rises with NSW in dark roast; bitterness rises with AFW in light roast. Proposed mechanism (Sections 3.3–3.5): dark-roast grounds are more porous and drain slower (Table 2 draining speed g/s: DRC-AFW 0.92 ± 0.01 bc, DRC-BFW 0.89 ± 0.02 cd, DRC-NSW 0.84 ± 0.01 d; LRC-AFW 0.96 ± 0.03 b, LRC-BFW 0.98 ± 0.03 ab, LRC-NSW 1.03 ± 0.04 a; water retention % 13–15.9, all letter a), and calcium in NSW is proposed to act as "salt-bridges" that pull taste compounds off coffee proteins in dark roast (Fig. 5), whereas in light roast the more complex protein set (A0A6P6TKT8 + A0A6P6TRT9) binds compounds more tightly in NSW, so AFW releases more (Fig. 6). Hardness "was negatively and positively correlated with the draining speeds of DRC and LRC, respectively" (Section 3.3; no coefficient given).

(c) Recommendation per roast (Conclusion, verbatim): "NSW and AFW benefited the extraction of taste compounds and the perception of secondary dominant tastes for DRC and LRC, respectively." So: mineral-rich spring water (hardness ~70, alkalinity ~52 mg/L CaCO3) if you want more acidity from a dark roast; ultra-filtered soft water (hardness ~22, alkalinity ~32) if you want more bitterness from a light roast. The authors frame this as "the coffee-water pairing standard is flexible", not as a quality recommendation.

### 1.7 Statistics
One-way ANOVA, SPSS 20.0, p < 0.05, n = 3 for water indexes, retention and sensory recognition percentages. No post-hoc test named. No two-way model, no effect sizes, no correlation coefficients printed.

### 1.8 Limitations stated by the authors
- "a comprehensive quantification of all taste compounds, a reliable threshold detection and an accurate calculation of the total bitterness/acidity activity values of all coffee brews were unrealistic due to the difficulty in obtaining chemical standards of high purity" (Section 3.2.2).
- Only relative extraction (peak areas) was compared; the first dominant taste could not be differentiated, which they attribute to compound levels "far beyond their thresholds".
- "research in the future should focus on investigating the roles specific minerals in water (such as Na+, Mg2+, K+, Ca2+) play" (Conclusion) — i.e. cation composition was not resolved.
Limitations I add: roast level is a retail label; hardness and alkalinity co-vary (both low in AFW, both high in BFW/NSW), so the two cannot be separated; brew pH/TA/TDS were not measured; 11 panelists with a 3-level categorical scale; the water producer co-authored and funded the work.

### 1.9 What this supports and does not support in our model
- Does not test our equation. No brew TA, pH or TDS was measured, so there is no number to compare against "TA minus protonated alkalinity".
- The alkalinity spread is small: 52.24 − 32.44 = 19.8 mg/L as CaCO3, which is 0.40 meq/L of bicarbonate (my arithmetic: 19.8 / 50.04). Our model would predict a small drop in residual acidity for NSW relative to AFW. The panel instead perceived NSW brews as more acidic in the dark roast (Fig. 2A, "high acidity" ~63 % vs ~23 %). The paper's own explanation is more organic acid extracted with the harder water (Fig. 1A). So in this dataset any buffering effect of 0.4 meq/L extra alkalinity is swamped by a change in extraction, in the direction of more acid with harder/more alkaline water for dark roast.
- This is direct evidence that treating cation effects as secondary is unsafe at the dark-roast end when hardness changes by ~50 mg/L CaCO3 alongside alkalinity. The data cannot say whether the driver is Ca/Mg (extraction) or alkalinity, because they move together.
- For the light roast the sensory picture is mixed: NSW gave the most "high acidity" votes (~45 %, a) but also many "low acidity" votes (~36 %, a), and the extraction heat map (Fig. 1B) says AFW extracted the most acid. So for light roast there is no clean direction to import.
- Usable facts: the water table itself (Table 1) as a real example of a soft spring-derived water set; the finding that water effects on perceived acidity flip sign between light and dark roast, which our model (a single subtraction with no roast term other than TA) cannot produce. Anything roast-dependent in our model must enter through the extraction of acids, not through alkalinity.

---

## 2. Kang, Piao & Ko 2022 — FULL TEXT

### 2.1 Citation
Kang, G.W., Piao, Z. (Zoey), Ko, J.Y. (2022). Effects of water types and roasting points on consumer liking and emotional responses toward coffee. *Food Quality and Preference* 101, 104631. DOI 10.1016/j.foodqual.2022.104631. Received 31 December 2021, accepted 16 May 2022, online 18 May 2022. Kyung Hee University (Seoul) and University of Central Florida.

### 2.2 Waters (Table 1, p. 3)
Three waters chosen for "(1) easy access and (2) TDS with a gap of approximately 100 ppm". TDS measured by "the Environment Analysis Center of Water Research"; only the class is printed.

| Code | Description | Total Dissolved Solid | Source |
|---|---|---|---|
| L | purified water, RO filter (Coway CHP-7300R) | Low (0 ~ 3 mg/L) | Korea |
| M | tap water (Seoul, Hoegi-dong, Paldang Dam supply) | Medium (≒100 mg/L) | Korea |
| H | bottled water from Australia (local mart in Hoegi-dong) | High (≒200 mg/L) | Australia |

Not reported: hardness, alkalinity, Ca, Mg, Na, pH, brand of the Australian water. The Discussion (p. 6) says the study "did not measure the chemical alterations/amounts in the beans or beverages" and names alkalinity, sulfate, chloride and sodium as unmeasured. In the Discussion the L and H waters are re-described as "under 10 ppm TDS" and "over 95 ppm TDS", which does not match Table 1's ≒200 mg/L for H; take Table 1 as the primary statement.

### 2.3 Coffee and roast levels (Section 2.2)
One green coffee: Guatemala, San Pedro Necta, Huehuetenango, SCAA specialty grade, bought in Seoul. Roasted on a Proaster THCR-03 at a local shop to three points, defined by Agtron number on a RoAmi roast analyzer plus a barista's taste check:
- Light: Agtron 60–70; 1st crack at 9'0" (195 °C); output temperature 214 °C; total 12'11".
- Medium: Agtron 50–60; 1st crack 9'10" (194 °C), 2nd crack 12'5" (219 °C); output 220 °C; total 12'14".
- Dark: Agtron 40–50; 1st crack 9'15" (194 °C), 2nd crack 12'5" (216 °C); output 226 °C; total 12'44".
Cooled four minutes with air, rested "at least three days" in degassing-valve bags at 22 ± 2 °C.

### 2.4 Brewing (Section 2.3)
French press (Bialetti 8C, 1 L), not filter. Grind 1 mm (Kalita Japan Coffee Café Grinder Nice Cut Mill), ground within 15 min of brewing. 45 g coffee + 900 mL water at 90 °C (5 g/100 mL, i.e. 1:20), stirred twice in five circles (at start and at 1 min), pressed at 2 min. Held in 2 L stainless bottles up to 15 min, served at 70 °C in coded 6.5 oz paper cups, 100 mL per sample. Nine samples (3 roasts × 3 waters) served light → dark, water order randomised within roast; sessions of five participants.

### 2.5 What was measured
Chemical: nothing on the brews — no pH, TA, TDS or extraction yield.
Sensory: 167 untrained consumers (62 men, 105 women; age 20–29: 93, 30–39: 43, 40–49: 24, 50+: 7; Table 3), 9-point hedonic scale (1 strongly dislike – 9 strongly like) for appearance, flavor, taste, aftertaste, overall; 31-term CATA emotion lexicon (Table 2, from Bhumiratana et al. 2014 and Hu & Lee 2019). No intensity ratings, no sourness or acidity attribute.

### 2.6 Main results

(a) Liking vs water TDS, by roast (Table 4, p. 4; means on a 9-point scale; superscript letters from Duncan's test across all nine samples within a column, same letter = not different at p < 0.05; "ns" = column not significant):

| Roast | Water | Appearance | Flavor | Taste | Aftertaste | Overall |
|---|---|---|---|---|---|---|
| Light | L | 3.891 ab | 3.970 ab | 3.794 abc | 3.842 ns | 3.709 abc |
| Light | M | 3.739 a | 3.727 a | 3.539 a | 3.582 ns | 3.558 a |
| Light | H | 3.806 ab | 3.861 ab | 3.570 a | 3.606 ns | 3.582 a |
| Medium | L | 4.309 c | 4.279 c | 4.055 bc | 4.000 ns | 4.000 c |
| Medium | M | 4.248 c | 4.055 bc | 3.885 bc | 3.927 ns | 3.927 bc |
| Medium | H | 3.752 a | 3.976 ab | 3.752 ab | 3.709 ns | 3.709 abc |
| Dark | L | 4.279 c | 4.085 bc | 4.091 c | 3.958 ns | 3.988 c |
| Dark | M | 4.067 bc | 4.103 bc | 3.897 bc | 3.776 ns | 3.842 abc |
| Dark | H | 3.855 ab | 3.958 ab | 3.782 abc | 3.745 ns | 3.661 ab |
| F-value | | 5.258 *** | 2.087 * | 2.791 ** | 1.838 | 2.251 * |

(* p < 0.05, ** p < 0.01, *** p < 0.001.) Fig. 1 (p. 5) plots the same means as line charts, y-axis "liking (9-point Likert scale)", no numeric axis ticks printed.

Authors' statements (Abstract and Section 3.1): "Consumer liking decreased in relation to increasing TDS at the medium and dark roasting points. Coffee brewed using purified water was preferred by coffee consumers at medium and dark roasting points." "the M–L and M–M coffee samples obtained the highest liking ratings for appearance, whereas the L-M and M–H were the least favorable. In terms of flavor liking, the M–L sample obtained the highest rating, whereas the L-M was the least favorable. Regarding taste liking, the D-L sample received the highest rating, whereas the L-M and L-H samples were the least favorable." Discussion: "coffee with a low mineral (under 10 ppm TDS) brewing water was preferred more than high mineral water (over 95 ppm TDS) among all roasting points."
Reading the letters strictly, within one roast the L-vs-H difference is significant for: appearance at medium (c vs a) and dark (c vs ab); flavor at medium (c vs ab); overall at dark (c vs ab). It is not significant for taste at any roast (medium bc vs ab share b; dark c vs abc share c), nor for overall at medium (c vs abc share c), nor for anything at light roast. All nine means sit between 3.5 and 4.3 on a 9-point scale, i.e. below the neutral point of 5.

Sourness/acidity: not measured. The only link is the authors' speculation in the Discussion: "Some authors have found that as the amount of minerals decreases, coffee becomes excessively sour ... However, our findings suggest that consumers generally have a high liking for coffee with low mineral brewing water. This may mean that consumers like the sour taste of the coffee more than the strong taste of the coffee." No pH, TA or sourness data support or contradict this.

(b) Roast × water interaction: not tested. The design is analysed as one-way ANOVA over nine samples, not as a 3 × 3 factorial. Descriptively, water had no significant effect at light roast, and low-TDS water scored highest at medium and dark roast on appearance and (for dark) overall. The emotion CATA (Table 5, Fig. 2) puts L-L (light roast, purified water) alone near "quiet" and "annoyed"; M-L near "energetic", "nostalgic", "independent", "adventurous", "focused"; D-H, D-L, M-H, D-M near "disgusted" and "empowering"; L-M and M-M near "merry". Correspondence analysis dimensions F1 + F2 explain 71.45 %.

(c) Recommendation per roast: purified (RO, TDS 0–3 mg/L) water for medium and dark roast (Abstract). For light roast the authors say "the light roast coffee with medium TDS water showed a low liking in all significant attributes" (Discussion), but Table 4 letters show no significant within-light-roast difference. The paper frames the recommendation as commercial guidance for cafés and bottled-water labelling, not as a chemistry rule.

### 2.7 Statistics
XLSTAT 2019.4. One-way ANOVA with Duncan's multiple range test (p < 0.05) on liking; Cochran's Q test on CATA frequencies with McNemar post-hoc; correspondence analysis on the CATA contingency table. Experiments "performed and duplicated" (Section 2.6). N = 167 consumers rating all nine samples in one session.

### 2.8 Limitations stated by the authors (Discussion, p. 6)
- "Samples representing other beans, roast levels, and brewing water—in detail, not only TDS, but also alkalinity, sulfate, chloride, and sodium content in the water—could produce different results."
- No temporal measures (liking may change over repeated sips).
- "our study only measured the minerals in brewing water but did not measure the chemical alterations/amounts in the beans or beverages during processing, roasting, or brewing. It means that any information regarding the effect of chemistry on the sensory experience is based on previous literature rather than a direct result of this study."
- Single consumer cluster; no segmentation.
Limitations I add: French press at 1:20 and 90 °C, not filter; the Australian bottled water is unnamed, so its hardness/alkalinity split is unknown; TDS values are approximate classes; nine samples in one 20-minute session with paper cups; all means below 5/9.

### 2.9 What this supports and does not support in our model
- Does not test our equation: no brew acidity, pH or TDS, and no water alkalinity. TDS alone does not tell us how much of the 100 or 200 mg/L is bicarbonate versus Ca/Mg sulfate or chloride, so the alkalinity term in our model cannot be estimated for these waters.
- Supports only a weak, indirect statement: for medium and dark roast, consumers liked the RO-water brew (alkalinity necessarily near 0, so residual acidity ≈ full brew TA) at least as much as, and on appearance/overall significantly more than, the ~200 mg/L TDS brew. Higher mineral load did not improve liking of dark roast, which is consistent with the notion that reducing acidity of a dark roast (already low TA) is not what consumers want, but the paper does not measure acidity so this is inference, not evidence.
- Contradicts nothing in our model; it simply does not reach it. It is usable as a citation that (i) water effects on liking were absent at light roast and present at medium/dark in a 167-consumer test, and (ii) consumer liking did not penalise zero-mineral water, contrary to the Pangborn 1971 "too sour" claim the authors cite.
- Do not import a "roast × water interaction" from this paper into the model: none was tested.

---

## 3. Ten-line summary

1. Liu et al. 2025 (J. Food Compos. Anal. 146:107987) brewed one dark and one light retail arabica by paper filter (15 g / 240 g boiling water, ~2 min) with three related waters: ultra-filtered AFW (pH 6.64, alkalinity 32.44, hardness 21.62 mg/L CaCO3), BFW (6.97 / 50.44 / 65.46) and spring NSW (7.15 / 52.24 / 69.96); Table 1, n = 3.
2. Liu measured no brew pH, TA or TDS; only relative HPLC-MS peak areas (Fig. 1 heat maps) and an 11-person trained panel rating acidity and bitterness as low/medium/high (Fig. 2).
3. Liu's key sensory result: dark roast brewed with the hardest, most alkaline water (NSW) was rated "high acidity" by ~63 % of panelists vs ~23 % with soft AFW (read from Fig. 2A, y-axis 0–90 %, letters a vs b); AFW gave the most "low acidity" (~45 %).
4. Liu explains this by extraction, not buffering: NSW pulled the most organic acids and chlorogenic acids out of dark roast, AFW the most out of light roast (Fig. 1); they propose calcium salt-bridging with coffee proteins (Figs 4–6) and slower drainage of dark-roast grounds in hard water (Table 2).
5. For our model, Liu shows that a 19.8 mg/L CaCO3 (0.40 meq/L) alkalinity difference was outweighed by an extraction effect in the opposite direction for dark roast; hardness and alkalinity co-vary in their waters, so the cation and alkalinity contributions cannot be separated.
6. Kang, Piao & Ko 2022 (Food Qual. Prefer. 101:104631) used one Guatemalan coffee at Agtron 60–70 / 50–60 / 40–50 and three waters defined only by TDS: RO 0–3 mg/L, Seoul tap ≒100 mg/L, Australian bottled ≒200 mg/L (Table 1); French press 45 g / 900 mL at 90 °C, 2 min.
7. Kang measured no chemistry at all on water (beyond TDS) or brew; 167 consumers gave 9-point liking and CATA emotions.
8. Kang's Table 4: overall liking 3.558–4.000 across nine samples; RO water scored highest at medium (4.000 c) and dark (3.988 c) roast, and significantly above ~200 mg/L water only for dark-roast overall (3.661 ab) and for appearance/flavor at medium; no significant water effect at light roast.
9. Neither paper ran a factorial roast × water test; both report per-roast one-way ANOVAs. Neither measured sourness intensity, pH or TA, so neither gives a number for how brew acidity moves with alkalinity.
10. Net: these two papers do not validate or quantify "residual acidity = TA − protonated alkalinity"; Liu warns that at dark roast a harder/more alkaline water can raise perceived acidity via extraction, and Kang shows consumers did not dislike zero-mineral (zero-alkalinity) water at any roast. Batali 2021 / Frost 2020 / Hendon 2014 remain the sources for the actual acidity-vs-water numbers.
