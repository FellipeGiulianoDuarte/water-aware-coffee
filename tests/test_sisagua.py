"""Tests for the SISAGUA Controle Semestral loader, on the fixture only (offline, fast).

The fixture is 246 real rows of controle_semestral_2025.csv (raw lines kept verbatim) plus the
cadastro_pontos_captacao rows for the systems they belong to. Row numbers below are the 0-based
data row index inside the fixture CSV, i.e. the number after "line:" in source_row_locator.
"""

from __future__ import annotations

import math
import shutil
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from water_aware_coffee.provenance import validate
from water_aware_coffee.sources import LOADERS, available
from water_aware_coffee.sources.sisagua import (
    LICENSE,
    LoadReport,
    load_with_report,
    parse_result_number,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "sisagua-br"
CSV = "controle_semestral_2025.csv"


def locator(line: int) -> str:
    return f"file:{CSV};line:{line}"


@pytest.fixture(scope="module")
def loaded(tmp_path_factory: pytest.TempPathFactory) -> tuple[pd.DataFrame, LoadReport]:
    # Copy so the sha256 cache that SourceFile writes next to the zips lands in tmp, not in tests/.
    raw_dir = tmp_path_factory.mktemp("raw")
    shutil.copytree(FIXTURE_DIR, raw_dir / "sisagua")
    return load_with_report(raw_dir)


@pytest.fixture(scope="module")
def df(loaded: tuple[pd.DataFrame, LoadReport]) -> pd.DataFrame:
    return loaded[0]


@pytest.fixture(scope="module")
def report(loaded: tuple[pd.DataFrame, LoadReport]) -> LoadReport:
    return loaded[1]


@pytest.fixture(scope="module")
def raw() -> pd.DataFrame:
    return pd.read_csv(
        FIXTURE_DIR / "controle_semestral_2025_csv.zip", sep=";", encoding="latin-1", dtype=str
    )


def row(df: pd.DataFrame, line: int) -> pd.Series:
    hits = df[df["source_row_locator"] == locator(line)]
    assert len(hits) == 1, f"expected exactly one emitted row for line {line}, got {len(hits)}"
    return hits.iloc[0]


def test_registered() -> None:
    assert "sisagua-br" in available()
    assert LOADERS["sisagua-br"].__module__ == "water_aware_coffee.sources.sisagua"


def test_validates_and_counts(df: pd.DataFrame, report: LoadReport) -> None:
    validate(df)
    assert report.rows_scanned == 246
    assert report.rows_by_param == {"Dureza total": 97, "Sódio": 88, "pH": 61}
    # 61 pH rows minus one empty RESULTADO (line 17) and one pH of 606 (line 21).
    assert df.groupby("quantity").size().to_dict() == {"hardness": 97, "ph": 59, "sodium": 88}
    assert report.dropped["result_missing"] == 1
    assert report.dropped["ph_outside_0_14"] == 1
    assert report.dropped["below_limit_without_numeric_limit"] == 0
    assert not df["source_row_locator"].isin([locator(17), locator(21)]).any()
    assert df["water_type"].value_counts().to_dict() == {"finished": 184, "source": 60}
    assert (df["value_type"] == "sample").all()
    assert df["n_samples"].isna().all()
    assert df["measured"].all()
    assert (df["country_iso2"] == "BR").all()


def test_provenance_constants(df: pd.DataFrame) -> None:
    assert set(df["source_id"]) == {"sisagua-br"}
    assert set(df["source_file"]) == {"controle_semestral_2025_csv.zip"}
    assert set(df["source_url"]) == {
        "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SISAGUA/"
        "controle_semestral_2025_csv.zip"
    }
    assert set(df["source_license"]) == {LICENSE}
    assert set(df["download_date"].dt.date) == {date(2026, 9, 14)}
    assert df["source_file_sha256"].str.len().eq(64).all()


def test_hand_verified_hardness_row(df: pd.DataFrame) -> None:
    # Fixture line 0: "ARARUAMA";"330020";... "SAÍDA DO TRATAMENTO";"Dureza total";"mg/L";"6,51"
    r = row(df, 0)
    assert r["quantity"] == "hardness"
    assert r["original_value"] == pytest.approx(6.51)
    assert r["conversion_factor"] == 1.0
    assert r["value"] == pytest.approx(6.51)
    assert r["unit"] == "mg/L as CaCO3"
    assert r["original_unit"] == "mg/L"
    assert r["original_parameter_name"] == "Dureza total"
    assert r["admin1"] == "RJ"
    assert r["locality"] == "ARARUAMA"
    assert r["locality_code"] == "330020"
    assert r["utility"] == "AGUAS DE JUTURNAIBA"
    assert r["utility_code"] == "S330020000001"
    assert r["water_type"] == "finished"
    assert r["period_start"] == pd.Timestamp("2025-01-02")
    assert r["period_end"] == pd.Timestamp("2025-01-02")
    assert bool(r["unit_assumed"]) is True
    assert bool(r["below_detection"]) is False
    assert r["notes"].startswith("TP_ABASTECIMENTO=SAA; SISAGUA reports Dureza total in mg/L")
    assert "assumed as CaCO3" in r["notes"]


def test_unit_assumed_only_for_hardness(df: pd.DataFrame) -> None:
    by_q = df.groupby("quantity")["unit_assumed"].agg(["all", "any"])
    assert bool(by_q.loc["hardness", "all"])
    assert not bool(by_q.loc["sodium", "any"])
    assert not bool(by_q.loc["ph", "any"])
    ph = df[df["quantity"] == "ph"]
    assert ph["original_unit"].isna().all()
    assert (ph["unit"] == "pH").all()
    assert (ph["conversion_factor"] == 1.0).all()
    assert ph["value"].between(0, 14).all()


def test_below_detection(df: pd.DataFrame, report: LoadReport) -> None:
    # Line 7: hardness MENOR_LD with LD="80,2" (LQ="264,6" must be ignored).
    ld = row(df, 7)
    assert bool(ld["below_detection"]) is True
    assert ld["value"] == pytest.approx(80.2)
    assert ld["locality"] == "VERA CRUZ DO OESTE"
    # Line 2: sodium MENOR_LQ with LQ="5" (LD="1,7" must be ignored).
    lq = row(df, 2)
    assert bool(lq["below_detection"]) is True
    assert lq["quantity"] == "sodium"
    assert lq["value"] == pytest.approx(5.0)
    assert lq["unit"] == "mg/L Na"
    assert bool(lq["unit_assumed"]) is False
    assert report.below_detection == {"MENOR_LQ": 22, "MENOR_LD": 4}
    assert int(df["below_detection"].sum()) == 26
    assert df.groupby("quantity")["below_detection"].sum().to_dict() == {
        "hardness": 17,
        "ph": 0,
        "sodium": 9,
    }


def test_number_formats(df: pd.DataFrame, report: LoadReport) -> None:
    # Line 64: hardness written with a decimal point, "8.71".
    assert row(df, 64)["value"] == pytest.approx(8.71)
    # Line 221: sodium "23.360,0000" = 23360 (entry error, emitted as is per the conventions).
    assert row(df, 221)["value"] == pytest.approx(23360.0)
    assert report.result_decimal_point_rows == 3
    assert report.result_thousands_sep_rows == 1


def test_parse_result_number() -> None:
    s = parse_result_number(pd.Series(["42,4", "162", "8.71", "23.360,0000", "MENOR_LQ", None]))
    assert s.tolist()[:4] == [42.4, 162.0, 8.71, 23360.0]
    assert math.isnan(s.iloc[4]) and math.isnan(s.iloc[5])


def test_source_type_and_coordinates(df: pd.DataFrame, raw: pd.DataFrame) -> None:
    # Own TP_CAPTACAO on intake rows wins over the cadastro join.
    capt = df[df["water_type"] == "source"]
    assert len(capt) == 60
    line = df["source_row_locator"].str.extract(r"line:(\d+)$")[0].astype(int)
    own = raw["TP_CAPTACAO"].map({"SUPERFICIAL": "surface", "SUBTERRANEO": "ground"})
    expected_own = line.map(own)
    has_own = expected_own.notna()
    assert int(has_own.sum()) == 59
    assert (df.loc[has_own, "source_type"] == expected_own[has_own]).all()
    # Line 18: intake row with empty TP_CAPTACAO -> type comes from the cadastro join.
    r18 = row(df, 18)
    assert r18["water_type"] == "source"
    assert r18["source_type"] in {"surface", "ground", "mixed"}
    # System with both surface and ground intakes in the 2025 cadastro -> mixed, centroid of 4.
    mixed = df[df["utility_code"] == "S420790000001"]
    assert len(mixed) > 0
    assert set(mixed["source_type"]) == {"mixed"}
    assert mixed["latitude"].iloc[0] == pytest.approx(-26.246008, abs=1e-5)
    assert mixed["longitude"].iloc[0] == pytest.approx(-50.797447, abs=1e-5)
    assert "centroid of 4 intake point(s)" in mixed["notes"].iloc[0]
    # System whose only 2025 cadastro coordinate is outside Brazil -> null coordinates, type kept.
    implausible = df[df["utility_code"] == "C315250000058"]
    assert len(implausible) > 0
    assert implausible["latitude"].isna().all() and implausible["longitude"].isna().all()
    assert set(implausible["source_type"]) == {"ground"}
    assert not implausible["notes"].str.contains("coordinates=").any()
    # System with no 2025 cadastro row but 2023/2024/2026 rows -> any-year fallback (9 intakes).
    fallback = df[df["utility_code"] == "C315250000038"]
    assert len(fallback) > 0
    assert set(fallback["source_type"]) == {"ground"}
    assert fallback["latitude"].iloc[0] == pytest.approx(-22.1825, abs=1e-4)
    assert "(system_any_year)" in fallback["notes"].iloc[0]
    # System absent from the cadastro -> unknown, no coordinates.
    missing = df[df["utility_code"] == "C353470000026"]
    assert len(missing) == 4
    assert set(missing["source_type"]) == {"unknown"}
    assert missing["latitude"].isna().all()
    assert df["source_type"].value_counts().to_dict() == {
        "surface": 137,
        "ground": 97,
        "mixed": 6,
        "unknown": 4,
    }
    # Every emitted coordinate is inside the Brazil bounding box.
    has = df["latitude"].notna()
    assert df.loc[has, "latitude"].between(-34, 6).all()
    assert df.loc[has, "longitude"].between(-74, -34).all()
    assert int((~has).sum()) == 12


def test_utility_fallback_and_supply_type(df: pd.DataFrame, raw: pd.DataFrame) -> None:
    # Line 245 has an empty NO_INSTITUICAO -> utility falls back to NO_SOLUCAO_ABASTECIMENTO.
    assert pd.isna(raw.loc[245, "NO_INSTITUICAO"])
    r = row(df, 245)
    assert r["utility"] == raw.loc[245, "NO_SOLUCAO_ABASTECIMENTO"]
    assert df["utility"].notna().all()
    assert int(df["notes"].str.startswith("TP_ABASTECIMENTO=SAC").sum()) == 72
    assert df["notes"].str.startswith("TP_ABASTECIMENTO=SA").all()
