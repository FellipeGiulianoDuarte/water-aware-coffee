"""Tests for the EPA SYR4 alkalinity / pH loader, on the fixture zip only.

Fixture: tests/fixtures/epa-syr4-us/us/epa_syr/syr4_dbp_related-parameters.zip with the same two
member names as the real archive ("SYR4_DBP_Related Parameters/TOTAL ALKALINITY.TXT" and
".../PH.txt"), 200 real rows each: FN/EP, FN/DS, blank code + EP/DS, RW/RW, RW code with DS point,
FN code with RW point, rows with no usable water type, below-detection rows with and without a
usable limit, one negative alkalinity, three pH values above 14, one 9,102 mg/L alkalinity,
purchased / GU source-water codes, a cp1252 en dash in a system name, and STATE_CODE != PWSID
prefix.
"""

from pathlib import Path

import pandas as pd
import pytest

from water_aware_coffee.provenance import COLUMNS, validate
from water_aware_coffee.sources import LOADERS
from water_aware_coffee.sources.epa_syr4 import ALKALINITY_NOTE, SOURCE_ID, load

FIXTURE_RAW_DIR = Path(__file__).parent / "fixtures" / "epa-syr4-us"


@pytest.fixture(scope="module")
def df() -> pd.DataFrame:
    return load(FIXTURE_RAW_DIR)


@pytest.fixture(scope="module")
def alk(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["quantity"] == "alkalinity"]


@pytest.fixture(scope="module")
def ph(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["quantity"] == "ph"]


def test_registered() -> None:
    assert LOADERS[SOURCE_ID] is load


def test_row_counts(df: pd.DataFrame) -> None:
    assert list(df.columns) == COLUMNS
    assert len(df) == 363
    assert df.groupby(["quantity", "water_type"]).size().to_dict() == {
        ("alkalinity", "finished"): 126,
        ("alkalinity", "source"): 58,
        ("ph", "finished"): 138,
        ("ph", "source"): 41,
    }
    # 400 raw rows: 20 have no usable water type, 13 are below detection without a usable limit,
    # 1 is a negative alkalinity, 3 are pH values above 14.
    assert 400 - len(df) == 20 + 13 + 1 + 3
    assert (df["source_file"] == "syr4_dbp_related-parameters.zip").all()
    assert (df["country_iso2"] == "US").all()
    assert df["admin1"].notna().all()


def test_validate_passes(df: pd.DataFrame) -> None:
    validate(df)


def test_hand_verified_alkalinity_row(alk: pd.DataFrame) -> None:
    # Raw: PWSID AK2271999 "BETHEL-CITY S/D WATER", STATE_CODE AK, SOURCE_WATER_TYPE GW,
    # SAMPLING_POINT_TYPE EP, SOURCE_TYPE_CODE blank, 27-DEC-18, VALUE 104, UNIT MG/L,
    # population 1650.
    r = alk[(alk["utility_code"] == "AK2271999") & (alk["value"] == 104.0)].iloc[0]
    assert r["unit"] == "mg/L as CaCO3"
    assert r["original_value"] == 104.0
    assert r["original_unit"] == "MG/L"
    assert r["conversion_factor"] == 1.0
    assert bool(r["unit_assumed"]) is True
    assert r["original_parameter_name"] == "ALKALINITY, TOTAL"
    assert r["admin1"] == "AK"
    assert r["locality"] == "BETHEL-CITY S/D WATER"
    assert r["utility"] == "BETHEL-CITY S/D WATER"
    assert r["water_type"] == "finished"
    assert r["source_type"] == "ground"
    assert r["value_type"] == "sample"
    assert bool(r["measured"]) is True
    assert bool(r["below_detection"]) is False
    assert r["period_start"] == pd.Timestamp("2018-12-27")
    assert r["period_end"] == pd.Timestamp("2018-12-27")
    assert r["notes"] == (
        ALKALINITY_NOTE
        + "; population=1650; sampling_point=EP; source_type_code=; source_water_type=GW"
    )
    assert r["source_row_locator"].startswith("file:TOTAL ALKALINITY.TXT;line:")


def test_hand_verified_ph_row(ph: pd.DataFrame) -> None:
    r = ph[ph["utility_code"] == "AK2271999"].iloc[0]
    assert r["value"] == 7.5
    assert r["unit"] == "pH"
    assert pd.isna(r["original_unit"])
    assert r["conversion_factor"] == 1.0
    assert bool(r["unit_assumed"]) is False
    assert r["original_parameter_name"] == "PH"
    assert (
        r["notes"] == "population=1650; sampling_point=EP; source_type_code=; source_water_type=GW"
    )
    assert r["source_row_locator"].startswith("file:PH.txt;line:")


def test_unit_flags(alk: pd.DataFrame, ph: pd.DataFrame) -> None:
    assert alk["unit_assumed"].all()
    assert (alk["original_unit"] == "MG/L").all()
    assert (alk["conversion_factor"] == 1.0).all()
    assert alk["notes"].str.startswith(ALKALINITY_NOTE).all()
    assert not ph["unit_assumed"].any()
    assert ph["original_unit"].isna().all()


def test_below_detection(alk: pd.DataFrame, ph: pd.DataFrame) -> None:
    assert int(alk["below_detection"].sum()) == 8
    assert int(ph["below_detection"].sum()) == 7
    # DETECT 0, VALUE blank, DETECTION_LIMIT_VALUE 5 MG/L (MRL) -> value = 5, flagged.
    r = alk[(alk["utility_code"] == "AL0000035") & alk["below_detection"]].iloc[0]
    assert r["value"] == 5.0 and r["original_value"] == 5.0
    assert r["notes"].endswith("; below_detection_limit_code=MRL")
    assert (alk.loc[alk["below_detection"], "value"] > 0).all()
    assert ph.loc[ph["below_detection"], "value"].between(0, 14).all()
    assert not alk.loc[~alk["below_detection"], "notes"].str.contains("below_detection").any()


def test_water_type_and_source_type(df: pd.DataFrame) -> None:
    src = df[df["water_type"] == "source"]
    assert src["notes"].str.contains("sampling_point=RW|source_type_code=RW").all()
    fin = df[df["water_type"] == "finished"]
    assert not fin["notes"].str.contains("sampling_point=RW|source_type_code=RW").any()
    assert (
        fin["notes"].str.contains("source_type_code=FN|sampling_point=EP|sampling_point=DS").all()
    )
    assert df.groupby("quantity")["source_type"].value_counts().to_dict() == {
        ("alkalinity", "ground"): 98,
        ("alkalinity", "surface"): 86,
        ("ph", "ground"): 107,
        ("ph", "surface"): 72,
    }
    swp = df[df["notes"].str.contains("source_water_type=SWP")]
    assert len(swp) > 0 and (swp["source_type"] == "surface").all()
    gu = df[df["notes"].str.contains("source_water_type=GU\\b")]
    assert len(gu) > 0 and (gu["source_type"] == "ground").all()


def test_schema_incompatible_rows_dropped_but_outliers_kept(
    alk: pd.DataFrame, ph: pd.DataFrame
) -> None:
    assert (alk["value"] >= 0).all()  # the one negative alkalinity row is dropped
    assert alk["value"].max() == 9102.0  # obvious entry errors stay (rule 9)
    assert ph["value"].between(0, 14).all()  # pH > 14 rows are dropped
    assert ph["value"].max() == 9.9


def test_text_encoding_and_provenance(df: pd.DataFrame) -> None:
    assert "RIDGEFIELD LITTLE LEAGUE – JENSEN FIELD" in set(df["locality"])
    assert (df["download_date"] == pd.Timestamp("2026-09-14")).all()
    assert (df["source_license"] == "US federal government work, public domain").all()
    assert df["source_url"].iloc[0].endswith("/syr4_dbp_related-parameters.zip")
    assert (df["period_start"] == df["period_end"]).all()
    assert df["period_start"].between("2012-01-01", "2019-12-31").all()
    # PWSIDs are 9 characters; tribal systems run by EPA regions start with digits ("083090062",
    # Region 8) and their state comes from STATE_CODE, not from the PWSID prefix.
    assert df["utility_code"].str.fullmatch(r"[A-Z0-9]{9}").all()
    tribal = df[df["utility_code"].str.startswith("0")]
    assert set(tribal["utility_code"]) == {"083090062", "063503111", "083090050", "083090067"}
    assert set(tribal["admin1"]) == {"MT", "NM"}
