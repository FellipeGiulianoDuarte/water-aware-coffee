from pathlib import Path

from water_aware_coffee.sources.bottled import load
from water_aware_coffee.units import HCO3_TO_CACO3

FIX = Path(__file__).parent / "fixtures" / "bottled-labels" / "raw"


def test_bottled_loader_on_fixture() -> None:
    df = load(FIX)
    assert (df["water_type"] == "bottled").all()
    assert (df["value_type"] == "declared").all()
    q = df.groupby("quantity").size().to_dict()
    assert q["calcium"] >= 10 and q["alkalinity"] >= 8 and q["ph"] >= 8
    # first product: Aguaí Fonte da Mata, bicarbonate 41.06 -> alkalinity as CaCO3
    a = df[
        (df["quantity"] == "alkalinity")
        & df["locality"].str.startswith("Aguaí | Aguaí Água Mineral Natural (Fonte da Mata)")
    ]
    assert abs(float(a["value"].iloc[0]) - 41.06 * HCO3_TO_CACO3) < 1e-6
    assert not bool(a["unit_assumed"].iloc[0])
    assert df["notes"].str.contains("provenance=").all()
