# water-aware-coffee

A tap-water chemistry atlas for coffee brewing, a mechanistic model of which roast levels work with
which water, and quantified dial-in rules. Zero budget: public datasets, published papers, volunteer brews.

Project brief, status and decision log live in the parent folder (`../overview.md`, `../status.md`,
`../decisions.md`); this repository holds code, data pipeline, tests and, later, the paper source.

## Setup

```bash
uv sync --all-extras
uv run pytest
```

Python 3.12 is pinned in `.python-version`; `uv` downloads it if missing.

## Layout

| Path | Contents |
|---|---|
| `src/water_aware_coffee/` | Package. `units.py` (conversions), `provenance.py` (per-row schema), `sources/` (one loader per data source), `cli.py`. |
| `scripts/` | Download scripts, one per source. Write into `data/raw/`. |
| `data/raw/` | Raw downloads, gitignored. Regenerate with `scripts/`. Frozen copies attached to GitHub Releases. |
| `data/interim/` | Normalized per-source tables, gitignored. |
| `data/processed/` | The atlas and other small derived outputs. Committed. CC BY 4.0 (`data/LICENSE`). |
| `docs/` | Data dictionary, method notes. |
| `notebooks/` | Exploration only. Nothing here is a source of truth. |
| `tests/` | pytest. Unit conversions and schemas are tested. |

## Licenses

Code: MIT (`LICENSE`). Produced datasets: CC BY 4.0 (`data/LICENSE`). Upstream sources keep their own terms.
