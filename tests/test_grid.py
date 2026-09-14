import numpy as np
import pytest

from water_aware_coffee.model.grid import (
    CationParams,
    Grid,
    RoastParams,
    acid_lost_fraction,
    alkalinity_meq,
    bicarbonate_protonated_fraction,
    relative_residual,
    residual_acidity,
)

LIGHT = RoastParams("light", 10.0, 8.0, 12.0, 0.20, 4.9, (70, 90), "test")


def test_protonation_fraction_at_brew_ph() -> None:
    assert bicarbonate_protonated_fraction(6.35) == pytest.approx(0.5)
    assert 0.91 < bicarbonate_protonated_fraction(5.3) < 0.93
    assert bicarbonate_protonated_fraction(4.8) > 0.97


def test_alkalinity_meq() -> None:
    assert alkalinity_meq(50.04) == pytest.approx(1.0, rel=1e-3)


def test_residual_decreases_with_alkalinity_and_is_flat_in_hardness_when_beta_zero() -> None:
    grid = Grid(alkalinity_mgl=np.array([0.0, 50.04, 100.08]), hardness_mgl=np.array([0.0, 200.0]))
    r = residual_acidity(LIGHT, grid, CationParams())
    assert r.shape == (3, 2)
    assert r[0, 0] == pytest.approx(10.0)
    f = bicarbonate_protonated_fraction(4.9)
    assert r[1, 0] == pytest.approx(10.0 - f * 1.0, rel=1e-3)
    assert np.allclose(r[:, 0], r[:, 1])


def test_positive_beta_raises_ta_with_hardness() -> None:
    grid = Grid(alkalinity_mgl=np.array([0.0]), hardness_mgl=np.array([0.0, 200.0]))
    r = residual_acidity(LIGHT, grid, CationParams(beta_central=0.05))
    assert r[0, 1] > r[0, 0]


def test_relative_residual_is_one_at_reference() -> None:
    grid = Grid(alkalinity_mgl=np.array([40.0]), hardness_mgl=np.array([68.0]))
    rel = relative_residual(LIGHT, grid, CationParams())
    assert rel[0, 0] == pytest.approx(1.0)


def test_acid_lost_fraction() -> None:
    grid = Grid(alkalinity_mgl=np.array([0.0, 250.2]), hardness_mgl=np.array([0.0, 100.0]))
    lost = acid_lost_fraction(LIGHT, grid)
    assert lost[0, 0] == 0.0
    # 250.2 mg/L CaCO3 = 5 meq/L; light roast TA 10 meq/L -> about half the acidity neutralised
    assert lost[1, 1] == pytest.approx(0.5 * bicarbonate_protonated_fraction(4.9), rel=1e-3)
