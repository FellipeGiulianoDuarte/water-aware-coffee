"""One loader per data source. Each exposes `load(raw_dir: Path) -> pd.DataFrame` returning a table
that passes `water_aware_coffee.provenance.validate`.

Register new loaders in LOADERS. Keys are the source ids used in docs/sources.md.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pandas as pd

Loader = Callable[[Path], pd.DataFrame]

LOADERS: dict[str, Loader] = {}


def register(source_id: str) -> Callable[[Loader], Loader]:
    def deco(fn: Loader) -> Loader:
        LOADERS[source_id] = fn
        return fn

    return deco


def available() -> list[str]:
    # Import modules for their registration side effect.
    from water_aware_coffee.sources import (  # noqa: F401
        epa_syr4,
        ni_water,
        sisagua,
        tapwaterdata,
        uk_stream,
    )

    return sorted(LOADERS)
