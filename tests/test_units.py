import math

import pytest

from water_aware_coffee import units as u
from water_aware_coffee.units import Quantity, UnknownUnitError, convert


def approx(x: float, rel: float = 1e-3) -> object:
    return pytest.approx(x, rel=rel)


# Reference values from definitions (not from this module) so the derivation is checked.
def test_degree_definitions() -> None:
    assert u.DH_TO_MGL_CACO3 == approx(17.85)  # 1 °dH = 17.85 mg/L CaCO3
    assert u.FH_TO_MGL_CACO3 == 10.0
    assert u.CLARKE_TO_MGL_CACO3 == approx(14.25)
    assert u.GPG_TO_MGL_CACO3 == approx(17.12)


def test_ion_to_caco3_factors() -> None:
    assert u.CA_TO_CACO3 == approx(2.497)
    assert u.MG_TO_CACO3 == approx(4.118)
    assert u.HCO3_TO_CACO3 == approx(0.820)
    assert u.EQ_CACO3 == approx(50.04)


@pytest.mark.parametrize(
    ("unit", "expected"),
    [
        ("mg/L as CaCO3", 100.0),
        ("mg/L CaCO3", 100.0),
        ("ppm", 100.0),
        ("°dH", 100 * 17.848),
        ("dH", 100 * 17.848),
        ("°fH", 1000.0),
        ("°e", 100 * 14.254),
        ("Clarke", 100 * 14.254),
        ("gpg", 100 * 17.118),
        ("grains per gallon", 100 * 17.118),
        ("mmol/L", 100 * 2 * 50.043),
        ("meq/L", 100 * 50.043),
        ("mg/L Ca", 100 * 2.4973),
    ],
)
def test_hardness_conversions(unit: str, expected: float) -> None:
    assert convert(100.0, Quantity.HARDNESS, unit) == approx(expected)


@pytest.mark.parametrize(
    ("unit", "expected"),
    [
        ("mg/L as CaCO3", 50.0),
        ("meq/L", 50 * 50.043),
        ("mmol/L", 50 * 50.043),
        ("mg/L HCO3", 50 * 0.8202),
    ],
)
def test_alkalinity_conversions(unit: str, expected: float) -> None:
    assert convert(50.0, Quantity.ALKALINITY, unit) == approx(expected)


def test_ion_conversions() -> None:
    assert convert(1.0, Quantity.CALCIUM, "mmol/L") == approx(40.078)
    assert convert(1.0, Quantity.MAGNESIUM, "mmol/L") == approx(24.305)
    assert convert(1.0, Quantity.SODIUM, "mmol/L") == approx(22.99)
    assert convert(1.0, Quantity.BICARBONATE, "mmol/L") == approx(61.016)
    # round trip: Ca as CaCO3 -> Ca
    assert convert(2.497, Quantity.CALCIUM, "mg/L as CaCO3") == approx(1.0)


def test_hardness_from_ions_matches_textbook() -> None:
    # 40 mg/L Ca + 12 mg/L Mg ~ 99.9 + 49.4 = 149.3 mg/L as CaCO3
    assert u.hardness_from_ions(40.0, 12.0) == approx(149.3)


def test_alkalinity_from_bicarbonate() -> None:
    assert u.alkalinity_from_bicarbonate(61.016) == approx(50.043)


def test_ph_unitless() -> None:
    assert convert(7.2, Quantity.PH, None) == 7.2
    assert convert(7.2, Quantity.PH, "std units") == 7.2
    with pytest.raises(UnknownUnitError):
        convert(7.2, Quantity.PH, "mg/L")


def test_unknown_unit_raises() -> None:
    with pytest.raises(UnknownUnitError):
        convert(1.0, Quantity.HARDNESS, "furlongs")
    with pytest.raises(UnknownUnitError):
        convert(1.0, Quantity.SODIUM, "°dH")


def test_ambiguous_flag() -> None:
    assert u.is_ambiguous("mg/L")
    assert u.is_ambiguous(" PPM ")
    assert not u.is_ambiguous("mg/L as CaCO3")
    assert not u.is_ambiguous("°dH")


def test_normalize_unit_string_variants() -> None:
    assert u.normalize_unit_string("Mg / L  CaCO₃") == "mg/l as caco3"
    assert u.normalize_unit_string("MG/L AS CACO3") == "mg/l as caco3"
    assert u.normalize_unit_string("German degrees") == "°dh"
    assert u.normalize_unit_string("grains/gallon") == "gpg"
    assert u.normalize_unit_string(None) == ""


def test_no_nan_factors() -> None:
    for q in Quantity:
        if q is Quantity.PH:
            continue
        for unit in ("mg/L",):
            assert not math.isnan(u.conversion_factor(q, unit))
