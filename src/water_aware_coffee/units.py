"""Unit normalization for water chemistry.

Everything in the atlas is stored in ONE unit per quantity:

- hardness, calcium hardness, magnesium hardness, alkalinity: mg/L as CaCO3
- calcium, magnesium, sodium, bicarbonate (as ion mass): mg/L of the ion
- pH: unitless

Every conversion factor is derived here from molar masses and definitions, not copied from
tables, so the derivation can be audited. Sources for definitions:

- German degree (°dH): 10 mg/L CaO.
- French degree (°fH): 10 mg/L CaCO3.
- English / Clarke degree (°e): 1 grain of CaCO3 per imperial gallon.
- US grains per gallon (gpg): 1 grain of CaCO3 per US gallon.
- ppm is treated as mg/L (dilute aqueous solution, density 1 kg/L).
- 1 meq/L of a divalent-ion hardness or of alkalinity = 50.04 mg/L as CaCO3
  (equivalent weight of CaCO3).
- 1 mmol/L of Ca2+ or Mg2+ = 2 meq/L (divalent). 1 mmol/L HCO3- = 1 meq/L (monovalent).
"""

from __future__ import annotations

from enum import StrEnum

# Molar masses, g/mol (IUPAC 2021 conventional values, rounded to 3 decimals).
M_CA = 40.078
M_MG = 24.305
M_NA = 22.990
M_C = 12.011
M_O = 15.999
M_H = 1.008
M_CACO3 = M_CA + M_C + 3 * M_O  # 100.086
M_CAO = M_CA + M_O  # 56.077
M_HCO3 = M_H + M_C + 3 * M_O  # 61.016

# Equivalent weight of CaCO3 (divalent): g per equivalent.
EQ_CACO3 = M_CACO3 / 2  # 50.043

# Grain and gallons.
GRAIN_MG = 64.79891
US_GALLON_L = 3.785411784
IMPERIAL_GALLON_L = 4.54609

# Hardness degrees expressed in mg/L as CaCO3.
DH_TO_MGL_CACO3 = 10.0 * M_CACO3 / M_CAO  # 17.848
FH_TO_MGL_CACO3 = 10.0
CLARKE_TO_MGL_CACO3 = GRAIN_MG / IMPERIAL_GALLON_L  # 14.254
GPG_TO_MGL_CACO3 = GRAIN_MG / US_GALLON_L  # 17.118

# Ion mass to "as CaCO3".
CA_TO_CACO3 = M_CACO3 / M_CA  # 2.497
MG_TO_CACO3 = M_CACO3 / M_MG  # 4.118
HCO3_TO_CACO3 = EQ_CACO3 / M_HCO3  # 0.820 (HCO3- is monovalent: 1 mg -> 1/61.016 meq)


class Quantity(StrEnum):
    """What is being measured. Determines the target unit and valid source units."""

    HARDNESS = "hardness"  # total hardness (Ca + Mg), target mg/L as CaCO3
    CALCIUM = "calcium"  # target mg/L Ca
    MAGNESIUM = "magnesium"  # target mg/L Mg
    ALKALINITY = "alkalinity"  # target mg/L as CaCO3
    BICARBONATE = "bicarbonate"  # target mg/L HCO3-
    SODIUM = "sodium"  # target mg/L Na
    PH = "ph"  # unitless


TARGET_UNIT: dict[Quantity, str] = {
    Quantity.HARDNESS: "mg/L as CaCO3",
    Quantity.CALCIUM: "mg/L Ca",
    Quantity.MAGNESIUM: "mg/L Mg",
    Quantity.ALKALINITY: "mg/L as CaCO3",
    Quantity.BICARBONATE: "mg/L HCO3",
    Quantity.SODIUM: "mg/L Na",
    Quantity.PH: "pH",
}


class UnknownUnitError(ValueError):
    """Raised when a unit string is not recognized for the given quantity."""


# Canonical unit tokens, after normalize_unit_string().
# Factor multiplies the source value to give the target unit for that quantity.
_HARDNESS_FACTORS: dict[str, float] = {
    "mg/l as caco3": 1.0,
    "mg/l caco3": 1.0,
    "mg caco3/l": 1.0,
    "mgcaco3/l": 1.0,
    "ppm caco3": 1.0,
    "ppm as caco3": 1.0,
    "mg/l": 1.0,  # bare mg/L for hardness is assumed to be as CaCO3 (flagged by caller)
    "ppm": 1.0,
    "mmol/l": 2.0 * EQ_CACO3,  # 1 mmol/L divalent = 2 meq/L
    "meq/l": EQ_CACO3,
    "dh": DH_TO_MGL_CACO3,
    "odh": DH_TO_MGL_CACO3,
    "°dh": DH_TO_MGL_CACO3,
    "fh": FH_TO_MGL_CACO3,
    "°fh": FH_TO_MGL_CACO3,
    "of": FH_TO_MGL_CACO3,
    "°f": FH_TO_MGL_CACO3,
    "clarke": CLARKE_TO_MGL_CACO3,
    "°e": CLARKE_TO_MGL_CACO3,
    "oe": CLARKE_TO_MGL_CACO3,
    "°clarke": CLARKE_TO_MGL_CACO3,
    "gpg": GPG_TO_MGL_CACO3,
    "grains/gal": GPG_TO_MGL_CACO3,
    "grains per gallon": GPG_TO_MGL_CACO3,
    "mg/l ca": CA_TO_CACO3,  # hardness reported as calcium mass
    "mg/l as ca": CA_TO_CACO3,
    "ppm ca": CA_TO_CACO3,
}

_ALKALINITY_FACTORS: dict[str, float] = {
    "mg/l as caco3": 1.0,
    "mg/l caco3": 1.0,
    "mg caco3/l": 1.0,
    "mgcaco3/l": 1.0,
    "ppm caco3": 1.0,
    "ppm as caco3": 1.0,
    "mg/l": 1.0,  # bare mg/L for alkalinity assumed as CaCO3 (flagged by caller)
    "ppm": 1.0,
    "meq/l": EQ_CACO3,
    "mmol/l": EQ_CACO3,  # 1 mmol/L HCO3- = 1 meq/L
    "mg/l hco3": HCO3_TO_CACO3,
    "mg/l as hco3": HCO3_TO_CACO3,
    "mg hco3/l": HCO3_TO_CACO3,
    "mghco3/l": HCO3_TO_CACO3,
    "ppm hco3": HCO3_TO_CACO3,
    "°dh": DH_TO_MGL_CACO3,  # "Karbonathärte" in German data
    "dh": DH_TO_MGL_CACO3,
    "°fh": FH_TO_MGL_CACO3,
    "fh": FH_TO_MGL_CACO3,
}

_ION_FACTORS: dict[Quantity, dict[str, float]] = {
    Quantity.CALCIUM: {
        "mg/l": 1.0,
        "ppm": 1.0,
        "mg/l ca": 1.0,
        "mg ca/l": 1.0,
        "mgca/l": 1.0,
        "mmol/l": M_CA,
        "meq/l": M_CA / 2,
        "mg/l as caco3": 1.0 / CA_TO_CACO3,
        "mg/l caco3": 1.0 / CA_TO_CACO3,
    },
    Quantity.MAGNESIUM: {
        "mg/l": 1.0,
        "ppm": 1.0,
        "mg/l mg": 1.0,
        "mg mg/l": 1.0,
        "mgmg/l": 1.0,
        "mmol/l": M_MG,
        "meq/l": M_MG / 2,
        "mg/l as caco3": 1.0 / MG_TO_CACO3,
        "mg/l caco3": 1.0 / MG_TO_CACO3,
    },
    Quantity.SODIUM: {
        "mg/l": 1.0,
        "ppm": 1.0,
        "mg/l na": 1.0,
        "mg na/l": 1.0,
        "mgna/l": 1.0,
        "mmol/l": M_NA,
        "meq/l": M_NA,
    },
    Quantity.BICARBONATE: {
        "mg/l": 1.0,
        "ppm": 1.0,
        "mg/l hco3": 1.0,
        "mmol/l": M_HCO3,
        "meq/l": M_HCO3,
        "mg/l as caco3": 1.0 / HCO3_TO_CACO3,
        "mg/l caco3": 1.0 / HCO3_TO_CACO3,
    },
}

_PH_UNITS = {
    "",
    "ph",
    "ph value",
    "ph values",
    "ph unit",
    "ph units",
    "ph_unit",
    "unitless",
    "std units",
    "standard units",
    "su",
    "none",
    "-",
}

# Units whose meaning depends on an assumption we cannot check from the string alone.
AMBIGUOUS_UNITS = {"mg/l", "ppm"}


def normalize_unit_string(unit: str | None) -> str:
    """Lower-case, strip, collapse whitespace, unify common spellings."""
    if unit is None:
        return ""
    u = " ".join(unit.strip().lower().split())
    u = (
        u.replace("mg / l", "mg/l")
        .replace("mg/ l", "mg/l")
        .replace("mg /l", "mg/l")
        .replace("milligrams per liter", "mg/l")
        .replace("milligrams per litre", "mg/l")
        .replace("mg l-1", "mg/l")
        .replace("mg.l-1", "mg/l")
        .replace("mgl", "mg/l")
        .replace("caco₃", "caco3")
        .replace("hco₃", "hco3")
        .replace("as caco3", "as caco3")
        .replace("mg/l caco3", "mg/l as caco3")
        .replace("ppm caco3", "ppm as caco3")
        .replace("mmol / l", "mmol/l")
        .replace("meq / l", "meq/l")
        .replace("° dh", "°dh")
        .replace("° fh", "°fh")
        .replace("° e", "°e")
        .replace("deg dh", "°dh")
        .replace("deg fh", "°fh")
        .replace("german degrees", "°dh")
        .replace("french degrees", "°fh")
        .replace("english degrees", "°e")
        .replace("degrees clarke", "clarke")
        .replace("grains per gallon", "gpg")
        .replace("grains/gallon", "gpg")
        .replace("gr/gal", "gpg")
    )
    return u


def conversion_factor(quantity: Quantity, unit: str | None) -> float:
    """Multiplier from `unit` to the target unit of `quantity`.

    Raises UnknownUnitError for unrecognized units. pH accepts only unitless labels and returns 1.0.
    """
    u = normalize_unit_string(unit)
    if quantity is Quantity.PH:
        if u in _PH_UNITS:
            return 1.0
        raise UnknownUnitError(f"pH is unitless; got {unit!r}")
    table: dict[str, float]
    if quantity is Quantity.HARDNESS:
        table = _HARDNESS_FACTORS
    elif quantity is Quantity.ALKALINITY:
        table = _ALKALINITY_FACTORS
    else:
        table = _ION_FACTORS[quantity]
    try:
        return table[u]
    except KeyError as exc:
        raise UnknownUnitError(f"unknown unit {unit!r} for {quantity.value}") from exc


def is_ambiguous(unit: str | None) -> bool:
    """True when the unit string does not say what the mg/L is 'as' (e.g. bare 'mg/L' hardness)."""
    return normalize_unit_string(unit) in AMBIGUOUS_UNITS


def convert(value: float, quantity: Quantity, unit: str | None) -> float:
    """Convert `value` from `unit` to the target unit of `quantity`."""
    return value * conversion_factor(quantity, unit)


def hardness_from_ions(calcium_mgl: float, magnesium_mgl: float) -> float:
    """Total hardness (mg/L as CaCO3) from Ca and Mg concentrations in mg/L."""
    return calcium_mgl * CA_TO_CACO3 + magnesium_mgl * MG_TO_CACO3


def alkalinity_from_bicarbonate(bicarbonate_mgl: float) -> float:
    """Alkalinity (mg/L as CaCO3) from bicarbonate in mg/L HCO3-, assuming bicarbonate dominates.

    Valid for pH roughly 6 to 9 where carbonate and hydroxide alkalinity are negligible.
    """
    return bicarbonate_mgl * HCO3_TO_CACO3
