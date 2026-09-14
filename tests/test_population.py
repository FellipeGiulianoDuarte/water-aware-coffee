"""Official population loader (IBGE SIDRA JSON, ONS LSOA xlsx) and the atlas join."""

from pathlib import Path

import pandas as pd
import pytest

from water_aware_coffee.atlas.population import (
    IBGE_SOURCE,
    ONS_SOURCE,
    POPULATION_COLUMNS,
    attach_population,
    load_ibge,
    load_ons,
    load_population,
)

FIXTURES = Path(__file__).parent / "fixtures" / "population"


def test_load_ibge_truncates_to_six_digit_code() -> None:
    pop = load_ibge(FIXTURES / "ibge" / "sidra_t4709_v93_n6_p2022.json")
    assert list(pop.columns) == POPULATION_COLUMNS
    assert len(pop) == 4
    assert (pop["country_iso2"] == "BR").all()
    assert pop["locality_code"].str.len().eq(6).all()
    sp = pop.set_index("locality_code").loc["355030"]  # São Paulo, 7-digit code 3550308
    assert sp["population"] == 11_451_999
    assert sp["population_source"] == IBGE_SOURCE
    assert sp["population_year"] == 2022
    assert pop.set_index("locality_code").loc["330455", "population"] == 6_211_223  # Rio


def test_load_ons_uses_latest_mid_year_sheet() -> None:
    pop = load_ons(FIXTURES / "ons" / "sapelsoasyoa20222024.xlsx")
    assert list(pop.columns) == POPULATION_COLUMNS
    assert len(pop) == 4
    assert (pop["country_iso2"] == "GB").all()
    assert (pop["population_year"] == 2024).all()
    assert (pop["population_source"] == ONS_SOURCE).all()
    by_code = pop.set_index("locality_code")["population"]
    assert by_code["E01011949"] == 1898  # mid-2024 value, not the mid-2022 1876
    assert by_code["W01001941"] == 1550


def test_load_population_concatenates_both_sources() -> None:
    pop = load_population(FIXTURES)
    assert len(pop) == 8
    assert pop["country_iso2"].value_counts().to_dict() == {"BR": 4, "GB": 4}
    assert str(pop["population"].dtype) == "Int64"
    assert not pop.duplicated(["country_iso2", "locality_code"]).any()


def test_load_population_skips_missing_subdir(tmp_path: Path) -> None:
    (tmp_path / "ibge").mkdir()
    src = FIXTURES / "ibge" / "sidra_t4709_v93_n6_p2022.json"
    (tmp_path / "ibge" / src.name).write_bytes(src.read_bytes())
    pop = load_population(tmp_path)
    assert set(pop["country_iso2"]) == {"BR"}


def test_load_population_raises_when_nothing_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_population(tmp_path)


def test_attach_population_fills_nulls_only() -> None:
    pop = load_population(FIXTURES)
    wide = pd.DataFrame(
        {
            "source_id": ["epa-syr4-us", "sisagua-br", "uk-stream", "uk-stream", "uk-ni-water"],
            "country_iso2": ["US", "BR", "GB", "GB", "GB"],
            "admin1": ["TX", "SP", "ENG", "ENG", "NIR"],
            "locality_key": ["TX0570004", "355030", "E01011949", "E01999999", "ZN0104"],
            "population": pd.array([123_456, None, None, None, None], dtype="Int64"),
            "hardness_best": [100.0, 50.0, 200.0, 210.0, 130.0],
        }
    )
    out = attach_population(wide, pop)
    assert len(out) == len(wide)
    assert list(out.columns[: len(wide.columns)]) == list(wide.columns)
    got = out.set_index("locality_key")
    # Existing US value untouched, attributed to the measurement source.
    assert got.loc["TX0570004", "population"] == 123_456
    assert got.loc["TX0570004", "population_source"] == "epa-syr4-us"
    assert pd.isna(got.loc["TX0570004", "population_year"])
    # BR and GB filled from the official datasets.
    assert got.loc["355030", "population"] == 11_451_999
    assert got.loc["355030", "population_source"] == IBGE_SOURCE
    assert got.loc["355030", "population_year"] == 2022
    assert got.loc["E01011949", "population"] == 1898
    assert got.loc["E01011949", "population_source"] == ONS_SOURCE
    assert got.loc["E01011949", "population_year"] == 2024
    # Unknown LSOA and NI zones stay null.
    assert pd.isna(got.loc["E01999999", "population"])
    assert pd.isna(got.loc["E01999999", "population_source"])
    assert pd.isna(got.loc["ZN0104", "population"])
    assert str(out["population"].dtype) == "Int64"
    # Input not mutated.
    assert wide["population"].isna().sum() == 4
    assert "population_source" not in wide.columns


def test_attach_population_does_not_cross_countries() -> None:
    pop = load_population(FIXTURES)
    wide = pd.DataFrame(
        {
            "source_id": ["x"],
            "country_iso2": ["GB"],
            "admin1": ["ENG"],
            "locality_key": ["355030"],  # a BR code under a GB row must not match
            "population": pd.array([None], dtype="Int64"),
        }
    )
    out = attach_population(wide, pop)
    assert pd.isna(out.loc[0, "population"])
