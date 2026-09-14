import numpy as np
import pandas as pd

from water_aware_coffee.atlas.regimes import (
    clustering_frame,
    fit_regimes,
    label_rule,
    matching_table,
    regime_summary,
)


def _wide() -> pd.DataFrame:
    rng = np.random.default_rng(1)
    n = 400
    soft = pd.DataFrame(
        {
            "alk": np.exp(rng.normal(np.log(30), 0.2, n)),
            "hard": np.exp(rng.normal(np.log(50), 0.2, n)),
        }
    )
    hard = pd.DataFrame(
        {
            "alk": np.exp(rng.normal(np.log(220), 0.15, n)),
            "hard": np.exp(rng.normal(np.log(280), 0.15, n)),
        }
    )
    d = pd.concat([soft, hard], ignore_index=True)
    return pd.DataFrame(
        {
            "source_id": "uk-stream",
            "country_iso2": "GB",
            "admin1": "England",
            "locality_key": [f"E{i:08d}" for i in range(len(d))],
            "locality": [f"Area {i}" for i in range(len(d))],
            "alkalinity_best": d["alk"],
            "hardness_best": d["hard"],
            "alkalinity_imputed": False,
            "population": 1500.0,
        }
    )


def test_two_clear_regimes_are_found() -> None:
    d = clustering_frame(_wide())
    model, labels = fit_regimes(d, k_max=4)
    assert model.k == 2
    assert set(labels) == {1, 2}
    # regime 1 is the low-alkalinity one
    assert d.loc[labels == 1, "alk"].median() < d.loc[labels == 2, "alk"].median()
    summary = regime_summary(d, labels, model)
    assert abs(summary["population_share"].sum() - 1.0) < 1e-9
    match = matching_table(summary)
    assert len(match) == 6
    light_soft = match[(match.regime == 1) & (match.roast == "light")].iloc[0]
    light_hard = match[(match.regime == 2) & (match.roast == "light")].iloc[0]
    assert light_soft["relative_residual_central"] > light_hard["relative_residual_central"]
    assert light_hard["label"].startswith("fights") or light_hard["label"].startswith("compensate")


def test_label_rule_boundaries() -> None:
    assert label_rule(1.0) == "works"
    assert label_rule(0.75) == "works"
    assert label_rule(0.6) == "compensate (flatter)"
    assert label_rule(0.4) == "fights (too flat)"
    assert label_rule(1.4) == "compensate (sharper)"
    assert label_rule(1.6) == "too sharp"
