import numpy as np
import pandas as pd

from water_aware_coffee.atlas.bands import (
    BAND_NAMES,
    assign_band,
    band_frame,
    band_matching,
    band_summary,
    edge_acid_loss,
    softened_flag,
)


def test_assign_band_edges() -> None:
    alk = pd.Series([0.0, 39.9, 40.0, 79.9, 80.0, 149.9, 150.0, 249.9, 250.0, 900.0])
    assert assign_band(alk).tolist() == [1, 1, 2, 2, 3, 3, 4, 4, 5, 5]


def test_softened_flag() -> None:
    assert softened_flag(
        pd.Series([150.0, 150.0, 20.0]), pd.Series([10.0, 100.0, 10.0])
    ).tolist() == [
        True,
        False,
        False,
    ]


def test_edge_acid_loss_monotonic() -> None:
    e = edge_acid_loss()
    assert e.iloc[:, 1].is_monotonic_increasing
    assert 0.05 < e.iloc[0, 1] < 0.07  # 40 mg/L on a light roast: about 6 percent


def test_summary_and_matching_on_synthetic() -> None:
    rng = np.random.default_rng(2)
    n = 300
    wide = pd.DataFrame(
        {
            "source_id": "uk-stream",
            "country_iso2": "GB",
            "admin1": "England",
            "locality_key": [f"E{i:08d}" for i in range(n)],
            "locality": [f"Area {i}" for i in range(n)],
            "alkalinity_best": rng.uniform(5, 400, n),
            "hardness_best": rng.uniform(5, 400, n),
            "alkalinity_imputed": False,
            "population": 1500.0,
        }
    )
    d = band_frame(wide)
    assert set(d["band"]) == {1, 2, 3, 4, 5}
    s = band_summary(d)
    assert len(s) == 5 and list(s["name"]) == list(BAND_NAMES)
    assert abs(s["population_share"].sum() - 1.0) < 1e-9
    m = band_matching(s)
    assert len(m) == 15
    light = m[m.roast == "light"].set_index("band")["relative_residual_at_median"]
    assert light.is_monotonic_decreasing
    assert m[(m.band == 5) & (m.roast == "light")]["label_at_median"].iloc[0] != "works"
