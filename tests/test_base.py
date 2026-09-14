from pathlib import Path

from water_aware_coffee.provenance import COLUMNS
from water_aware_coffee.sources.base import MeasurementBuilder, SourceFile, parse_decimal_comma
from water_aware_coffee.units import Quantity


def test_builder_roundtrip(tmp_path: Path) -> None:
    f = tmp_path / "x.csv"
    f.write_text("a;b\n1;2\n")
    src = SourceFile.from_path("test", f, "https://example.org", "CC BY")
    assert len(src.sha256) == 64
    b = MeasurementBuilder(src)
    b.add(
        quantity=Quantity.HARDNESS,
        original_value=5.0,
        original_unit="°dH",
        original_parameter_name="Härte",
        locator="row:0",
        country_iso2="DE",
        locality="Berlin",
        water_type="finished",
        source_type="unknown",
        value_type="mean",
    )
    b.add(
        quantity=Quantity.HARDNESS,
        original_value=100.0,
        original_unit="mg/L",
        original_parameter_name="Dureza total",
        locator="row:1",
        country_iso2="BR",
        locality="Campinas",
        water_type="finished",
        source_type="unknown",
        value_type="sample",
    )
    df = b.frame()
    assert list(df.columns) == COLUMNS
    assert df.loc[0, "value"] > 89 and df.loc[0, "unit"] == "mg/L as CaCO3"
    assert not bool(df.loc[0, "unit_assumed"])
    assert bool(df.loc[1, "unit_assumed"])


def test_parse_decimal_comma() -> None:
    import pandas as pd

    s = parse_decimal_comma(pd.Series(["42,4", "162", "MENOR_LQ", "1.234,5"]))
    assert s.tolist()[:2] == [42.4, 162.0]
    assert s.isna().tolist()[2]
    assert s.tolist()[3] == 1234.5
