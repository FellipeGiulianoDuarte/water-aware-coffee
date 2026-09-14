import pandas as pd
import pandera.errors
import pytest

from water_aware_coffee import provenance as prov
from water_aware_coffee.units import TARGET_UNIT, Quantity, convert


def _row(**over: object) -> dict[str, object]:
    base: dict[str, object] = {
        "source_id": "test",
        "source_url": "https://example.org/x.csv",
        "source_file": "x.csv",
        "source_file_sha256": "0" * 64,
        "download_date": "2026-09-14",
        "source_row_locator": "row:1",
        "source_license": "CC BY 4.0",
        "country_iso2": "BR",
        "admin1": "SP",
        "locality": "São Paulo",
        "locality_code": "3550308",
        "utility": "SABESP",
        "utility_code": None,
        "latitude": -23.55,
        "longitude": -46.63,
        "water_type": "finished",
        "source_type": "surface",
        "softened": False,
        "period_start": "2025-01-01",
        "period_end": "2025-06-30",
        "quantity": "hardness",
        "value": convert(5.0, Quantity.HARDNESS, "°dH"),
        "unit": TARGET_UNIT[Quantity.HARDNESS],
        "value_type": "mean",
        "n_samples": 12,
        "measured": True,
        "below_detection": False,
        "original_parameter_name": "Dureza total",
        "original_value": 5.0,
        "original_unit": "°dH",
        "conversion_factor": convert(1.0, Quantity.HARDNESS, "°dH"),
        "unit_assumed": False,
        "notes": None,
    }
    base.update(over)
    return base


def test_valid_row_passes() -> None:
    df = pd.DataFrame([_row()])
    out = prov.validate(df)
    assert len(out) == 1
    assert list(out.columns) == prov.COLUMNS


def test_value_must_match_conversion() -> None:
    df = pd.DataFrame([_row(value=999.0)])
    with pytest.raises(pandera.errors.SchemaErrors):
        prov.validate(df)


def test_unknown_column_rejected() -> None:
    df = pd.DataFrame([_row(extra="x")])
    with pytest.raises(pandera.errors.SchemaErrors):
        prov.validate(df)


def test_bad_quantity_rejected() -> None:
    df = pd.DataFrame([_row(quantity="taste")])
    with pytest.raises(pandera.errors.SchemaErrors):
        prov.validate(df)


def test_period_order_enforced() -> None:
    df = pd.DataFrame([_row(period_start="2025-12-31", period_end="2025-01-01")])
    with pytest.raises(pandera.errors.SchemaErrors):
        prov.validate(df)


def test_ph_range_enforced() -> None:
    df = pd.DataFrame(
        [
            _row(
                quantity="ph",
                unit="pH",
                original_parameter_name="pH",
                original_value=15.0,
                original_unit=None,
                conversion_factor=1.0,
                value=15.0,
            )
        ]
    )
    with pytest.raises(pandera.errors.SchemaErrors):
        prov.validate(df)


def test_negative_concentration_rejected() -> None:
    df = pd.DataFrame(
        [_row(original_value=-1.0, value=-1.0 * convert(1.0, Quantity.HARDNESS, "°dH"))]
    )
    with pytest.raises(pandera.errors.SchemaErrors):
        prov.validate(df)
