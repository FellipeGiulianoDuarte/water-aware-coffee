"""Tests for the TapWaterData US hardness loader, on the 200-row fixture only.

Fixture: tests/fixtures/tapwaterdata-us/us/tapwaterdata/water-hardness.csv, a real excerpt of the
raw file (original '#' header block kept) with 69 T1, 37 T2 and 94 T3 rows, including Delaware and
Utah alphanumeric PWSIDs, a "PWSID null" row, rows whose utility name contains '#', 32 disputed rows
and 28 rows without coordinates.
"""

from pathlib import Path

import pandas as pd
import pytest

from water_aware_coffee.provenance import COLUMNS, validate
from water_aware_coffee.sources import LOADERS
from water_aware_coffee.sources.tapwaterdata import SOURCE_ID, load

FIXTURE_RAW_DIR = Path(__file__).parent / "fixtures" / "tapwaterdata-us"


@pytest.fixture(scope="module")
def df() -> pd.DataFrame:
    return load(FIXTURE_RAW_DIR)


def test_registered() -> None:
    assert LOADERS[SOURCE_ID] is load


def test_row_counts(df: pd.DataFrame) -> None:
    assert list(df.columns) == COLUMNS
    assert df.groupby("quantity").size().to_dict() == {"hardness": 200}
    tier = df["notes"].str.extract(r"tier=(T\d)")[0]
    assert tier.value_counts().to_dict() == {"T3": 94, "T1": 69, "T2": 37}
    assert df["locality_code"].nunique() == 200  # slug is the unique key
    assert df["locality"].nunique() == 198  # two city names occur in two states each
    assert (df["source_file"] == "water-hardness.csv").all()
    assert (df["country_iso2"] == "US").all()


def test_validate_passes(df: pd.DataFrame) -> None:
    validate(df)


def test_tiers_map_to_water_type_measured_and_value_type(df: pd.DataFrame) -> None:
    assert df["water_type"].value_counts().to_dict() == {"finished": 106, "unknown": 94}
    assert df["value_type"].value_counts().to_dict() == {"typical": 106, "median": 94}
    assert int((~df["measured"]).sum()) == 94
    t3 = df[df["notes"].str.startswith("tier=T3")]
    assert not t3["measured"].any()
    assert t3["n_samples"].notna().all()
    assert (t3["n_samples"] >= 1).all()
    assert df[~df["notes"].str.startswith("tier=T3")]["n_samples"].isna().all()
    assert (df["source_type"] == "unknown").all()


def test_hand_verified_t1_row(df: pd.DataFrame) -> None:
    # Raw row: al/abbeville, hardness_mg_l 127, tier T1, sourceDate 2022-05-17, disputed true,
    # range 90.8-127, source "Utility-reported water quality data — ABBEVILLE WATER WORKS & SEWER
    # BOARD (PWSID AL0000657)"
    r = df[df["locality_code"] == "al/abbeville"].iloc[0]
    assert r["value"] == 127.0
    assert r["unit"] == "mg/L as CaCO3"
    assert r["original_value"] == 127.0
    assert r["original_unit"] == "mg/L as CaCO3"
    assert r["conversion_factor"] == 1.0
    assert r["original_parameter_name"] == "hardness_mg_l"
    assert r["admin1"] == "AL"
    assert r["locality"] == "Abbeville"
    assert r["utility"] == "ABBEVILLE WATER WORKS & SEWER BOARD"
    assert r["utility_code"] == "AL0000657"
    assert r["water_type"] == "finished"
    assert r["value_type"] == "typical"
    assert bool(r["measured"]) is True
    assert pd.isna(r["period_start"])
    assert r["period_end"] == pd.Timestamp("2022-05-17")
    assert r["notes"] == "tier=T1; category=hard; disputed=True; range=90.8-127"
    assert r["source_row_locator"] == "file:water-hardness.csv;line:42;slug:al/abbeville"


def test_hand_verified_t3_row(df: pd.DataFrame) -> None:
    # Raw row: ak/anchor-point, 27.4 mg/L, T3, 152 samples, category soft, not disputed.
    r = df[df["locality_code"] == "ak/anchor-point"].iloc[0]
    assert r["value"] == 27.4
    assert r["water_type"] == "unknown"
    assert r["value_type"] == "median"
    assert r["n_samples"] == 152.0
    assert bool(r["measured"]) is False
    assert pd.isna(r["utility"]) and pd.isna(r["utility_code"])
    assert r["notes"] == "tier=T3; category=soft; disputed=False; range=na-na"


def test_pwsid_and_utility_parsing(df: pd.DataFrame) -> None:
    t1 = df[df["notes"].str.startswith("tier=T1")]
    assert int(t1["utility_code"].notna().sum()) == 67
    assert int(t1["utility"].notna().sum()) == 68
    # Alphanumeric PWSIDs (Delaware, Utah) are real EPA ids and must be kept.
    assert df.loc[df["locality_code"] == "de/georgetown", "utility_code"].iloc[0] == "DE00A0757"
    assert df.loc[df["locality_code"] == "de/georgetown", "utility"].iloc[0] == (
        "WILLOW LAKE PUMP DISTRICT"
    )
    assert t1["utility_code"].dropna().str.fullmatch(r"[A-Z]{2}[A-Z0-9]{7}").all()
    # "(PWSID null)" gives a utility name but no code.
    thornton = df[df["locality_code"] == "il/thornton"].iloc[0]
    assert thornton["utility"] == "THORNTON WATER SYSTEM" and pd.isna(thornton["utility_code"])
    # T2 and T3 rows never carry a utility.
    other = df[~df["notes"].str.startswith("tier=T1")]
    assert other["utility"].isna().all() and other["utility_code"].isna().all()


def test_hash_in_data_rows_is_not_treated_as_comment(df: pd.DataFrame) -> None:
    # 3 fixture rows contain '#' inside the source text; a comment='#' read would truncate them.
    assert "OID-OAKDALE RURAL WATER SYSTEM #1" in set(df["utility"].dropna())
    assert df["utility"].fillna("").str.contains("#").sum() == 3


def test_flags_and_provenance(df: pd.DataFrame) -> None:
    assert not df["unit_assumed"].any()
    assert not df["below_detection"].any()
    assert int(df["latitude"].isna().sum()) == 28
    assert df["latitude"].isna().eq(df["longitude"].isna()).all()
    assert int(df["notes"].str.contains("disputed=True").sum()) == 32
    assert (df["download_date"] == pd.Timestamp("2026-09-14")).all()
    assert (df["source_url"] == "https://www.tapwaterdata.com/data/water-hardness.csv").all()
    assert df["source_license"].iloc[0].startswith("CC BY 4.0")
    assert df["source_file_sha256"].str.len().eq(64).all()
