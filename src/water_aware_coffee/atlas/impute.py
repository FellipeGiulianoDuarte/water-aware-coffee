"""Alkalinity imputation for localities that report hardness but not alkalinity (Brazil).

Model: log(alkalinity) = a + b * log(hardness) + c[source_type] + e, fitted by weighted least
squares on localities that report both (US utilities joined by PWSID, UK small areas), weights =
population where known (else the median population of the training set, so unweighted rows still
count).

Why log-log: both quantities are positive and right-skewed, and the US/UK scatter in Task 3 is a
diagonal with roughly constant relative spread. The residual standard deviation on the log scale
gives a multiplicative error band; we report the 16th to 84th percentile band (± one residual sd).

Caveat on source type: in the training data, source type is known only for US rows (surface or
ground); every UK row is "unknown". The "unknown" coefficient therefore mostly measures a UK
offset, not a source type. Brazilian rows have real source types (from the SISAGUA intake
registry), so they are predicted with the US-derived surface / ground coefficients. "mixed" has no
training rows and is predicted as the average of surface and ground.

Everything imputed is flagged: alkalinity_imputed = True, with the band and the fit id in columns,
so downstream code can drop or down-weight these rows.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm

TRAIN_SOURCES = ("tapwaterdata-us+epa-syr4-us", "uk-stream")
SOURCE_TYPES = ("surface", "ground", "mixed", "unknown")


@dataclass
class AlkalinityFit:
    params: pd.Series
    resid_sd: float
    r2: float
    n: int
    weighted: bool
    fit_id: str

    def predict_log(self, hardness: pd.Series, source_type: pd.Series) -> pd.Series:
        log_h = pd.Series(
            np.log(hardness.astype(float).clip(lower=1.0).to_numpy()), index=hardness.index
        )
        x = _design(log_h, source_type, levels=_fitted_levels(self.params))
        # "mixed" without a fitted coefficient: average of surface (0) and ground.
        if "st_mixed" not in self.params.index and "st_ground" in self.params.index:
            st = _clean_source_type(source_type)
            x.loc[st == "mixed", "st_ground"] = 0.5
        x = x.reindex(columns=self.params.index, fill_value=0.0)
        return pd.Series(x.to_numpy() @ self.params.to_numpy(), index=hardness.index)


def _clean_source_type(source_type: pd.Series) -> pd.Series:
    st = source_type.fillna("unknown")
    return st.where(st.isin(SOURCE_TYPES), "unknown")


def _fitted_levels(params: pd.Series) -> tuple[str, ...]:
    return tuple(str(k)[3:] for k in params.index if str(k).startswith("st_"))


def _design(
    log_hardness: pd.Series, source_type: pd.Series, levels: tuple[str, ...] | None = None
) -> pd.DataFrame:
    st = _clean_source_type(source_type)
    x = pd.DataFrame(
        {"const": 1.0, "log_hardness": log_hardness.to_numpy()}, index=log_hardness.index
    )
    use = levels if levels is not None else tuple(t for t in SOURCE_TYPES[1:] if (st == t).any())
    for t in use:  # surface is the reference level; only levels present in the data get a column
        x[f"st_{t}"] = (st == t).astype(float).to_numpy()
    return x


def training_frame(wide: pd.DataFrame) -> pd.DataFrame:
    d = wide[wide["source_id"].isin(TRAIN_SOURCES)].copy()
    d["alk"] = pd.to_numeric(d["alkalinity_median"], errors="coerce")
    d["hard"] = pd.to_numeric(d["hardness_best"], errors="coerce")
    d = d.dropna(subset=["alk", "hard"])
    d = d[(d["alk"] > 0) & (d["hard"] > 0) & (d["alk"] < 1000) & (d["hard"] < 1500)]
    return d


def fit_alkalinity(wide: pd.DataFrame) -> AlkalinityFit:
    d = training_frame(wide)
    pop = pd.to_numeric(d["population"], errors="coerce").astype("float64")
    weights = pop.fillna(pop.median() if pop.notna().any() else 1.0).clip(lower=1.0)
    y = np.log(d["alk"].to_numpy(dtype=float))
    log_h = pd.Series(np.log(d["hard"].to_numpy(dtype=float)), index=d.index)
    x = _design(log_h, d["source_type"])
    model = sm.WLS(y, x.to_numpy(), weights=weights.to_numpy()).fit()
    params = pd.Series(model.params, index=x.columns)
    resid = y - x.to_numpy() @ params.to_numpy()
    resid_sd = float(np.sqrt(np.average(resid**2, weights=weights.to_numpy())))
    return AlkalinityFit(
        params=params,
        resid_sd=resid_sd,
        r2=float(model.rsquared),
        n=int(len(d)),
        weighted=bool(pop.notna().any()),
        fit_id="alk_v0_loglog_sourcetype",
    )


def impute_alkalinity(wide: pd.DataFrame, fit: AlkalinityFit) -> pd.DataFrame:
    """Fill alkalinity where missing and hardness exists. Adds columns alkalinity_best,
    alkalinity_imputed, alkalinity_low, alkalinity_high, alkalinity_fit_id."""
    out = wide.copy()
    alk = pd.to_numeric(out["alkalinity_median"], errors="coerce")
    hard = pd.to_numeric(out["hardness_best"], errors="coerce")
    tap = out["source_id"] != "bottled-labels"  # never impute a label; declared values only
    need = alk.isna() & hard.notna() & (hard > 0) & tap
    out["alkalinity_best"] = alk
    out["alkalinity_imputed"] = False
    out["alkalinity_low"] = np.nan
    out["alkalinity_high"] = np.nan
    out["alkalinity_fit_id"] = pd.Series(pd.NA, index=out.index, dtype="string")
    if need.any():
        mu = fit.predict_log(hard[need], out.loc[need, "source_type"])
        out.loc[need, "alkalinity_best"] = np.exp(mu)
        out.loc[need, "alkalinity_low"] = np.exp(mu - fit.resid_sd)
        out.loc[need, "alkalinity_high"] = np.exp(mu + fit.resid_sd)
        out.loc[need, "alkalinity_imputed"] = True
        out.loc[need, "alkalinity_fit_id"] = fit.fit_id
    return out


def fit_report(fit: AlkalinityFit) -> str:
    lines = [
        f"fit {fit.fit_id}: n={fit.n:,}, weighted={fit.weighted}, R2={fit.r2:.3f}, "
        f"residual sd (log)={fit.resid_sd:.3f} -> multiplicative band "
        f"x/÷ {np.exp(fit.resid_sd):.2f}",
        "coefficients (log alkalinity; surface is the reference source type):",
    ]
    for k, v in fit.params.items():
        lines.append(f"  {k:>14s} = {v:+.3f}")
    return "\n".join(lines)
