"""Tests for the UK Stream loader, run on the fixture excerpts under tests/fixtures/uk-stream.

The fixture mirrors the raw layout (<raw_dir>/uk/stream/<company>/*.csv) and holds real rows
copied verbatim (header, BOM and encoding kept) from the three company files.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd
import pytest

from water_aware_coffee.provenance import validate
from water_aware_coffee.sources.uk_stream import (
    LoadStats,
    load,
    load_with_stats,
    parse_sample_dates,
)
from water_aware_coffee.units import CA_TO_CACO3

FIXTURES = Path(__file__).parent / "fixtures" / "uk-stream"
WESSEX_FILE = "Wessex_Water_Domestic_Water_Quality_2022_2024_view_-6387738141497925089.csv"
SOUTHERN_FILE = "Southern_Water_Drinking_Water_Quality_2018_2022_part1.csv"
YORKSHIRE_FILE = "Yorkshire Water Drinking Water Quality 2024_-4876658227378681787.csv"


@pytest.fixture(scope="module")
def loaded() -> tuple[pd.DataFrame, LoadStats]:
    return load_with_stats(FIXTURES)


def test_registered_loader_validates(loaded: tuple[pd.DataFrame, LoadStats]) -> None:
    df = load(FIXTURES)
    validate(df)
    assert len(df) == len(loaded[0]) == 234
    assert set(df["source_id"]) == {"uk-stream"}
    assert set(df["country_iso2"]) == {"GB"}
    assert set(df["admin1"]) == {"England"}
    assert set(df["water_type"]) == {"finished"}
    assert set(df["value_type"]) == {"sample"}
    assert df["period_start"].notna().all()
    assert (df["period_start"] == df["period_end"]).all()


def test_row_counts_per_utility_and_quantity(loaded: tuple[pd.DataFrame, LoadStats]) -> None:
    df, _ = loaded
    counts = df.groupby(["utility", "quantity"]).size().to_dict()
    assert counts == {
        ("Southern Water", "alkalinity"): 16,
        ("Southern Water", "calcium"): 14,
        ("Southern Water", "hardness"): 14,
        ("Southern Water", "magnesium"): 12,
        ("Southern Water", "ph"): 12,
        ("Southern Water", "sodium"): 11,
        ("Wessex Water", "alkalinity"): 22,
        ("Wessex Water", "hardness"): 23,
        ("Wessex Water", "ph"): 20,
        ("Wessex Water", "sodium"): 25,
        ("Yorkshire Water", "hardness"): 23,
        ("Yorkshire Water", "ph"): 22,
        ("Yorkshire Water", "sodium"): 20,
    }


def test_skipped_and_dropped_rows_are_counted(loaded: tuple[pd.DataFrame, LoadStats]) -> None:
    _, stats = loaded
    assert stats.files_read == [WESSEX_FILE, SOUTHERN_FILE, YORKSHIRE_FILE]
    assert stats.files_skipped_stale == []
    assert stats.files_generic_url == []
    assert stats.skipped_determinands == {
        "ALKALINITY (BICARBONATE)": 4,
        "HARDNESS (?DH)": 4,
        "HARDNESS (°DH)": 4,
    }
    assert not stats.unmapped_units
    # Two Yorkshire "Hardness total" rows have an empty Result: dropped and counted.
    assert stats.non_numeric_results[YORKSHIRE_FILE] == 2
    assert sum(stats.unparsable_dates.values()) == 0
    assert stats.above_limit_rows == 0
    assert sum(stats.ph_out_of_range.values()) == 0
    assert stats.wessex_ug_sodium_relabelled == 10
    # One Yorkshire hardness row has the literal LSOA "null": dropped and counted.
    assert stats.missing_lsoa[YORKSHIRE_FILE] == 1
    assert stats.rows_read == 262 and stats.rows_emitted == 234


def test_localities_are_lsoa_codes(loaded: tuple[pd.DataFrame, LoadStats]) -> None:
    df, stats = loaded
    assert df["locality"].str.match(r"^[EW]\d{8}$").all()
    assert (df["locality"] == df["locality_code"]).all()
    assert stats.lsoa_not_a_code == 0
    assert df["utility_code"].isna().all()


def test_provenance_per_company(loaded: tuple[pd.DataFrame, LoadStats]) -> None:
    df, _ = loaded
    urls = {u: set(g["source_url"]) for u, g in df.groupby("utility")}
    licenses = {u: set(g["source_license"]) for u, g in df.groupby("utility")}
    items = "https://www.streamwaterdata.co.uk/api/download/v1/items/{}/csv?layers=0"
    assert urls == {
        "Wessex Water": {items.format("9d9900db3b5d484e84e2319fd1c6ca54")},
        "Southern Water": {items.format("1677bec2d846429a9a2224fcb205c1b1")},
        "Yorkshire Water": {items.format("6fff0eef81cf466f8363be7153d85f57")},
    }
    assert licenses == {
        "Wessex Water": {
            "Wessex Water Domestic Water Quality © 2025 by Wessex Water is licensed under CC BY 4.0"
        },
        "Southern Water": {"CC BY 4.0"},
        "Yorkshire Water": {
            "Yorkshire Water Drinking Water Quality 2024 © 2024 by Yorkshire Water "
            "is licensed under CC BY 4.0"
        },
    }
    assert df["source_file_sha256"].str.len().eq(64).all()


def test_wessex_units_and_flags(loaded: tuple[pd.DataFrame, LoadStats]) -> None:
    df, _ = loaded
    w = df[df["utility"] == "Wessex Water"]
    # "mg CaCO3/L" states the basis: no assumption, factor 1.
    hard = w[w["quantity"] == "hardness"]
    assert set(hard["original_unit"]) == {"mg CaCO3/L"}
    assert not hard["unit_assumed"].any()
    assert (hard["conversion_factor"] == 1.0).all()
    assert set(w.loc[w["quantity"] == "alkalinity", "original_unit"]) == {"mg CaCO3/L"}
    assert not w.loc[w["quantity"] == "alkalinity", "unit_assumed"].any()
    # pH: unit string passed through, factor 1, never "assumed".
    assert set(w.loc[w["quantity"] == "ph", "original_unit"]) == {"pH Value"}
    assert not w.loc[w["quantity"] == "ph", "unit_assumed"].any()
    # Sodium: 15 properly labelled rows, 10 mislabelled "μg/l Na" rows kept as mg/L and flagged.
    na = w[w["quantity"] == "sodium"]
    assert na["original_unit"].value_counts().to_dict() == {"mg/L Na": 15, "μg/l Na": 10}
    ug = na[na["original_unit"] == "μg/l Na"]
    assert ug["unit_assumed"].all() and (ug["conversion_factor"] == 1.0).all()
    assert ug["notes"].str.contains("mislabelled").all()
    assert not na.loc[na["original_unit"] == "mg/L Na", "unit_assumed"].any()
    # Hand check: OBJECTID 5788 reads 69 "μg/l Na" -> 69 mg/L Na.
    row = ug[ug["source_row_locator"].str.endswith(";OBJECTID=5788")].iloc[0]
    assert row["original_value"] == 69.0 and row["value"] == 69.0
    assert row["source_row_locator"] == (
        f"{WESSEX_FILE}:Sample_Id=0724ffd9-ecd4-42ef-88e4-a7b46ff89548;OBJECTID=5788"
    )
    # Below-detection rows: two alkalinity and two hardness rows carry Operator "<".
    assert w[w["below_detection"]].groupby("quantity").size().to_dict() == {
        "alkalinity": 2,
        "hardness": 2,
    }
    # One real outlier (5,656 mg/L as CaCO3) is kept, not filtered here.
    assert hard["value"].max() == 5656.0


def test_southern_assumptions_and_hardness_conversion(
    loaded: tuple[pd.DataFrame, LoadStats],
) -> None:
    df, _ = loaded
    s = df[df["utility"] == "Southern Water"]
    # Units column is empty: every concentration is an assumption and says so.
    ions = s[s["quantity"].isin(["calcium", "magnesium", "sodium"])]
    assert ions["unit_assumed"].all()
    assert ions["original_unit"].isna().all()
    assert (ions["conversion_factor"] == 1.0).all()
    assert set(ions["notes"]) == {"Southern Water Stream file has empty Units; mg/L assumed"}
    alk = s[s["quantity"] == "alkalinity"]
    assert alk["unit_assumed"].all() and (alk["conversion_factor"] == 1.0).all()
    assert alk["notes"].str.contains("assumed as CaCO3").all()
    ph = s[s["quantity"] == "ph"]
    assert not ph["unit_assumed"].any() and ph["original_unit"].isna().all()
    # Hardness: reported as mg/L calcium, converted to as CaCO3 (x 2.497) and flagged.
    hard = s[s["quantity"] == "hardness"]
    assert set(hard["original_unit"]) == {"mg/L Ca"}
    assert hard["unit_assumed"].all()
    assert hard["conversion_factor"].map(lambda f: abs(f - CA_TO_CACO3) < 1e-12).all()
    assert hard["notes"].str.contains("mg/L calcium").all()
    # Hand check: ObjectId 491950, HARDNESS (TOTAL) 116 -> 116 * 100.086 / 40.078 = 289.68.
    row = hard[hard["source_row_locator"] == f"{SOUTHERN_FILE}:ObjectId=491950"].iloc[0]
    assert row["original_value"] == 116.0
    assert row["value"] == pytest.approx(289.68, abs=0.01)
    assert row["unit"] == "mg/L as CaCO3"
    # Operator "<": below detection, value kept as the limit.
    below = s[s["below_detection"]]
    assert below.groupby("quantity").size().to_dict() == {
        "alkalinity": 2,
        "calcium": 2,
        "hardness": 2,
        "magnesium": 2,
        "sodium": 1,
    }
    assert (below.loc[below["quantity"] == "hardness", "original_value"] == 0.7).all()
    # Redundant determinands are not emitted.
    assert not s["original_parameter_name"].str.contains("BICARBONATE|DH").any()


def test_yorkshire_hardness_basis_flagged(loaded: tuple[pd.DataFrame, LoadStats]) -> None:
    df, _ = loaded
    y = df[df["utility"] == "Yorkshire Water"]
    hard = y[y["quantity"] == "hardness"]
    assert set(hard["original_unit"]) == {"mg/l"}
    assert hard["unit_assumed"].all()  # bare mg/l: base flags it, loader adds the reason
    assert (hard["conversion_factor"] == 1.0).all()
    assert hard["notes"].str.contains("basis unstated").all()
    assert set(y.loc[y["quantity"] == "sodium", "original_unit"]) == {"mg/l Na"}
    assert not y.loc[y["quantity"] == "sodium", "unit_assumed"].any()
    assert set(y.loc[y["quantity"] == "ph", "original_unit"]) == {"pH value"}
    # The 'n' operator used by Yorkshire means "none", not below detection.
    below = y[y["below_detection"]]
    assert len(below) == 1
    row = below.iloc[0]
    assert row["quantity"] == "hardness"
    assert row["original_value"] == pytest.approx(2.19757155)
    assert row["period_start"] == pd.Timestamp("2024-04-15")  # from "4/15/2024 12:00:00 AM"
    assert row["source_row_locator"] == (
        f"{YORKSHIRE_FILE}:Sample_Id=e953e2fb192653345ef1b18410313e48;OBJECTID=58808"
    )


def test_parse_sample_dates_covers_every_shape() -> None:
    s = pd.Series(
        [
            "2022-02-21",
            "2016/01/04",
            "1/29/2025 12:00:00 AM",
            "2026/02/25 00:00:00",
            "2026/02/12 00:00:00+00",
            "07/10/2022",
            "not a date",
            None,
        ]
    )
    out = parse_sample_dates(s)
    assert out.tolist()[:6] == [
        pd.Timestamp("2022-02-21"),
        pd.Timestamp("2016-01-04"),
        pd.Timestamp("2025-01-29"),
        pd.Timestamp("2026-02-25"),
        pd.Timestamp("2026-02-12"),
        pd.Timestamp("2022-10-07"),  # bare dd/mm/yyyy is read day-first
    ]
    assert out.isna().tolist()[6:] == [True, True]


def test_stale_hub_csv_is_skipped_when_paged_export_exists(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    shutil.copytree(FIXTURES, raw)
    folder = raw / "uk" / "stream" / "yorkshire-water"
    src = folder / YORKSHIRE_FILE
    hub = folder / "Yorkshire_Water_Drinking_Water_Quality_2026.csv"
    paged = (
        folder / "Yorkshire_Water_Drinking_Water_Quality_2026.featureserver_paged_2026-09-14.csv"
    )
    shutil.copy(src, hub)
    shutil.copy(src, paged)
    df, stats = load_with_stats(raw)
    assert stats.files_skipped_stale == [hub.name]
    assert paged.name in stats.files_read and hub.name not in stats.files_read
    y = df[df["utility"] == "Yorkshire Water"]
    assert y["source_file"].value_counts().to_dict() == {YORKSHIRE_FILE: 65, paged.name: 65}
    # The 2026 file maps to the 2026 item id.
    assert set(y.loc[y["source_file"] == paged.name, "source_url"]) == {
        "https://www.streamwaterdata.co.uk/api/download/v1/items/"
        "a71a93148df04e579fb5694e59cee61e/csv?layers=0"
    }


def test_missing_company_folder_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load(tmp_path)
