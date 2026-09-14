import numpy as np
import pandas as pd
import pytest

from water_aware_coffee.atlas.impute import fit_alkalinity, impute_alkalinity


def _wide() -> pd.DataFrame:
    rng = np.random.default_rng(0)
    hard = np.exp(rng.uniform(np.log(20), np.log(400), 300))
    alk = 0.9 * hard * np.exp(rng.normal(0, 0.1, 300))
    train = pd.DataFrame(
        {
            "source_id": "uk-stream",
            "country_iso2": "GB",
            "locality_key": [f"E{i:08d}" for i in range(300)],
            "hardness_best": hard,
            "alkalinity_median": alk,
            "source_type": rng.choice(["surface", "ground"], 300),
            "population": 1500.0,
        }
    )
    br = pd.DataFrame(
        {
            "source_id": "sisagua-br",
            "country_iso2": "BR",
            "locality_key": ["355030", "310620"],
            "hardness_best": [100.0, 40.0],
            "alkalinity_median": [np.nan, np.nan],
            "source_type": ["surface", "ground"],
            "population": [12e6, 2.5e6],
        }
    )
    return pd.concat([train, br], ignore_index=True)


def test_fit_recovers_slope_and_imputes() -> None:
    wide = _wide()
    fit = fit_alkalinity(wide)
    assert fit.n == 300
    assert fit.params["log_hardness"] == pytest.approx(1.0, abs=0.05)
    assert 0.07 < fit.resid_sd < 0.14
    out = impute_alkalinity(wide, fit)
    br = out[out["source_id"] == "sisagua-br"]
    assert br["alkalinity_imputed"].all()
    assert br.iloc[0]["alkalinity_best"] == pytest.approx(90.0, rel=0.1)
    assert (
        float(br.iloc[0]["alkalinity_low"])
        < br.iloc[0]["alkalinity_best"]
        < float(br.iloc[0]["alkalinity_high"])
    )
    gb = out[out["source_id"] == "uk-stream"]
    assert not gb["alkalinity_imputed"].any()
    assert (gb["alkalinity_best"] == gb["alkalinity_median"]).all()
