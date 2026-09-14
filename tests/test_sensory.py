import pytest

from water_aware_coffee.model.params import DARK, LIGHT
from water_aware_coffee.model.sensory import AdditiveSensory, dial_in


@pytest.fixture(scope="module")
def sens() -> AdditiveSensory:
    return AdditiveSensory.from_frost_csv()


def test_additive_reproduces_marginal_means(sens: AdditiveSensory) -> None:
    # In a balanced design the roast marginal mean equals the average of the additive
    # predictions over all TDS and PE levels.
    import numpy as np

    from water_aware_coffee.model.sensory import PE_LEVELS, TDS_LEVELS

    def marginal(attr: str, roast: str) -> float:
        return float(
            np.mean([sens.predict(attr, roast, t, p) for t in TDS_LEVELS for p in PE_LEVELS])
        )

    assert marginal("Sourness", "light") == pytest.approx(37.4, abs=0.1)  # printed to 0.1
    assert marginal("Bitterness", "dark") == pytest.approx(44.6, abs=0.1)
    # and the TDS marginal at 1.5 percent likewise
    m = float(
        np.mean(
            [
                sens.predict("Sourness", r, 1.5, p)
                for r in ("light", "medium", "dark")
                for p in PE_LEVELS
            ]
        )
    )
    assert m == pytest.approx(37.2, abs=0.1)


def test_slopes_have_expected_signs(sens: AdditiveSensory) -> None:
    assert sens.slope_per_tds("Sourness") > 15  # 26.5 -> 37.2 over 0.5 percent TDS
    assert sens.slope_per_pe("Sourness") < 0
    assert sens.slope_per_tds("Bitterness") > 0
    assert sens.slope_per_pe("Bitterness") > 0


def test_dial_in_directions(sens: AdditiveSensory) -> None:
    d = dial_in(150.0, LIGHT, sens)
    assert d.acid_neutralised_meq > 2.0
    assert d.sourness_change_points < -7
    assert d.tds_delta_percent > 0.15
    assert d.side_effects_tds_route["Bitterness"] > 0  # more strength, more bitter
    assert d.pe_delta_percent < 0  # lower extraction to regain sourness
    assert d.side_effects_pe_route["Bitterness"] < 0
    ref = dial_in(40.0, DARK, sens)
    assert abs(ref.acid_neutralised_meq) < 1e-9
    soft = dial_in(10.0, DARK, sens)
    assert soft.tds_delta_percent < 0
