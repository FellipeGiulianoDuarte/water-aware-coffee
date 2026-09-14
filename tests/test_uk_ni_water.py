"""Tests for the uk-ni-water loader, on the fixture excerpt only (offline, fast)."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from water_aware_coffee.provenance import COLUMNS, validate
from water_aware_coffee.sources.ni_water import RESOURCE_URLS, _parse_result, load
from water_aware_coffee.units import CA_TO_CACO3

FIXTURE_RAW = Path(__file__).parent / "fixtures" / "uk-ni-water"


@pytest.fixture(scope="module")
def df() -> pd.DataFrame:
    return load(FIXTURE_RAW)


def test_row_counts_per_quantity(df: pd.DataFrame) -> None:
    # The fixture holds 160 raw rows: 138 for our five parameters (all "Customer Tap"),
    # 8 "Customer Tap" Conductivity rows and 14 "Supply Point" rows of other parameters.
    assert len(df) == 138
    assert df.groupby("quantity").size().to_dict() == {
        "calcium": 28,
        "hardness": 28,
        "magnesium": 28,
        "ph": 26,
        "sodium": 28,
    }
    assert df.groupby("quantity")["locality"].nunique().to_dict() == {
        "calcium": 4,
        "hardness": 4,
        "magnesium": 4,
        "ph": 3,
        "sodium": 4,
    }


def test_schema_and_constants(df: pd.DataFrame) -> None:
    assert list(df.columns) == COLUMNS
    validate(df)
    assert set(df["source_id"]) == {"uk-ni-water"}
    assert set(df["source_url"]) == {
        RESOURCE_URLS["2025-ni-water-customer-tap-supply-point-results.csv"]
    }
    assert set(df["source_license"]) == {"UK Open Government Licence (OGL) v3"}
    assert set(df["country_iso2"]) == {"GB"}
    assert set(df["admin1"]) == {"Northern Ireland"}
    assert set(df["utility"]) == {"Northern Ireland Water"}
    assert set(df["water_type"]) == {"finished"}
    assert set(df["source_type"]) == {"unknown"}
    assert set(df["value_type"]) == {"sample"}
    assert df["n_samples"].isna().all()
    assert df["measured"].all()
    assert (df["period_start"] == df["period_end"]).all()


def test_hand_verified_sample(df: pd.DataFrame) -> None:
    # Raw line: 2025,Customer Tap,ZN0104,Ballinrees North,ZN0104AE-25-5020692,07/01/2025 10:33,
    #           BT52 2BS,Total hardness,,51,51,mg/l   (and Calcium 36, Magnesium 8.8, Sodium 18,
    #           Hydrogen Ion 7.4 for the same sample id)
    s = df[df["source_row_locator"] == "ZN0104AE-25-5020692"].set_index("quantity")
    assert len(s) == 5
    assert s.loc["hardness", "original_value"] == 51.0
    assert s.loc["hardness", "original_unit"] == "mg/l"
    assert s.loc["hardness", "conversion_factor"] == pytest.approx(CA_TO_CACO3)
    # 51 mg/l as Ca * (100.086 / 40.078) = 127.36 mg/L as CaCO3
    assert s.loc["hardness", "value"] == pytest.approx(127.36, abs=0.01)
    assert s.loc["hardness", "unit"] == "mg/L as CaCO3"
    assert s.loc["calcium", "value"] == 36.0
    assert s.loc["calcium", "unit"] == "mg/L Ca"
    assert s.loc["magnesium", "value"] == pytest.approx(8.8)
    assert s.loc["sodium", "value"] == 18.0
    assert s.loc["sodium", "original_unit"] == "mg Na/l"
    assert s.loc["ph", "value"] == pytest.approx(7.4)
    assert s.loc["ph", "original_unit"] == "pH value"
    assert (s["locality"] == "Ballinrees North").all()
    assert (s["locality_code"] == "ZN0104").all()
    assert (s["period_start"] == pd.Timestamp("2025-01-07 10:33")).all()
    assert s["notes"].str.startswith("postcode=BT52 2BS").all()
    assert sorted(s["original_parameter_name"]) == [
        "Calcium",
        "Hydrogen Ion",
        "Magnesium",
        "Sodium",
        "Total hardness",
    ]


def test_unit_flags(df: pd.DataFrame) -> None:
    hardness = df["quantity"] == "hardness"
    assert df.loc[hardness, "unit_assumed"].all()
    assert np.allclose(df.loc[hardness, "conversion_factor"], CA_TO_CACO3)
    assert df.loc[hardness, "notes"].str.contains("hardness as mg/l Ca, not as CaCO3").all()
    assert not df.loc[~hardness, "unit_assumed"].any()
    assert (df.loc[~hardness, "conversion_factor"] == 1.0).all()


def test_below_detection_flags(df: pd.DataFrame) -> None:
    # None of the five parameters is below detection in the 2025 file (the fixture's "<0.011"
    # rows are 2,4-D supply-point rows, which are not loaded). Check the parser directly.
    assert not df["below_detection"].any()
    raw = pd.DataFrame(
        {
            "Result": ["<0.011", "7.4", "n/a", ">5", "<"],
            "Report Value": ["0", "7.4", "12", "0", "0"],
        }
    )
    value, below = _parse_result(raw)
    # "<0.011": below detection, value = the limit (not the "Report Value" 0).
    # "n/a": falls back to "Report Value". ">5" and a bare "<": no usable value -> NaN (dropped).
    assert value.tolist()[:3] == [0.011, 7.4, 12.0]
    assert value.isna().tolist() == [False, False, False, True, True]
    assert below.tolist() == [True, False, False, False, False]


def test_postcode_zone_cross_check(df: pd.DataFrame) -> None:
    # BT51 3LH is sampled under zone ZN0105 but the lookup maps it to ZN0104 in 2025.
    n = df[df["notes"].str.contains("postcode=BT51 3LH", na=False)]
    assert len(n) > 0
    assert (n["locality_code"] == "ZN0105").all()
    assert n["notes"].str.contains("gives zone ZN0104 for this postcode in 2025").all()
    # BT52 2BS was left out of the lookup excerpt on purpose.
    m = df[df["notes"].str.contains("postcode=BT52 2BS", na=False)]
    assert len(m) == 5
    assert m["notes"].str.contains("postcode not in postcode-v-zone-lookup-by-year.csv").all()
    # Postcodes found in the lookup with a matching zone carry neither note.
    ok = df[~df["notes"].str.contains("BT51 3LH|BT44 9EG|BT52 2BS", na=False)]
    assert not ok["notes"].str.contains("gives zone|not in", na=False).any()


def test_missing_lookup_still_loads(tmp_path: Path) -> None:
    folder = tmp_path / "uk" / "ni-water"
    folder.mkdir(parents=True)
    name = "2025-ni-water-customer-tap-supply-point-results.csv"
    (folder / name).write_bytes((FIXTURE_RAW / "uk" / "ni-water" / name).read_bytes())
    out = load(tmp_path)
    assert len(out) == 138
    assert not out["notes"].str.contains("lookup", na=False).any()
