"""Loader for SISAGUA "Controle Semestral" (Brazil, Ministério da Saúde).

Raw files (data/raw/sisagua/):
- controle_semestral_<year>_csv.zip: one CSV per year with semestral control samples reported by
  water suppliers. One row per (system, sample point, parameter, sample). We keep "Dureza total",
  "Sódio" and "pH" from the parameter column, which is spelled ``PAARAMETRO`` in the header (the
  typo is stable across years and is matched verbatim).
- cadastro_pontos_captacao_csv.zip: registry of intake points, one row per intake point per year,
  with TP_CAPTACAO (SUPERFICIAL / SUBTERRANEO) and coordinates. Joined on
  (NU_SOLUCAO_ABASTECIMENTO, NU_ANO), falling back to NU_SOLUCAO_ABASTECIMENTO alone, to give
  source_type and a location to rows whose own TP_CAPTACAO is empty (all treated-water rows).

Format facts used here (verified on the 2025 file): ISO-8859-1, ";" separator, decimal comma in
RESULTADO with an occasional "." thousands separator ("23.360,0000") and a few rows written with a
decimal point and no comma ("8.71"). Below-limit results carry the token MENOR_LQ or MENOR_LD in
RESULTADO with the limit in the LQ or LD column. Coordinates in the cadastro use a decimal point.
"""

from __future__ import annotations

import logging
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from water_aware_coffee.sources import register
from water_aware_coffee.sources.base import SourceFile, frame_from_records
from water_aware_coffee.units import Quantity

log = logging.getLogger(__name__)

SOURCE_ID = "sisagua-br"
BASE_URL = "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SISAGUA/"
LICENSE = "Creative Commons Atribuição (cc-by)"
DOWNLOAD_DATE = date(2026, 9, 14)
SUBDIR_NAMES = ("sisagua", SOURCE_ID)
SEMESTRAL_GLOB = "controle_semestral_*_csv.zip"
CADASTRO_ZIP = "cadastro_pontos_captacao_csv.zip"
CHUNK_ROWS = 500_000

PARAM_COL = "PAARAMETRO"  # sic: header typo, stable across years
QUANTITY_BY_PARAM: dict[str, Quantity] = {
    "Dureza total": Quantity.HARDNESS,
    "Sódio": Quantity.SODIUM,
    "pH": Quantity.PH,
}
# Present in the file but not in the Quantity enum yet; counted for the report only.
COUNTED_ONLY_PARAMS = ("Cloreto", "Sulfato")

SEMESTRAL_COLS = [
    "SG_UF",
    "NO_MUNICIPIO",
    "CO_MUNICIPIO_IBGE",
    "NO_INSTITUICAO",
    "TP_ABASTECIMENTO",
    "NU_SOLUCAO_ABASTECIMENTO",
    "NO_SOLUCAO_ABASTECIMENTO",
    "NU_ANO",
    "DT_COLETA",
    "PT_MONITORAMENTO",
    PARAM_COL,
    "TP_CAPTACAO",
    "UNIDADE",
    "LD",
    "LQ",
    "RESULTADO",
]
CADASTRO_COLS = [
    "NU_SOLUCAO_ABASTECIMENTO",
    "NU_ANO",
    "TP_CAPTACAO",
    "NU_LATITUDE",
    "NU_LONGITUDE",
]

WATER_TYPE_BY_POINT: dict[str, str] = {
    "PONTO DE CAPTAÇÃO": "source",
    "SAÍDA DO TRATAMENTO": "finished",
    "SISTEMA DE DISTRIBUIÇÃO": "finished",
    "PONTO DE CONSUMO": "finished",
}
SOURCE_TYPE_BY_CAPTACAO: dict[str, str] = {"SUPERFICIAL": "surface", "SUBTERRANEO": "ground"}
BELOW_LIMIT_TOKENS: dict[str, str] = {"MENOR_LQ": "LQ", "MENOR_LD": "LD"}

# Brazil bounding box for coordinate plausibility.
LAT_RANGE = (-34.0, 6.0)
LON_RANGE = (-74.0, -34.0)

HARDNESS_NOTE = (
    "SISAGUA reports Dureza total in mg/L; legal limit VMP 300 mg/L matches Portaria GM/MS "
    "888/2021 hardness as CaCO3, so basis assumed as CaCO3"
)


@dataclass
class LoadReport:
    """Counts collected while loading, for the human report (not part of the output table)."""

    files: list[str] = field(default_factory=list)
    rows_scanned: int = 0
    rows_by_param: dict[str, int] = field(default_factory=dict)
    counted_only: dict[str, int] = field(default_factory=dict)
    dropped: dict[str, int] = field(default_factory=dict)
    below_detection: dict[str, int] = field(default_factory=dict)
    source_type_origin: dict[str, int] = field(default_factory=dict)
    utility_fallback_rows: int = 0
    result_decimal_point_rows: int = 0
    result_thousands_sep_rows: int = 0
    date_unparsed_rows: int = 0
    coordinates_from: dict[str, int] = field(default_factory=dict)
    cadastro_rows: int = 0
    cadastro_implausible_coordinate_rows: int = 0
    cadastro_missing_coordinate_rows: int = 0
    cadastro_system_years_mixed: int = 0
    cadastro_system_years_multi_intake: int = 0

    def bump(self, counter: dict[str, int], key: str, n: int = 1) -> None:
        counter[key] = counter.get(key, 0) + int(n)


def _source_dir(raw_dir: Path) -> Path:
    """data/raw/sisagua/ in the repo layout; the directory itself when it holds the zips."""
    for name in SUBDIR_NAMES:
        if (raw_dir / name).is_dir():
            return raw_dir / name
    return raw_dir


def _csv_name(zip_path: Path) -> str:
    with zipfile.ZipFile(zip_path) as z:
        names = [n for n in z.namelist() if n.lower().endswith(".csv")]
    if len(names) != 1:
        raise ValueError(f"{zip_path.name}: expected exactly one CSV inside, found {names}")
    return names[0]


def _iter_zip_csv(zip_path: Path, usecols: list[str], chunksize: int) -> Iterator[pd.DataFrame]:
    """Stream the single CSV inside `zip_path` as string chunks, keeping the global row index."""
    name = _csv_name(zip_path)
    with zipfile.ZipFile(zip_path) as z, z.open(name) as fh:
        yield from pd.read_csv(
            fh,
            sep=";",
            encoding="latin-1",
            dtype=str,
            usecols=usecols,
            chunksize=chunksize,
            keep_default_na=True,
            na_values=[""],
        )


def parse_result_number(s: pd.Series) -> pd.Series:
    """SISAGUA numbers: decimal comma, optional '.' thousands separator; a few rows use a decimal
    point with no comma ('8.71'). Non-numeric -> NaN."""
    txt = s.astype("string").str.strip()
    has_comma = txt.str.contains(",", regex=False).fillna(False)
    comma_form = txt.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    normalised = comma_form.where(has_comma, txt)
    return pd.to_numeric(normalised, errors="coerce").astype(float)


def _classify_result_format(s: pd.Series, report: LoadReport) -> None:
    txt = s.astype("string")
    has_dot = txt.str.contains(".", regex=False).fillna(False)
    has_comma = txt.str.contains(",", regex=False).fillna(False)
    report.result_decimal_point_rows += int((has_dot & ~has_comma).sum())
    report.result_thousands_sep_rows += int((has_dot & has_comma).sum())


def _load_cadastro(path: Path, report: LoadReport) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Aggregate the intake registry to one row per (system, year) and one row per system.

    Columns of both frames: cad_source_type, cad_lat, cad_lon (centroid of plausible intake
    coordinates), cad_n_intakes, cad_n_coords.
    """
    parts = list(_iter_zip_csv(path, CADASTRO_COLS, CHUNK_ROWS))
    cad = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=CADASTRO_COLS)
    report.cadastro_rows = len(cad)
    lat = pd.to_numeric(cad["NU_LATITUDE"].str.replace(",", ".", regex=False), errors="coerce")
    lon = pd.to_numeric(cad["NU_LONGITUDE"].str.replace(",", ".", regex=False), errors="coerce")
    present = lat.notna() & lon.notna()
    plausible = present & lat.between(*LAT_RANGE) & lon.between(*LON_RANGE)
    report.cadastro_missing_coordinate_rows = int((~present).sum())
    report.cadastro_implausible_coordinate_rows = int((present & ~plausible).sum())
    work = pd.DataFrame(
        {
            "system": cad["NU_SOLUCAO_ABASTECIMENTO"],
            "year": cad["NU_ANO"],
            "is_surface": (cad["TP_CAPTACAO"] == "SUPERFICIAL").astype(int),
            "is_ground": (cad["TP_CAPTACAO"] == "SUBTERRANEO").astype(int),
            "lat": lat.where(plausible),
            "lon": lon.where(plausible),
            "has_coord": plausible.astype(int),
        }
    ).dropna(subset=["system"])

    def aggregate(keys: list[str]) -> pd.DataFrame:
        g = work.groupby(keys, sort=False)
        out = g.agg(
            n_surface=("is_surface", "sum"),
            n_ground=("is_ground", "sum"),
            cad_lat=("lat", "mean"),
            cad_lon=("lon", "mean"),
            cad_n_intakes=("system", "size"),
            cad_n_coords=("has_coord", "sum"),
        )
        stype = np.select(
            [
                (out["n_surface"] > 0) & (out["n_ground"] > 0),
                out["n_surface"] > 0,
                out["n_ground"] > 0,
            ],
            ["mixed", "surface", "ground"],
            default="unknown",
        )
        out["cad_source_type"] = stype
        return out.drop(columns=["n_surface", "n_ground"])

    by_year = aggregate(["system", "year"])
    by_system = aggregate(["system"])
    report.cadastro_system_years_mixed = int((by_year["cad_source_type"] == "mixed").sum())
    report.cadastro_system_years_multi_intake = int((by_year["cad_n_intakes"] > 1).sum())
    return by_year, by_system


def _read_semestral(path: Path, report: LoadReport) -> pd.DataFrame:
    """Rows for our parameters only, with the 0-based data row index of the CSV preserved."""
    wanted = set(QUANTITY_BY_PARAM)
    kept: list[pd.DataFrame] = []
    for chunk in _iter_zip_csv(path, SEMESTRAL_COLS, CHUNK_ROWS):
        report.rows_scanned += len(chunk)
        params = chunk[PARAM_COL]
        for p in COUNTED_ONLY_PARAMS:
            report.bump(report.counted_only, p, int((params == p).sum()))
        kept.append(chunk[params.isin(wanted)])
    if not kept:
        return pd.DataFrame(columns=SEMESTRAL_COLS)
    return pd.concat(kept)


def _join_cadastro(
    df: pd.DataFrame, by_year: pd.DataFrame, by_system: pd.DataFrame, report: LoadReport
) -> pd.DataFrame:
    """Attach cad_* columns: (system, year) match first, then any-year match for the system."""
    keys = pd.DataFrame(
        {"system": df["NU_SOLUCAO_ABASTECIMENTO"].values, "year": df["NU_ANO"].values}
    )
    year_hit = keys.merge(by_year, how="left", left_on=["system", "year"], right_index=True)
    sys_hit = keys.merge(by_system, how="left", left_on="system", right_index=True)
    cols = ["cad_source_type", "cad_lat", "cad_lon", "cad_n_intakes", "cad_n_coords"]
    matched_year = year_hit["cad_n_intakes"].notna()
    matched_sys = ~matched_year & sys_hit["cad_n_intakes"].notna()
    out = year_hit[cols].where(matched_year, sys_hit[cols])
    out["cad_match"] = np.select(
        [matched_year, matched_sys], ["system_year", "system_any_year"], default="none"
    )
    out.index = df.index
    return pd.concat([df, out], axis=1)


def _build_records(df: pd.DataFrame, csv_name: str, report: LoadReport) -> pd.DataFrame:
    """Per-row measurement columns for frame_from_records (drops rows with no usable value)."""
    params = df[PARAM_COL]
    for p, n in params.value_counts().items():
        report.bump(report.rows_by_param, str(p), int(n))

    result = df["RESULTADO"].astype("string").str.strip()
    token = result.where(result.isin(list(BELOW_LIMIT_TOKENS)))
    below = token.notna().fillna(False).astype(bool)
    limit_col = token.map(BELOW_LIMIT_TOKENS)
    limit_text = df["LQ"].where(limit_col == "LQ", df["LD"]).where(limit_col.notna())
    _classify_result_format(result.where(~below), report)
    value = parse_result_number(result.where(~below)).where(~below, parse_result_number(limit_text))

    quantity = params.map({k: v.value for k, v in QUANTITY_BY_PARAM.items()})
    is_ph = quantity == Quantity.PH.value

    # Drop rules: no number at all, below-limit token without a numeric limit, and values the
    # schema refuses (pH outside 0-14, negative concentrations). Everything else is emitted.
    result_missing = ~below & result.isna()
    result_non_numeric = ~below & result.notna() & value.isna()
    limit_missing = below & value.isna()
    ph_out = is_ph & value.notna() & ~value.between(0, 14)
    negative = ~is_ph & (value < 0)
    report.bump(report.dropped, "result_missing", int(result_missing.sum()))
    report.bump(report.dropped, "result_non_numeric", int(result_non_numeric.sum()))
    report.bump(report.dropped, "below_limit_without_numeric_limit", int(limit_missing.sum()))
    report.bump(report.dropped, "ph_outside_0_14", int(ph_out.sum()))
    report.bump(report.dropped, "negative_concentration", int(negative.sum()))
    keep = ~(result_missing | result_non_numeric | limit_missing | ph_out | negative)

    for tok in BELOW_LIMIT_TOKENS:
        report.bump(report.below_detection, tok, int((keep & (token == tok)).sum()))

    row_type = df["TP_CAPTACAO"].map(SOURCE_TYPE_BY_CAPTACAO)
    cad_type = df["cad_source_type"].where(df["cad_source_type"].notna(), None)
    source_type = row_type.where(row_type.notna(), cad_type).fillna("unknown")
    origin = pd.Series(
        np.select(
            [row_type.notna(), cad_type.notna()],
            ["row_TP_CAPTACAO", "cadastro_" + df["cad_match"].astype(str)],
            default="unknown",
        ),
        index=df.index,
    )
    for o, n in origin[keep].value_counts().items():
        report.bump(report.source_type_origin, str(o), int(n))

    institution = df["NO_INSTITUICAO"].str.strip().replace("", None)
    utility = institution.where(institution.notna(), df["NO_SOLUCAO_ABASTECIMENTO"])
    report.utility_fallback_rows += int((institution.isna() & keep).sum())

    period = pd.to_datetime(df["DT_COLETA"], format="%d/%m/%Y", errors="coerce")
    report.date_unparsed_rows += int((period.isna() & keep).sum())

    has_coord = df["cad_lat"].notna() & df["cad_lon"].notna()
    coord_origin = ("cadastro_" + df["cad_match"].astype(str)).where(has_coord, "none")
    for o, n in coord_origin[keep].value_counts().items():
        report.bump(report.coordinates_from, str(o), int(n))

    notes = "TP_ABASTECIMENTO=" + df["TP_ABASTECIMENTO"].fillna("").astype(str)
    notes = notes.where(quantity != Quantity.HARDNESS.value, notes + "; " + HARDNESS_NOTE)
    coord_note = (
        "; coordinates=centroid of "
        + df["cad_n_coords"].fillna(0).astype(int).astype(str)
        + " intake point(s) from cadastro_pontos_captacao ("
        + df["cad_match"].astype(str)
        + ")"
    )
    notes = notes.where(~has_coord, notes + coord_note)

    unit = df["UNIDADE"].str.strip()
    unit = unit.where(unit.notna() & (unit != ""), None)

    records = pd.DataFrame(
        {
            "source_row_locator": f"file:{csv_name};line:"
            + pd.Series(df.index, index=df.index).astype(str),
            "country_iso2": "BR",
            "admin1": df["SG_UF"],
            "locality": df["NO_MUNICIPIO"],
            "locality_code": df["CO_MUNICIPIO_IBGE"],
            "utility": utility,
            "utility_code": df["NU_SOLUCAO_ABASTECIMENTO"],
            "latitude": df["cad_lat"].astype(float),
            "longitude": df["cad_lon"].astype(float),
            "water_type": df["PT_MONITORAMENTO"].map(WATER_TYPE_BY_POINT).fillna("unknown"),
            "source_type": source_type,
            "softened": None,
            "period_start": period,
            "period_end": period,
            "quantity": quantity,
            "value_type": "sample",
            "n_samples": None,
            "measured": True,
            "below_detection": below,
            "original_parameter_name": params,
            "original_value": value,
            "original_unit": unit,
            # Sodium mg/L is unambiguous; only the hardness basis is assumed (see HARDNESS_NOTE).
            "unit_assumed": quantity == Quantity.HARDNESS.value,
            "notes": notes,
        },
        index=df.index,
    )
    records["softened"] = records["softened"].astype("boolean")
    records["n_samples"] = records["n_samples"].astype(float)
    return records[keep].reset_index(drop=True)


def load_with_report(raw_dir: Path) -> tuple[pd.DataFrame, LoadReport]:
    """Load every controle_semestral_*_csv.zip under raw_dir (or raw_dir/sisagua) and return the
    validated measurement table plus the counts a human wants to see."""
    report = LoadReport()
    src_dir = _source_dir(raw_dir)
    zips = sorted(src_dir.glob(SEMESTRAL_GLOB))
    if not zips:
        raise FileNotFoundError(f"no {SEMESTRAL_GLOB} under {src_dir}")
    cadastro_path = src_dir / CADASTRO_ZIP
    if not cadastro_path.exists():
        raise FileNotFoundError(f"missing {cadastro_path}")

    by_year, by_system = _load_cadastro(cadastro_path, report)
    frames: list[pd.DataFrame] = []
    for zip_path in zips:
        report.files.append(zip_path.name)
        src = SourceFile.from_path(
            SOURCE_ID,
            zip_path,
            url=BASE_URL + zip_path.name,
            license=LICENSE,
            download_date=DOWNLOAD_DATE,
        )
        raw = _read_semestral(zip_path, report)
        if raw.empty:
            log.info("%s: no rows for %s", zip_path.name, sorted(QUANTITY_BY_PARAM))
            continue
        joined = _join_cadastro(raw, by_year, by_system, report)
        records = _build_records(joined, _csv_name(zip_path), report)
        frames.append(frame_from_records(records, src))
        log.info("%s: %d rows emitted", zip_path.name, len(records))
    if not frames:
        raise ValueError(f"no usable rows in {[z.name for z in zips]}")
    return pd.concat(frames, ignore_index=True), report


@register(SOURCE_ID)
def load(raw_dir: Path) -> pd.DataFrame:
    df, _ = load_with_report(raw_dir)
    return df
