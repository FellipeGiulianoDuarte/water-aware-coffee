"""Loader for uk-ni-water: Northern Ireland Water sample results published on OpenDataNI.

Reads every `<year>-ni-water-customer-tap-supply-point-results.csv` (and the older
`<year>-ni-water-customer-tap-results.csv`) under data/raw/uk/ni-water/ plus the
postcode-to-zone lookup `postcode-v-zone-lookup-by-year.csv`, and emits one row per sample for
total hardness, calcium, magnesium, sodium and pH.

Verified against the 2025 file (83,101 rows, 105 parameters):

- The five parameters we keep appear only on "Customer Tap" rows; "Supply Point" rows carry
  other parameters. Both locations are treated as finished water.
- "Site Code" is the water supply zone code (ZS0107 style) and "Site Name" the zone name, 1:1.
  For supply points the code is the works code (W1301P) and the name the works name.
- "Result" and "Report Value" are numerically identical for our parameters. Elsewhere in the file
  a below-detection "Result" reads "<0.011" and "Report Value" reads "0", so "Result" is the
  primary column: "<x" gives below_detection=True with value x.
- "Total hardness" is published with unit "mg/l" but is hardness expressed as mg/l Ca, not as
  CaCO3: on all 504 samples (Ca*2.497 + Mg*4.118) / "Total hardness" = 2.499 +- 0.02, and the
  zone PDF "2025 Water Hardness by Water Supply Zone" lists the zone mean of the CSV figure
  (e.g. 52.38 for ZN0104) next to "Total Hardness (mg CaCO3/l)" = 130.87 = 52.38 * 2.4985.
  The loader therefore converts with the Ca -> CaCO3 factor and flags unit_assumed=True.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from water_aware_coffee.sources import register
from water_aware_coffee.sources.base import SourceFile, frame_from_records
from water_aware_coffee.units import CA_TO_CACO3, Quantity, UnknownUnitError, conversion_factor

log = logging.getLogger(__name__)

SOURCE_ID = "uk-ni-water"
RAW_SUBDIR = ("uk", "ni-water")
DATASET_URL = (
    "https://www.opendatani.gov.uk/dataset/ni-water-customer-tap-authorised-supply-point-results"
)
LICENSE = "UK Open Government Licence (OGL) v3"
COUNTRY = "GB"
ADMIN1 = "Northern Ireland"
UTILITY = "Northern Ireland Water"

# Exact resource download URLs from the CKAN package_show response, fetched 2026-09-14:
# https://admin.opendatani.gov.uk/api/3/action/package_show?id=ni-water-customer-tap-authorised-supply-point-results
_CKAN = "https://admin.opendatani.gov.uk/dataset/38a9a8f1-9346-41a2-8e5f-944d87d9caf2/resource/"
RESOURCE_URLS: dict[str, str] = {
    "postcode-v-zone-lookup-by-year.csv": _CKAN
    + "4c63a2e6-94c5-4cef-9c14-1594ea5d76c0/download/postcode-v-zone-lookup-by-year.csv",
    "2025-ni-water-customer-tap-supply-point-results.csv": _CKAN
    + "d63c20f2-a4f9-4aa1-a6ce-ffe5cf5ce8b5/download/"
    "2025-ni-water-customer-tap-supply-point-results.csv",
    "2024-ni-water-customer-tap-supply-point-results.csv": _CKAN
    + "02d85526-c082-482c-b205-a318f97fd18d/download/"
    "2024-ni-water-customer-tap-supply-point-results.csv",
    "2023-ni-water-customer-tap-supply-point-results.csv": _CKAN
    + "606248be-0fdd-4c42-a846-a70df1a0b212/download/"
    "2023-ni-water-customer-tap-supply-point-results.csv",
    "2022-ni-water-customer-tap-supply-point-results.csv": _CKAN
    + "18e9f161-0792-497f-abfc-1f961afeb644/download/"
    "2022-ni-water-customer-tap-supply-point-results.csv",
    "2021-ni-water-customer-tap-supply-point-results.csv": _CKAN
    + "df4849ce-23ef-4be3-a919-42cbe6e1f3ca/download/"
    "2021-ni-water-customer-tap-supply-point-results.csv",
    "2020-ni-water-customer-tap-supply-point-results.csv": _CKAN
    + "cfaf532b-79e5-4b13-a8f0-adebdf2ce6cd/download/"
    "2020-ni-water-customer-tap-supply-point-results.csv",
    "2019-ni-water-customer-tap-supply-point-results.csv": _CKAN
    + "2d6a9f55-d3a5-48b6-b4ac-4064c372db89/download/"
    "2019-ni-water-customer-tap-supply-point-results.csv",
    "2018-ni-water-customer-tap-supply-point-results.csv": _CKAN
    + "e89dc7f5-0981-40bf-ab4f-5d1c6f7d8a31/download/"
    "2018-ni-water-customer-tap-supply-point-results.csv",
    "2017-ni-water-customer-tap-supply-point-results.csv": _CKAN
    + "02408047-44d9-45db-abc6-5cdd4e7f2bbd/download/"
    "2017-ni-water-customer-tap-supply-point-results.csv",
    "2016-ni-water-customer-tap-supply-point-results.csv": _CKAN
    + "ca7d9a6f-18a4-423c-9644-d35f9bcda866/download/"
    "2016-ni-water-customer-tap-supply-point-results.csv",
    "2015-ni-water-customer-tap-supply-point-results.csv": _CKAN
    + "3996989a-efbe-4998-bf46-9f39f173f6e6/download/"
    "2015-ni-water-customer-tap-supply-point-results.csv",
    "2014-ni-water-customer-tap-supply-point-results.csv": _CKAN
    + "6de794d9-27d9-4659-b677-92f1492d9dde/download/"
    "2014-ni-water-customer-tap-supply-point-results.csv",
    "2013-ni-water-customer-tap-supply-point-results.csv": _CKAN
    + "73a23f91-5706-4052-a8fe-5c17348dc4ad/download/"
    "2013-ni-water-customer-tap-supply-point-results.csv",
    "2012-ni-water-customer-tap-supply-point-results.csv": _CKAN
    + "7f8a23c7-210a-4dae-80a4-05a04cf7095c/download/"
    "2012-ni-water-customer-tap-supply-point-results.csv",
    "2011-ni-water-customer-tap-supply-point-results.csv": _CKAN
    + "6b2c042e-5f15-4401-867c-5a97fa304ae7/download/"
    "2011-ni-water-customer-tap-supply-point-results.csv",
    "2010-ni-water-customer-tap-supply-point-results.csv": _CKAN
    + "01968f42-f36d-4822-ad02-0d1d7e75646e/download/"
    "2010-ni-water-customer-tap-supply-point-results.csv",
    "2009-ni-water-customer-tap-supply-point-results.csv": _CKAN
    + "1c446a58-b713-4596-8171-4fb3fba40fe2/download/"
    "2009-ni-water-customer-tap-supply-point-results.csv",
    "2008-ni-water-customer-tap-supply-point-results.csv": _CKAN
    + "900fb957-0914-47b6-bbdc-1b47a9df3625/download/"
    "2008-ni-water-customer-tap-supply-point-results.csv",
    "2007-ni-water-customer-tap-supply-point-results.csv": _CKAN
    + "75de44a8-855c-4654-9b1e-3aebac4118cd/download/"
    "2007-ni-water-customer-tap-supply-point-results.csv",
    "2006-ni-water-customer-tap-supply-point-results.csv": _CKAN
    + "ac7dcfb8-4795-4789-b94e-08325617bbde/download/"
    "2006-ni-water-customer-tap-supply-point-results.csv",
    "2005-ni-water-customer-tap-supply-point-results.csv": _CKAN
    + "76f10495-4f13-4f13-8a8f-a078d30a3dca/download/"
    "2005-ni-water-customer-tap-supply-point-results.csv",
    "2004-ni-water-customer-tap-supply-point-results.csv": _CKAN
    + "46ddbf3f-c811-4060-8d0f-58b92dd072ae/download/"
    "2004-ni-water-customer-tap-supply-point-results.csv",
    "2003-ni-water-customer-tap-results.csv": _CKAN
    + "1372fed9-b976-40db-9bfb-243e3eb601ee/download/2003-ni-water-customer-tap-results.csv",
    "2002-ni-water-customer-tap-results.csv": _CKAN
    + "03ca24a5-7527-4dd3-bfb1-f1c5b5115d2b/download/2002-ni-water-customer-tap-results.csv",
}
RESULTS_GLOBS = (
    "*-ni-water-customer-tap-supply-point-results.csv",
    "*-ni-water-customer-tap-results.csv",
)
LOOKUP_FILE = "postcode-v-zone-lookup-by-year.csv"

# Source "Parameter" -> our quantity.
PARAMETERS: dict[str, Quantity] = {
    "Total hardness": Quantity.HARDNESS,
    "Calcium": Quantity.CALCIUM,
    "Magnesium": Quantity.MAGNESIUM,
    "Sodium": Quantity.SODIUM,
    "Hydrogen Ion": Quantity.PH,
}

HARDNESS_NOTE = (
    "NI Water CSV unit 'mg/l' for 'Total hardness' is hardness as mg/l Ca, not as CaCO3: "
    "(Ca*2.497 + Mg*4.118) / hardness = 2.50 on every 2025 sample, and the zone PDF lists this "
    "figure's zone mean next to 'Total Hardness (mg CaCO3/l)' = 2.4985 x larger. Converted with "
    "the Ca -> CaCO3 factor; basis inferred, not stated by the source."
)
ION_NOTE = (
    "NI Water CSV unit 'mg/l'; basis mg/l {ion} verified: the zone PDF labels the zone mean "
    "'{label} (mg/l)' and Ca*2.497 + Mg*4.118 reproduces the PDF total hardness as CaCO3"
)

# (parameter, unit verbatim) -> (factor to target unit, unit_assumed, note or None).
# Units not recognised by units.py get an explicit factor here; see the module docstring.
_UNIT_RULES: dict[tuple[str, str], tuple[float, bool, str | None]] = {
    ("Total hardness", "mg/l"): (CA_TO_CACO3, True, HARDNESS_NOTE),
    ("Calcium", "mg/l"): (1.0, False, ION_NOTE.format(ion="Ca", label="Calcium")),
    ("Magnesium", "mg/l"): (1.0, False, ION_NOTE.format(ion="Mg", label="Magnesium")),
    ("Sodium", "mg Na/l"): (1.0, False, None),
    ("Hydrogen Ion", "pH value"): (1.0, False, None),
}

WATER_TYPE_BY_LOCATION: dict[str, str] = {
    "Customer Tap": "finished",
    "Supply Point": "finished",
}
DATE_FORMAT = "%d/%m/%Y %H:%M"


def _unit_rule(parameter: str, unit: str) -> tuple[float, bool, str | None]:
    rule = _UNIT_RULES.get((parameter, unit))
    if rule is not None:
        return rule
    try:
        return conversion_factor(PARAMETERS[parameter], unit), False, None
    except UnknownUnitError as exc:
        raise ValueError(
            f"{SOURCE_ID}: unexpected unit {unit!r} for parameter {parameter!r}; "
            "add a rule to _UNIT_RULES after checking the basis"
        ) from exc


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)


def _read_lookup(path: Path) -> pd.DataFrame:
    """Long table (Postcode, Year, lookup_zone) from the wide postcode-by-year lookup."""
    wide = _read_csv(path)
    years = [c for c in wide.columns if c != "POSTCODE"]
    long = wide.melt(
        id_vars=["POSTCODE"], value_vars=years, var_name="Year", value_name="lookup_zone"
    )
    long = long.rename(columns={"POSTCODE": "Postcode"})
    long["Postcode"] = long["Postcode"].str.strip()
    long["lookup_zone"] = long["lookup_zone"].str.strip()
    return long[long["lookup_zone"] != ""].drop_duplicates(["Postcode", "Year"])


def _parse_result(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Numeric value and below-detection flag from "Result".

    "<x" -> below detection with value x. ">x" has no usable value and is left NaN (dropped by the
    caller). Any other non-numeric "Result" falls back to "Report Value" when that is numeric.
    """
    result = df["Result"].str.strip()
    below = result.str.startswith("<")
    above = result.str.startswith(">")
    value = pd.to_numeric(result.str.lstrip("<").str.strip(), errors="coerce")
    report = pd.to_numeric(df["Report Value"].str.strip(), errors="coerce")
    use_report = value.isna() & ~below & ~above & report.notna()
    if use_report.any():
        log.info(
            "%s: %d rows use 'Report Value' because 'Result' is not numeric",
            SOURCE_ID,
            use_report.sum(),
        )
    if above.any():
        log.warning("%s: %d rows with '>x' Result have no usable value", SOURCE_ID, above.sum())
    value = value.where(~use_report, report).where(~above)
    return value, below & value.notna()


def _notes(df: pd.DataFrame, have_lookup: bool) -> pd.Series:
    postcode = df["Postcode"].str.strip()
    withheld = postcode.str.lower().eq("withheld") | postcode.eq("")
    notes = ("postcode=" + postcode).where(~withheld, "postcode withheld by the source")
    is_supply = df["Sample Location"].eq("Supply Point")
    notes = notes.where(
        ~is_supply, notes + "; authorised supply point (treated water entering supply)"
    )
    if have_lookup:
        lookup_zone = df["lookup_zone"]
        check_lookup = ~withheld & ~is_supply
        missing = check_lookup & lookup_zone.isna()
        differs = check_lookup & lookup_zone.notna() & (lookup_zone != df["Site Code"])
        notes = notes.where(~missing, notes + "; postcode not in " + LOOKUP_FILE)
        notes = notes.where(
            ~differs,
            notes
            + "; "
            + LOOKUP_FILE
            + " gives zone "
            + lookup_zone.fillna("")
            + " for this postcode in "
            + df["Year"],
        )
    unit_note = df["unit_note"]
    return notes.where(unit_note.isna(), notes + "; " + unit_note.fillna(""))


def _records(df: pd.DataFrame, lookup: pd.DataFrame | None, file_name: str) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]
    df["Parameter"] = df["Parameter"].str.strip()
    df = df[df["Parameter"].isin(PARAMETERS)].copy()
    if df.empty:
        return pd.DataFrame()
    for col in ("Sample Location", "Site Code", "Site Name", "Sample Id Text", "Units", "Year"):
        df[col] = df[col].str.strip()

    value, below = _parse_result(df)
    dropped = value.isna()
    if dropped.any():
        log.warning(
            "%s: dropping %d rows of %s with no usable value "
            "('>x', bare '<', or non-numeric 'Result' and 'Report Value'): %s",
            SOURCE_ID,
            dropped.sum(),
            file_name,
            df.loc[dropped, "Result"].value_counts().head(10).to_dict(),
        )
    df = df[~dropped].copy()
    df["original_value"] = value[~dropped].astype(float)
    df["below_detection"] = below[~dropped].to_numpy()

    rules = {key: _unit_rule(*key) for key in set(zip(df["Parameter"], df["Units"], strict=True))}
    keys = list(zip(df["Parameter"], df["Units"], strict=True))
    df["conversion_factor"] = [rules[k][0] for k in keys]
    df["unit_assumed"] = [rules[k][1] for k in keys]
    df["unit_note"] = pd.Series([rules[k][2] for k in keys], index=df.index, dtype="object")

    unknown_location = ~df["Sample Location"].isin(WATER_TYPE_BY_LOCATION)
    if unknown_location.any():
        log.warning(
            "%s: %d rows with unexpected 'Sample Location' %s -> water_type unknown",
            SOURCE_ID,
            unknown_location.sum(),
            df.loc[unknown_location, "Sample Location"].unique().tolist(),
        )

    df["Postcode"] = df["Postcode"].str.strip()
    if lookup is not None:
        df = df.merge(lookup, on=["Postcode", "Year"], how="left")

    sample_date = pd.to_datetime(df["Sample Date"].str.strip(), format=DATE_FORMAT)
    out = pd.DataFrame(
        {
            "source_row_locator": df["Sample Id Text"],
            "country_iso2": COUNTRY,
            "admin1": ADMIN1,
            "locality": df["Site Name"],
            "locality_code": df["Site Code"],
            "utility": UTILITY,
            "utility_code": None,
            "latitude": None,
            "longitude": None,
            "water_type": df["Sample Location"].map(WATER_TYPE_BY_LOCATION).fillna("unknown"),
            "source_type": "unknown",
            "softened": None,
            "period_start": sample_date,
            "period_end": sample_date,
            "quantity": df["Parameter"].map(lambda p: PARAMETERS[p].value),
            "value_type": "sample",
            "n_samples": None,
            "measured": True,
            "below_detection": df["below_detection"],
            "original_parameter_name": df["Parameter"],
            "original_value": df["original_value"],
            "original_unit": df["Units"],
            "conversion_factor": df["conversion_factor"],
            "unit_assumed": df["unit_assumed"],
            "notes": _notes(df, have_lookup=lookup is not None),
        }
    )
    return out


@register(SOURCE_ID)
def load(raw_dir: Path) -> pd.DataFrame:
    """Read data/raw/uk/ni-water/ and return the validated measurement table."""
    folder = raw_dir.joinpath(*RAW_SUBDIR)
    result_files = sorted({p for g in RESULTS_GLOBS for p in folder.glob(g)})
    if not result_files:
        raise FileNotFoundError(f"{SOURCE_ID}: no results CSV under {folder}")

    lookup_path = folder / LOOKUP_FILE
    lookup: pd.DataFrame | None = None
    if lookup_path.exists():
        lookup = _read_lookup(lookup_path)
    else:
        log.warning("%s: %s missing; postcode/zone cross-check skipped", SOURCE_ID, lookup_path)

    frames: list[pd.DataFrame] = []
    for path in result_files:
        src = SourceFile.from_path(
            SOURCE_ID, path, RESOURCE_URLS.get(path.name, DATASET_URL), LICENSE
        )
        records = _records(_read_csv(path), lookup, path.name)
        if records.empty:
            log.warning("%s: %s has no rows for %s", SOURCE_ID, path.name, sorted(PARAMETERS))
            continue
        frames.append(frame_from_records(records, src))
    if not frames:
        raise ValueError(f"{SOURCE_ID}: no usable rows in {[p.name for p in result_files]}")
    return pd.concat(frames, ignore_index=True)
