# Bottled mineral waters — label chemistry (v0)

`bottled_waters_v0.csv` is a compilation of the mineral analysis printed on the labels (or published on the brand's website) of bottled waters sold in supermarkets in Brazil, the United States, the United Kingdom, Germany, France, Italy and Portugal. It exists so the coffee-brewing project can look up the calcium, magnesium and bicarbonate content of waters a reader can actually buy.

Every value is copied as printed by the brand (or by the retailer reproducing the label). Nothing is estimated, converted between units, or filled from memory. A cell is empty when the source does not print that value. Retrieval date for every row: 2026-09-14. One row per product; a brand appears more than once when it bottles from several named sources or sells a market-specific label (for example Evian in FR, GB and US).

## Coverage (2026-09-14)

| Country of sale | rows | brand_site | label_photo_official | official_regulator | third_party |
|---|---|---|---|---|---|
| Brazil (BR) | 49 | 27 | 19 | 0 | 3 |
| United States (US) | 47 | 46 | 1 | 0 | 0 |
| United Kingdom (GB) | 9 | 7 | 0 | 0 | 2 |
| Germany (DE) | 25 | 25 | 0 | 0 | 0 |
| France (FR) | 21 | 15 | 6 | 0 | 0 |
| Italy (IT) | 19 | 13 | 6 | 0 | 0 |
| Portugal (PT) | 17 | 13 | 3 | 1 | 0 |
| **Total** | **187** | **146** | **35** | **1** | **5** |

- Distinct brand-and-market pairs: 158.
- Rows with bicarbonate printed: 140; rows with alkalinity printed instead (no bicarbonate): 17; rows with neither: 30.
- Rows with both calcium and magnesium: 159.
- Rows with dry residue at 180 °C: 78; with TDS / "mineralização total": 63; with pH: 144.
- Sparkling rows (kept because the brand sells no still water and is a major seller, or the source is naturally carbogaseous): Uliveto (IT), Pedras Salgadas (PT), Frescca sparkling label (BR). Everything else is still water.

## Columns

| column | meaning |
|---|---|
| brand, product_name | as printed / as named on the source page |
| country_of_sale | ISO-2: BR, US, GB, DE, FR, IT, PT |
| carbonation | still / sparkling |
| source_name, source_location | spring or well name and place, as printed |
| water_type | natural mineral water / spring water / purified / remineralised / artesian / other, as declared |
| calcium_mg_l … fluoride_mg_l | mg/L as printed. US water-quality reports print ranges such as `ND - 17` (ND = not detected); these strings are kept verbatim. `<0.1` style strings are kept. |
| ph | as printed (US reports may give a range) |
| dry_residue_180c_mg_l | "resíduo de evaporação / résidu sec / residuo fisso / Trockenrückstand at 180 °C". Where the label states a different or no temperature, `units_notes` says so. |
| tds_mg_l | "TDS / Total Dissolved Solids" (US), or the Portuguese "mineralização total" (sum of ions plus silica, not a gravimetric residue — flagged in `units_notes`). |
| alkalinity_as_printed | the alkalinity string when the label prints alkalinity instead of (or in addition to) bicarbonate, with the unit the label gives (US reports: "Alkalinity, Total as CaCO3") |
| hardness_as_printed | the hardness string when printed ("dureza", "Gesamthärte", "durezza in °F", "Total Hardness as CaCO3") |
| analysis_or_label_date | analysis date, laboratory report number (Brazil: LAMIN/CPRM number) or report year, if printed |
| source_url | the page or PDF the values were read from |
| retrieval_date | 2026-09-14 for every row |
| provenance_flag | see below |
| units_notes | anything about units: decimal commas converted to points, g/L labels kept verbatim (Rheinfels Quelle), nitrate as N vs as NO3, ± uncertainties |
| notes | partial rows, other ions printed (silica, strontium, barium…), cross-checks, caveats |

## Provenance flags

- `brand_site` — the brand's or brand owner's own web page or PDF (product page, "análise química", "Mineralstoffgehalt", US "Water Quality Report"). Preferred.
- `label_photo_official` — the label text, or the manufacturer's technical sheet, reproduced on a retailer or distributor page (Pão de Açúcar, Pingo Doce, Auchan, Conad, Raja, Amazon…). Official content, second-hand host.
- `official_regulator` — a regulator document: DGEG Hidrogenoma (Portugal). Brazilian rows quoting a LAMIN/CPRM or ANM analysis number keep `brand_site` / `label_photo_official` because the number was read from the brand's or retailer's page, not from the regulator.
- `third_party` — a compilation site or Wikipedia. Used for 5 rows only, where the brand publishes nothing: Charrua, Sferriê and São Lourenço (BR), Brecon Carreg and Princes Gate (GB). Treat these as unverified.

Pages that return HTTP 403 to scripted fetchers (Nestlé Waters sites: Buxton, Vittel, Contrex, Hépar, Acqua Panna) were read in a desktop browser; `notes` says so.

## Partial rows (official source prints only some values)

Vittel (Ca only), Contrex (Ca, Mg, Na), Hépar (Mg, Na), Thonon, Courmayeur, Saint-Amand, Carola, Volvic FR (no dry residue / pH), Sant'Anna, Lauretana, San Bernardo, Plose, Surgiva, Fonte Essenziale, Lurisia, Rosbacher, hassia, Aqua Römer Still, SELTERS (no Mg), Sparkletts / Alhambra / Crystal Springs / Hinckley Springs / Mount Olympus (one generic 2017 DS Services sheet: Cl, SO4, TDS, pH only), Aquafina / LIFEWTR / Dasani (regulated parameters only), Glaciar, São Silvestre, Salutis, Serra Catarinense (pH and residue only), Sferriê.

## Known gaps — brands with no published analysis found (details and every URL tried are in SOURCES.md)

- **Brazil:** Indaiá, Petrópolis (domain parked), Ingá (site says values are label-only), Schin, Santa Joana, Pouso Alto, Puríssima, Poá, Lindoya Vida, Lindoya Mineral / Premium / Vitalis, Acqua Lindoya, Nova Lindoya, Fonte da Ilha, Fonte Ijuí, Itaipava, Neblina, Fonte Roriz, Serra Grande, Bem Viver, Fonte Vale, Água Doce, Aquarel (no Brazilian product), Acqua Vita (Araçatuba). São Lourenço has only a rounded third-party row. Minalba Brasil brands publish no numbers on the web.
- **United States:** smartwater (official reports print no concentrations), Kirkland Signature, Great Value, Member's Mark, Kroger, 365 Whole Foods, Trader Joe's, Safeway Refreshe (retailer sites bot-walled), Topo Chico (no still product), Boxed Water, Path, Open Water, Proud Source (report is images), Castle Rock, Absopure, Chippewa Springs, Crystal Rock, Hawaiian Isles, AQUAhydrate, Iceland Spring (pH only), Aqua Carpatica US, Volvic US, Origin.
- **United Kingdom:** Harrogate Spring (no numbers published), Radnor Hills, Strathmore, Aqua Pura, Life Water, Speyside Glenlivet, Smartwater UK, Nestlé Pure Life UK, Tesco Ashbeck / Scottish, Sainsbury's Caledonian, Asda Eden Falls, Waitrose Essential, M&S, Aldi Aqua Select, Lidl Saskia UK (retailer sites 403 or JavaScript-only).
- **Germany:** Apollinaris (no still product found), Volvic DE, Vittel DE, Bad Liebenwerda, Franken Brunnen, Siegsdorfer Petrusquelle, Ensinger Sport Still, Saskia (Lidl), Ja! (Rewe), Gut & Günstig (Edeka), Quellbrunn (Aldi Süd), Aqua Mia (Netto), K-Classic (Kaufland), Aqua Culinaris, Aqua Vitale.
- **France:** Carrefour Source Montclar, Leclerc Marque Repère, Intermarché (all label pages HTTP 502), Aix-les-Bains, Luchon, Cristaline sources Aurèle / Sainte-Sophie / Louise / Saint-Cyr (brand pages show only a bottle image). Vittel, Contrex and Hépar have partial rows only.
- **Italy:** Acqua Panna IT (brand site prints pH 8.0 only; US report row exists), Ferrarelle (JavaScript-only site), Fiuggi, Vera (Cloudflare check), Vitasnella, Boario, Sant'Antonio, Monterosa, Cerelia, Esselunga, Coop Italia, Lete (sparkling).
- **Portugal:** Continente own label (composition loads by JavaScript), Pingo Doce own label (no numbers), Lidl PT Naturis / Saguaro, Mercadona PT, Serrana, Água do Alardo, Áqua Nova, Areeiro.

## Units notes

- **Bicarbonate vs alkalinity.** European and Brazilian labels print bicarbonate (HCO3⁻, mg/L). US water-quality reports print "Alkalinity, Total as CaCO3" and never bicarbonate; those strings are in `alkalinity_as_printed`, `bicarbonate_mg_l` is empty. Caramulo (PT) prints both. Lindoya Joia (BR) prints "Bicarbonato NaHCO3 187,360", which may be sodium-bicarbonate mass rather than HCO3⁻ (flagged in `units_notes`). No conversion has been applied anywhere.
- **Hardness.** Kept as printed in `hardness_as_printed` with its unit (Italian °F, US "as CaCO3", Portuguese "dureza total" often without a stated basis). It is not split into Ca/Mg.
- **Dry residue vs TDS.** `dry_residue_180c_mg_l` is a gravimetric residue at 180 °C (the European legal figure). `tds_mg_l` is US "TDS" or Portuguese "mineralização total" (computed sum of ions + silica). The two are not interchangeable; `units_notes` flags rows where the residue temperature is not stated (Deeside, Evian FR "résidu à sec").
- **Decimal separators.** Labels in BR/DE/FR/IT/PT print decimal commas; they are converted to decimal points, nothing else is changed. Rheinfels Quelle (DE) prints g/L and the g/L strings are kept verbatim.
- **Nitrate.** Most labels print nitrate as NO3⁻. US reports and FIJI print "Nitrate as N" / "Nitrate-N"; those rows say so in `units_notes` or keep the suffix in the cell.
- **Ranges.** Primo Brands / BlueTriton reports (Poland Spring, Deer Park, Zephyrhills, Ozarka, Ice Mountain, Arrowhead, Pure Life) print a low–high range across springs and samples; the range string is kept.

## Files

- `bottled_waters_v0.csv` — the table (187 rows, 27 columns, UTF-8, comma-separated, decimal point).
- `SOURCES.md` — every URL used or tried, grouped by market and brand, with retrieval date and provenance flag.
- `README.md` — this file.

## Licence

Label compositions are facts that bottlers are required by law to print (EU Directive 2009/54/EC, Brazil ANVISA/ANM rules, US FDA 21 CFR 165.110 and California SB 220) and are not copyrightable. This table — the selection, normalisation and provenance annotations — is our compilation and is released under CC BY 4.0 (Creative Commons Attribution 4.0). Cite as "water-aware-coffee bottled water label table v0, retrieved 2026-09-14".
