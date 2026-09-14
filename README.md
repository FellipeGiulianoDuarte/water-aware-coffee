# water-aware-coffee

An open atlas of tap-water chemistry for coffee brewing, a model of how much of a coffee's acidity a given water removes,
and compensation rules with their costs. Zero budget: public datasets, published papers, label data. A prediction paper
(Quarto source in `paper/`) is being prepared for arXiv; a community validation protocol is in `docs/validation_protocol.md`.

Headline results: population-weighted, the median United States tap water neutralises 13 percent of a light roast's acidity and
16 percent of a dark roast's; about one person in ten is supplied with water above 150 mg/L alkalinity as CaCO3, where every roast
level needs compensation; alkalinity tracks hardness along one line across countries (factor-of-1.7 prediction); each 50 mg/L of
alkalinity above the SCA target costs about 3.6 sourness points on a 100-point scale.

## Contents

| Path | What |
|---|---|
| `data/processed/atlas_v0.csv` | The atlas: one row per locality (47,825), dictionary in `docs/atlas_data_dictionary.md`. CC BY 4.0. |
| `data/processed/` | Bands, matching table, dial-in rules, rankings inputs (CSV/parquet). |
| `data/external/bottled/` | 187 bottled waters with label chemistry and per-row provenance. |
| `data/external/ucdavis/` | Sensory tables transcribed from Frost et al. 2020 and Cotter et al. 2021. |
| `docs/` | Result documents per task, figures, data dictionaries, literature extractions, rankings, validation protocol. |
| `paper/` | Quarto manuscript, bibliography, generated tables and figures. |
| `src/water_aware_coffee/` | Package: units, provenance schema, source loaders, atlas aggregation, imputation, bands, model, sensory. |
| `scripts/` | Figure, table, ranking and export generators. |

## Reproduce

```bash
uv sync --all-extras
uv run pytest
# raw data: download with the scripts referenced in docs/ (or fetch the release assets into data/raw/), then
uv run wac build --all      # validated measurement tables -> data/interim/
uv run wac atlas            # per-locality atlas, population, alkalinity imputation -> data/processed/
uv run wac bands            # alkalinity bands and matching table
uv run python scripts/figures.py && uv run python scripts/figures.py --paper
uv run python scripts/paper_tables.py && uv run python scripts/rankings.py && uv run python scripts/export_atlas.py
uv run wac dialin --alkalinity 150 --roast light
quarto render paper/paper.qmd
```

Python 3.12 (`.python-version`), `uv` for the environment, Quarto (`uv tool install quarto-cli`) and TinyTeX for the PDF.

## Data sources and licences

Brazil SISAGUA (CC BY), TapWaterData (CC BY 4.0), EPA Six-Year Review 4 (public domain), the English water-industry open-data hub
(CC BY 4.0), Northern Ireland Water via OpenDataNI (OGL v3), IBGE and ONS population (open), bottled-water labels (facts; this compilation
CC BY 4.0). Per-file URLs, checksums and download dates are recorded in the loaders and in the release assets' manifests. UK water
company web lookups under all-rights-reserved terms were not used.

## Licences

Code: MIT (`LICENSE`). Produced data: CC BY 4.0 (`data/LICENSE`). Cite as: Duarte, F. G. (2026). Tap water alkalinity and coffee
acidity: a population-weighted atlas and a prediction model for filter brewing. Preprint; repository https://github.com/FellipeGiulianoDuarte/water-aware-coffee.

## Contributing a brew session

See `docs/validation_protocol.md` and open an issue with the "Brew session" template.
