"""Loader for the UK "Stream" open-data hub (source id "uk-stream").

Stream (https://www.streamwaterdata.co.uk, an ArcGIS Hub) is where England and Wales water
companies publish household-tap sample results: one row per sample per determinand, located by
ONS Lower-layer Super Output Area (LSOA) code. Only three companies publish the chemistry this
project needs, so only these are loaded:

- Wessex Water 2016-2025: total hardness, alkalinity, sodium, pH.
- Southern Water 2016-2026 (four files, about 2.5 M rows): calcium, magnesium, sodium, pH,
  alkalinity, total hardness. Its Units column never carries a unit (it only mirrors the
  Operator column), so every conversion here rests on a documented assumption and is flagged.
- Yorkshire Water 2022-2026: total hardness (basis unstated), sodium, pH.

Files are expected under ``<raw_dir>/uk/stream/<company>/*.csv``. Column names differ in case
between companies (Sample_Id / SAMPLE_ID, OBJECTID / ObjectId) and are normalised to lower case.
Dates come in three shapes ("2022-02-21", "2016/01/04", "1/29/2025 12:00:00 AM", plus
"2026/02/12 00:00:00+00"); all are parsed with explicit formats and unparsable rows are dropped
and counted. Also dropped and counted: empty or non-numeric results, rows without an LSOA, and
pH values outside 0-14 (entry errors the schema rejects).

`load()` is the registered entry point; `load_with_stats()` also returns the counters a report
needs (rows skipped and why, flags, per-file timing).
"""

from __future__ import annotations

import logging
import re
import time
from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import EllipsisType

import pandas as pd

from water_aware_coffee.sources import register
from water_aware_coffee.sources.base import SourceFile, frame_from_records
from water_aware_coffee.units import (
    Quantity,
    conversion_factor,
    is_ambiguous,
    normalize_unit_string,
)

log = logging.getLogger(__name__)

SOURCE_ID = "uk-stream"
ITEM_CSV_URL = "https://www.streamwaterdata.co.uk/api/download/v1/items/{item_id}/csv?layers=0"
# Used only when a file cannot be tied to an item id with certainty; counted in stats.
GENERIC_URL = "https://www.streamwaterdata.co.uk/"

COUNTRY = "GB"
ADMIN1 = "England"
WATER_TYPE = "finished"  # household tap samples
SOURCE_TYPE = "unknown"
VALUE_TYPE = "sample"

# Columns we read from every file (after lower-casing the header). Files may lack some of them.
_WANTED_COLUMNS = frozenset(
    {"sample_id", "sample_date", "determinand", "units", "operator", "result", "lsoa", "objectid"}
)

_LSOA_CODE = re.compile(r"^[EW]\d{8}$")
_MISSING_LSOA = frozenset({"", "null", "none", "nan", "na", "n/a", "#n/a"})

# Every date shape seen in the files. Order matters only for speed; each row is parsed by the
# first format that fits. A trailing UTC offset ("+00") is removed before parsing.
_DATE_FORMATS: tuple[str, ...] = (
    "%Y-%m-%d",  # Wessex: 2022-02-21
    "%Y/%m/%d",  # Southern: 2016/01/04
    "%m/%d/%Y %I:%M:%S %p",  # Yorkshire Hub CSV: 1/29/2025 12:00:00 AM (month first)
    "%Y/%m/%d %H:%M:%S",  # Yorkshire paged export: 2026/02/25 00:00:00
    "%d/%m/%Y",  # bare UK date, e.g. 07/10/2022 (day first); none seen so far
)
_UTC_SUFFIX = re.compile(r"\+00(:?00)?$")


@dataclass(frozen=True)
class _Rule:
    """How one (determinand, unit) pair of one company maps onto the schema."""

    quantity: Quantity
    factor: float | None = None  # None -> conversion_factor(quantity, unit)
    unit_assumed: bool | None = None  # None -> base default (ambiguous bare mg/L -> True)
    notes: str | None = None
    # Ellipsis (the default) -> pass the file's unit string verbatim.
    original_unit: str | None | EllipsisType = ...


# Rule keys: (stripped determinand name, normalised unit string) or (name, None) for "any unit".
_RuleTable = Mapping[tuple[str, str | None], _Rule]


@dataclass(frozen=True)
class _Company:
    slug: str  # folder name under <raw_dir>/uk/stream/
    utility: str
    rules: _RuleTable
    skip: frozenset[str]  # determinands to drop but count (redundant duplicates)
    item_id: Callable[[Path], str | None]
    license: Callable[[Path], str]


# --- Wessex Water -----------------------------------------------------------------------------

_WESSEX_ITEM = "9d9900db3b5d484e84e2319fd1c6ca54"
_WESSEX_LICENSE = (
    "Wessex Water Domestic Water Quality © 2025 by Wessex Water is licensed under CC BY 4.0"
)
_WESSEX_UG_NOTE = (
    "Unit labelled 'μg/l Na' but the values (5 to 126) sit in the same range as the 'mg/L Na' "
    "sodium rows; treated as mislabelled mg/L Na"
)
_WESSEX_RULES: _RuleTable = {
    # "mg CaCO3/L" says the basis, so nothing is assumed; units.py does not know this spelling
    # yet, hence the explicit factor (see the loader report for the requested units.py change).
    ("Total hardness", "mg caco3/l"): _Rule(Quantity.HARDNESS, factor=1.0, unit_assumed=False),
    ("Alkalinity (methyl orange)", "mg caco3/l"): _Rule(
        Quantity.ALKALINITY, factor=1.0, unit_assumed=False
    ),
    ("Sodium (total)", "mg/l na"): _Rule(Quantity.SODIUM),
    ("Sodium (total)", "μg/l na"): _Rule(
        Quantity.SODIUM, factor=1.0, unit_assumed=True, notes=_WESSEX_UG_NOTE
    ),
    ("Hydrogen ion (pH) - indicator - zone", "ph value"): _Rule(
        Quantity.PH, factor=1.0, unit_assumed=False
    ),
}

# --- Southern Water ---------------------------------------------------------------------------

# Item ids verified 2026-09-14 against arcgis.com item metadata (title / service name).
_SOUTHERN_ITEMS: dict[tuple[str, str, str], str] = {
    ("2016", "2018", "1"): "378996afd7574138aec2058ef1789dc3",
    ("2018", "2022", "1"): "1677bec2d846429a9a2224fcb205c1b1",
    ("2022", "2026", "1"): "c5bf5e8411364c308272137b08177872",
    ("2022", "2026", "2"): "2ca547850a5e4375be80c1f7c28718d5",
}
_SOUTHERN_FILE_KEY = re.compile(r"(\d{4})_(\d{4})_part(\d)", re.IGNORECASE)
_SOUTHERN_LICENSE = "CC BY 4.0"
_SOUTHERN_ION_NOTE = "Southern Water Stream file has empty Units; mg/L assumed"
_SOUTHERN_ALK_NOTE = (
    "Southern Water Stream file has empty Units; basis (CaCO3 vs HCO3) not stated; assumed as CaCO3"
)
_SOUTHERN_HARDNESS_NOTE = (
    "Southern Water reports total hardness as mg/L calcium per its web checker "
    "(HARDNESS (TOTAL) tracks CALCIUM about 1:1 in the file); converted to as CaCO3"
)
_SOUTHERN_HARDNESS_UNIT = "mg/L Ca"
_SOUTHERN_RULES: _RuleTable = {
    ("CALCIUM", None): _Rule(
        Quantity.CALCIUM, factor=1.0, unit_assumed=True, notes=_SOUTHERN_ION_NOTE
    ),
    ("MAGNESIUM", None): _Rule(
        Quantity.MAGNESIUM, factor=1.0, unit_assumed=True, notes=_SOUTHERN_ION_NOTE
    ),
    ("SODIUM", None): _Rule(
        Quantity.SODIUM, factor=1.0, unit_assumed=True, notes=_SOUTHERN_ION_NOTE
    ),
    ("PH", None): _Rule(Quantity.PH, factor=1.0, unit_assumed=False, original_unit=None),
    ("ALKALINITY", None): _Rule(
        Quantity.ALKALINITY, factor=1.0, unit_assumed=True, notes=_SOUTHERN_ALK_NOTE
    ),
    ("HARDNESS (TOTAL)", None): _Rule(
        Quantity.HARDNESS,
        factor=conversion_factor(Quantity.HARDNESS, _SOUTHERN_HARDNESS_UNIT),
        unit_assumed=True,
        notes=_SOUTHERN_HARDNESS_NOTE,
        original_unit=_SOUTHERN_HARDNESS_UNIT,
    ),
}
# Redundant duplicates of rows we already emit: same samples, other expression.
_SOUTHERN_SKIP = frozenset({"ALKALINITY (BICARBONATE)", "HARDNESS (°DH)", "HARDNESS (?DH)"})

# --- Yorkshire Water --------------------------------------------------------------------------

# Item ids verified 2026-09-14 via the arcgis.com search API (titles "... Drinking Water Quality
# <year>"); the 2026 id also appears in the Hub download's file name.
_YORKSHIRE_ITEMS: dict[str, str] = {
    "2022": "1c4e280cf21b4cfa803351e798e762b6",
    "2023": "fb641f56af3c418298dcdd052e40eb78",
    "2024": "6fff0eef81cf466f8363be7153d85f57",
    "2025": "b9278dad0f1e42b29509fd5aadd531f7",
    "2026": "a71a93148df04e579fb5694e59cee61e",
}
_YORKSHIRE_YEAR = re.compile(r"(20\d\d)")
_YORKSHIRE_HARDNESS_NOTE = (
    "Yorkshire Water hardness unit 'mg/l' with basis unstated; assumed as CaCO3 "
    "(range 2 to 380 consistent with CaCO3)"
)
_YORKSHIRE_RULES: _RuleTable = {
    # bare "mg/l": base flags unit_assumed=True on its own; the note says why it is acceptable.
    ("Hardness total", "mg/l"): _Rule(Quantity.HARDNESS, notes=_YORKSHIRE_HARDNESS_NOTE),
    ("Sodium (Total)", "mg/l na"): _Rule(Quantity.SODIUM),
    ("Hydrogen ion (pH) - Indicator (Hydrogen ion) (pH)", "ph value"): _Rule(
        Quantity.PH, factor=1.0, unit_assumed=False
    ),
}


def _yorkshire_year(path: Path) -> str | None:
    m = _YORKSHIRE_YEAR.search(path.name)
    return m.group(1) if m else None


def _yorkshire_item(path: Path) -> str | None:
    year = _yorkshire_year(path)
    return _YORKSHIRE_ITEMS.get(year) if year else None


def _yorkshire_license(path: Path) -> str:
    year = _yorkshire_year(path) or "<year>"
    return (
        f"Yorkshire Water Drinking Water Quality {year} © 2024 by Yorkshire Water "
        "is licensed under CC BY 4.0"
    )


def _southern_item(path: Path) -> str | None:
    m = _SOUTHERN_FILE_KEY.search(path.name)
    return _SOUTHERN_ITEMS.get((m.group(1), m.group(2), m.group(3))) if m else None


COMPANIES: tuple[_Company, ...] = (
    _Company(
        slug="wessex-water",
        utility="Wessex Water",
        rules=_WESSEX_RULES,
        skip=frozenset(),
        item_id=lambda _p: _WESSEX_ITEM,
        license=lambda _p: _WESSEX_LICENSE,
    ),
    _Company(
        slug="southern-water",
        utility="Southern Water",
        rules=_SOUTHERN_RULES,
        skip=_SOUTHERN_SKIP,
        item_id=_southern_item,
        license=lambda _p: _SOUTHERN_LICENSE,
    ),
    _Company(
        slug="yorkshire-water",
        utility="Yorkshire Water",
        rules=_YORKSHIRE_RULES,
        skip=frozenset(),
        item_id=_yorkshire_item,
        license=_yorkshire_license,
    ),
)


@dataclass
class LoadStats:
    """Counters for the loader report. Keys of the per-file counters are file names."""

    files_read: list[str] = field(default_factory=list)
    files_skipped_stale: list[str] = field(default_factory=list)
    files_generic_url: list[str] = field(default_factory=list)
    rows_read: int = 0
    rows_emitted: int = 0
    # determinand -> rows dropped because the determinand is a redundant duplicate
    skipped_determinands: Counter[str] = field(default_factory=Counter)
    # (utility, determinand, unit) -> rows dropped because no rule covers that unit string
    unmapped_units: Counter[tuple[str, str, str]] = field(default_factory=Counter)
    non_numeric_results: Counter[str] = field(default_factory=Counter)
    unparsable_dates: Counter[str] = field(default_factory=Counter)
    date_format_hits: Counter[str] = field(default_factory=Counter)
    missing_lsoa: Counter[str] = field(default_factory=Counter)
    lsoa_not_a_code: int = 0
    above_limit_rows: int = 0  # Operator ">" on an emitted row (value kept, flag not set)
    # pH outside 0-14 (entry errors); the schema rejects them, so they are dropped, not emitted
    ph_out_of_range: Counter[str] = field(default_factory=Counter)
    wessex_ug_sodium_relabelled: int = 0
    seconds: dict[str, float] = field(default_factory=dict)


def parse_sample_dates(s: pd.Series, stats: LoadStats | None = None) -> pd.Series:
    """Parse the date strings seen in Stream files; NaT where no known format fits."""
    raw = s.astype("string").str.strip().str.replace(_UTC_SUFFIX, "", regex=True)
    out = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
    for fmt in _DATE_FORMATS:
        todo = out.isna() & raw.notna()
        if not todo.any():
            break
        parsed = pd.to_datetime(raw[todo], format=fmt, errors="coerce")
        out.loc[todo] = parsed.astype("datetime64[ns]")
        if stats is not None:
            stats.date_format_hits[fmt] += int(parsed.notna().sum())
    return out


def _optional_strings(s: pd.Series) -> list[str | None]:
    """Series values as str, with every kind of missing value (NaN, pd.NA, None) as None."""
    return [None if pd.isna(v) else str(v) for v in s.tolist()]


def _read_csv(path: Path) -> pd.DataFrame:
    """Read only the columns we use, as strings, with a lower-cased header."""
    df = pd.read_csv(
        path,
        dtype=str,
        encoding="utf-8-sig",
        usecols=lambda c: c.strip().lower() in _WANTED_COLUMNS,
        keep_default_na=False,
        na_values=[""],
    )
    df.columns = [c.strip().lower() for c in df.columns]
    return df


def _stale_hub_exports(paths: list[Path]) -> set[Path]:
    """A Hub CSV is stale when a paged FeatureServer export of the same dataset sits beside it.

    The paged export is named ``<hub stem>.featureserver_paged_<date>.csv``.
    """
    names = {p.name: p for p in paths}
    stale: set[Path] = set()
    for p in paths:
        if ".featureserver_paged_" in p.name:
            hub_name = p.name.split(".featureserver_paged_", 1)[0] + ".csv"
            if hub_name in names:
                stale.add(names[hub_name])
    return stale


def _select_rule(
    det: pd.Series, unit_norm: pd.Series, company: _Company
) -> tuple[pd.Series, pd.Series]:
    """Return (the matching _Rule or None per row, mask of rows whose determinand is skipped)."""
    rules = company.rules
    any_unit: dict[str, _Rule] = {d: r for (d, u), r in rules.items() if u is None}
    exact: dict[tuple[str, str], _Rule] = {(d, u): r for (d, u), r in rules.items() if u}
    keys = list(zip(det, unit_norm, strict=True))
    chosen = [exact.get(k) or any_unit.get(k[0]) for k in keys]
    return pd.Series(chosen, index=det.index, dtype=object), det.isin(company.skip)


def _records_for_file(company: _Company, path: Path, stats: LoadStats) -> pd.DataFrame | None:
    t0 = time.perf_counter()
    df = _read_csv(path)
    stats.rows_read += len(df)
    det = df["determinand"].astype("string").str.strip()
    wanted = {d for d, _u in company.rules} | set(company.skip)
    df = df.loc[det.isin(wanted)].copy()
    det = det.loc[df.index]
    if df.empty:
        stats.seconds[path.name] = time.perf_counter() - t0
        return None

    units = df["units"] if "units" in df.columns else pd.Series(pd.NA, index=df.index)
    units = units.astype("string").str.strip()
    # Southern Water's Units column never holds a unit; it mirrors the Operator ("<" / ">").
    units = units.where(~units.isin(["<", ">", ""]), pd.NA)
    unit_norm = units.fillna("").map(normalize_unit_string)
    rule, skip = _select_rule(det, unit_norm, company)
    for name, n in det[skip].value_counts().items():
        stats.skipped_determinands[str(name)] += int(n)
    unmapped = rule.isna() & ~skip
    unmapped_pairs = Counter(
        zip(det[unmapped].tolist(), units[unmapped].fillna("").tolist(), strict=True)
    )
    for (d, u), n in unmapped_pairs.items():
        stats.unmapped_units[(company.utility, str(d), str(u))] += n
    keep = ~skip & ~unmapped
    df, det, units, rule = df[keep], det[keep], units[keep], rule[keep]

    value = pd.to_numeric(df["result"], errors="coerce")
    bad_value = value.isna()
    stats.non_numeric_results[path.name] += int(bad_value.sum())
    date = parse_sample_dates(df["sample_date"], stats)
    bad_date = date.isna()
    stats.unparsable_dates[path.name] += int((bad_date & ~bad_value).sum())
    lsoa = df["lsoa"].astype("string").str.strip()
    # Placeholders seen in Stream files for "no LSOA": empty, "null", "#N/A".
    bad_lsoa = lsoa.isna() | lsoa.str.lower().isin(_MISSING_LSOA)
    stats.missing_lsoa[path.name] += int((bad_lsoa & ~bad_value & ~bad_date).sum())
    keep = ~(bad_value | bad_date | bad_lsoa)
    df = df[keep]
    det, units, rule = det[keep], units[keep], rule[keep]
    value, date, lsoa = value[keep], date[keep], lsoa[keep]
    if df.empty:
        stats.seconds[path.name] = time.perf_counter() - t0
        return None
    stats.lsoa_not_a_code += int((~lsoa.str.match(_LSOA_CODE)).sum())

    is_ph = pd.Series([r.quantity is Quantity.PH for r in rule], index=df.index, dtype=bool)
    bad_ph = is_ph & ~value.between(0.0, 14.0)
    stats.ph_out_of_range[path.name] += int(bad_ph.sum())
    if bad_ph.any():
        keep = ~bad_ph
        df = df[keep]
        det, units, rule = det[keep], units[keep], rule[keep]
        value, date, lsoa = value[keep], date[keep], lsoa[keep]

    operator = (
        df["operator"].astype("string").str.strip()
        if "operator" in df.columns
        else pd.Series(pd.NA, index=df.index, dtype="string")
    )
    below = (operator == "<").fillna(False).astype(bool)
    stats.above_limit_rows += int((operator == ">").fillna(False).sum())

    unit_list = _optional_strings(units)
    factor = pd.Series(
        [
            r.factor if r.factor is not None else conversion_factor(r.quantity, u)
            for r, u in zip(rule, unit_list, strict=True)
        ],
        index=df.index,
        dtype=float,
    )
    original_unit = pd.Series(
        [
            u if r.original_unit is ... else r.original_unit
            for r, u in zip(rule, unit_list, strict=True)
        ],
        index=df.index,
        dtype="string",
    )
    unit_assumed_override = pd.Series([r.unit_assumed for r in rule], index=df.index, dtype=object)
    notes = pd.Series([r.notes for r in rule], index=df.index, dtype="string")
    quantity = pd.Series([r.quantity.value for r in rule], index=df.index, dtype="string")
    if company.slug == "wessex-water":
        stats.wessex_ug_sodium_relabelled += int((notes == _WESSEX_UG_NOTE).sum())

    if "sample_id" in df.columns:
        locator = (
            f"{path.name}:Sample_Id="
            + df["sample_id"].astype("string").fillna("")
            + ";OBJECTID="
            + df["objectid"].astype("string").fillna("")
        )
    elif "objectid" in df.columns:
        locator = f"{path.name}:ObjectId=" + df["objectid"].astype("string").fillna("")
    else:
        locator = pd.Series(
            [f"{path.name};line:{i}" for i in df.index], index=df.index, dtype="string"
        )

    records = pd.DataFrame(
        {
            "source_row_locator": locator,
            "country_iso2": COUNTRY,
            "admin1": ADMIN1,
            "locality": lsoa,
            "locality_code": lsoa.where(lsoa.str.match(_LSOA_CODE), None),
            "utility": company.utility,
            "utility_code": None,
            "water_type": WATER_TYPE,
            "source_type": SOURCE_TYPE,
            "softened": None,
            "period_start": date,
            "period_end": date,
            "quantity": quantity,
            "value_type": VALUE_TYPE,
            "n_samples": None,
            "measured": True,
            "below_detection": below,
            "original_parameter_name": det,
            "original_value": value.astype(float),
            "original_unit": original_unit,
            "conversion_factor": factor,
            "notes": notes,
        },
        index=df.index,
    )
    # unit_assumed: rule value where given, else base's rule (ambiguous bare unit -> True).
    default_assumed = [
        is_ambiguous(u) and q != Quantity.PH.value
        for q, u in zip(
            records["quantity"], _optional_strings(records["original_unit"]), strict=True
        )
    ]
    records["unit_assumed"] = [
        bool(o) if o is not None else d
        for o, d in zip(unit_assumed_override, default_assumed, strict=True)
    ]

    item_id = company.item_id(path)
    if item_id is None:
        stats.files_generic_url.append(path.name)
        url = GENERIC_URL
    else:
        url = ITEM_CSV_URL.format(item_id=item_id)
    src = SourceFile.from_path(SOURCE_ID, path, url, company.license(path))
    out = frame_from_records(records.reset_index(drop=True), src)
    stats.rows_emitted += len(out)
    stats.seconds[path.name] = time.perf_counter() - t0
    log.info("%s: %s rows in %.1fs", path.name, f"{len(out):,}", stats.seconds[path.name])
    return out


def load_with_stats(raw_dir: Path) -> tuple[pd.DataFrame, LoadStats]:
    """Load every company under ``raw_dir/uk/stream`` and return the table plus counters."""
    stats = LoadStats()
    frames: list[pd.DataFrame] = []
    for company in COMPANIES:
        folder = raw_dir / "uk" / "stream" / company.slug
        paths = sorted(folder.glob("*.csv"))
        if not paths:
            raise FileNotFoundError(f"no CSV files for {company.utility} under {folder}")
        stale = _stale_hub_exports(paths)
        for path in paths:
            if path in stale:
                stats.files_skipped_stale.append(path.name)
                continue
            stats.files_read.append(path.name)
            part = _records_for_file(company, path, stats)
            if part is not None:
                frames.append(part)
    if not frames:
        raise ValueError(f"no rows for any target determinand under {raw_dir / 'uk' / 'stream'}")
    return pd.concat(frames, ignore_index=True), stats


@register(SOURCE_ID)
def load(raw_dir: Path) -> pd.DataFrame:
    return load_with_stats(raw_dir)[0]
