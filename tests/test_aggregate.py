import pandas as pd
import pytest

from water_aware_coffee.atlas.aggregate import summarise_long, to_wide
from water_aware_coffee.provenance import COLUMNS
from water_aware_coffee.units import CA_TO_CACO3, MG_TO_CACO3


def _row(
    quantity: str, value: float, locality_code: str = "Z1", water_type: str = "finished"
) -> dict:
    base = {c: None for c in COLUMNS}
    base.update(
        source_id="t",
        country_iso2="GB",
        admin1="X",
        locality="Zone 1",
        locality_code=locality_code,
        utility="U",
        water_type=water_type,
        source_type="unknown",
        quantity=quantity,
        value=value,
        unit="x",
        value_type="sample",
        measured=True,
        below_detection=False,
        unit_assumed=quantity == "hardness",
        period_start=pd.Timestamp("2025-01-01"),
        period_end=pd.Timestamp("2025-01-01"),
    )
    return base


def test_summary_and_wide_derive_hardness() -> None:
    rows = [
        _row("calcium", 40.0),
        _row("calcium", 44.0),
        _row("magnesium", 10.0),
        _row("hardness", 50.0),
        _row("alkalinity", 100.0),
        _row("alkalinity", 999.0, water_type="source"),  # excluded
    ]
    df = pd.DataFrame(rows, columns=COLUMNS)
    long = summarise_long(df)
    assert set(long["quantity"]) == {"calcium", "magnesium", "hardness", "alkalinity"}
    alk = long[long["quantity"] == "alkalinity"].iloc[0]
    assert alk["n"] == 1 and alk["median"] == 100.0
    wide = to_wide(long)
    assert len(wide) == 1
    w = wide.iloc[0]
    assert w["calcium_median"] == 42.0
    assert w["hardness_from_ions"] == pytest.approx(42.0 * CA_TO_CACO3 + 10.0 * MG_TO_CACO3)
    assert w["hardness_best_basis"] == "from_ions"
    assert w["hardness_median"] == 50.0
    assert w["hardness_share_unit_assumed"] == 1.0
