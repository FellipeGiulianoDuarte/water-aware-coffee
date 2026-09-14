"""Task 4: water regimes by Gaussian mixture on (log alkalinity, log hardness), population-weighted.

Weighting: scikit-learn's GaussianMixture has no sample weights, so parameters are fitted on a large
resample of localities drawn with probability proportional to population (with replacement). Model
selection does NOT use the resample: a resample of 40,000 points would make the BIC penalty look
negligible and favour too many components. Instead BIC is computed on the original localities with
a population-weighted log-likelihood scaled to the Kish effective sample size
n_eff = (sum w)^2 / sum w^2, and the penalty uses ln(n_eff). k is the BIC minimum, capped at K_MAX.
The resample size and seed are fixed so the result is reproducible; the BIC curve is saved so the
cap is visible.

Fitting set: only localities with MEASURED alkalinity (US utilities joined by PWSID, UK small
areas).
Localities with imputed alkalinity (Brazil) are classified into the fitted components afterwards but
do not shape them; otherwise Brazil's 129 million people, all imputed, would define the regimes.

Regime naming is descriptive and derived from the component means; duplicate names get the median
hardness appended so every regime has a distinct label.

Matching table: for each regime mean and each roast bin, the residual acidity relative to the SCA
reference water (40 mg/L alkalinity, 68 mg/L hardness) from the Task 3 model, with the label rule
from decisions.md item 27: 0.75 to 1.25 works; 0.5 to 0.75 or 1.25 to 1.5 compensate; below 0.5
fights (too flat); above 1.5 too sharp.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture

from water_aware_coffee.model.grid import CationParams, Grid, relative_residual
from water_aware_coffee.model.params import CATIONS, ROASTS

K_MAX = 6
RESAMPLE_N = 40_000
SEED = 20260914
REF_ALK, REF_HARD = 40.0, 68.0


@dataclass
class RegimeModel:
    k: int
    means_z: list[list[float]]
    covariances_z: list[list[list[float]]]
    weights: list[float]
    z_mean: list[float]
    z_sd: list[float]
    bic: dict[int, float]
    n_eff: float
    resample_n: int
    seed: int
    names: list[str]

    def to_json(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), indent=2))


def clustering_frame(wide: pd.DataFrame) -> pd.DataFrame:
    """Localities with hardness and (measured or imputed) alkalinity, with a weight column."""
    d = wide.copy()
    d["alk"] = pd.to_numeric(d["alkalinity_best"], errors="coerce")
    d["hard"] = pd.to_numeric(d["hardness_best"], errors="coerce")
    # EPA-only rows have alkalinity but no hardness; joined rows carry both. Avoid double counting:
    # drop the plain tapwaterdata rows whose PWSID also appears in the joined set.
    joined_codes = set(
        d.loc[d["source_id"] == "tapwaterdata-us+epa-syr4-us", "locality_key"].dropna()
    )
    dup = (d["source_id"] == "tapwaterdata-us") & d["locality_key"].isin(joined_codes)
    d = d[~dup]
    d = d.dropna(subset=["alk", "hard"])
    d = d[(d["alk"] > 0) & (d["hard"] > 0) & (d["alk"] < 1000) & (d["hard"] < 1500)]
    pop = pd.to_numeric(d["population"], errors="coerce").astype("float64")
    # Missing population: country median if any, else the global median.
    fill = pop.groupby(d["country_iso2"]).transform("median")
    fill = fill.fillna(pop.median() if pop.notna().any() else 1.0)
    d["weight"] = pop.fillna(fill).clip(lower=1.0)
    d["population_known"] = pop.notna()
    return d


def wmedian(x: pd.Series, w: pd.Series, q: float = 0.5) -> float:
    order = np.argsort(x.to_numpy())
    xs = x.to_numpy()[order]
    ws = w.to_numpy(dtype=float)[order]
    c = np.cumsum(ws) / ws.sum()
    return float(xs[min(int(np.searchsorted(c, q)), len(xs) - 1)])


def _features(d: pd.DataFrame) -> np.ndarray:
    return np.column_stack([np.log10(d["alk"].to_numpy()), np.log10(d["hard"].to_numpy())])


def fit_regimes(d: pd.DataFrame, k_max: int = K_MAX) -> tuple[RegimeModel, pd.Series]:
    rng = np.random.default_rng(SEED)
    measured = ~d["alkalinity_imputed"].astype(bool)
    if measured.sum() < 50:  # tiny test data: fit on everything
        measured = pd.Series(True, index=d.index)
    x_all = _features(d)
    x = x_all[measured.to_numpy()]
    w = d.loc[measured, "weight"].to_numpy(dtype=float)
    p = w / w.sum()
    idx = rng.choice(len(x), size=RESAMPLE_N, replace=True, p=p)
    xs = x[idx]
    z_mean = xs.mean(axis=0)
    z_sd = xs.std(axis=0)
    zs = (xs - z_mean) / z_sd
    z_fit = (x - z_mean) / z_sd
    z_all = (x_all - z_mean) / z_sd
    n_eff = float(w.sum() ** 2 / (w**2).sum())
    wn = w / w.sum() * n_eff  # weights summing to the effective sample size
    bic: dict[int, float] = {}
    models: dict[int, GaussianMixture] = {}
    for k in range(1, k_max + 1):
        gm = GaussianMixture(
            n_components=k, covariance_type="full", n_init=3, random_state=SEED
        ).fit(zs)
        loglik = float((gm.score_samples(z_fit) * wn).sum())
        n_params = gm._n_parameters()
        bic[k] = float(-2.0 * loglik + n_params * np.log(n_eff))
        models[k] = gm
    k_best = min(bic, key=bic.get)  # type: ignore[arg-type]
    gm = models[k_best]
    # Order components by mean alkalinity so regime 1 is the lowest-alkalinity water.
    order = np.argsort(gm.means_[:, 0])
    means = gm.means_[order]
    covs = gm.covariances_[order]
    wts = gm.weights_[order]
    raw_labels = gm.predict(z_all)
    remap = {int(old): int(new) for new, old in enumerate(order)}
    labels = pd.Series([remap[int(r)] + 1 for r in raw_labels], index=d.index, name="regime")
    # Names are assigned from the members' population-weighted medians (see name_from_members),
    # because a broad component's mean can sit far from where its members actually are.
    names = name_from_members(d, labels, int(k_best))
    model = RegimeModel(
        k=int(k_best),
        means_z=means.tolist(),
        covariances_z=covs.tolist(),
        weights=wts.tolist(),
        z_mean=z_mean.tolist(),
        z_sd=z_sd.tolist(),
        bic=bic,
        n_eff=n_eff,
        resample_n=RESAMPLE_N,
        seed=SEED,
        names=names,
    )
    return model, labels


def name_from_members(d: pd.DataFrame, labels: pd.Series, k: int) -> list[str]:
    names, hards = [], []
    for r in range(1, k + 1):
        g = d[labels == r]
        if len(g) == 0:
            names.append(f"empty regime {r}")
            hards.append(0.0)
            continue
        a = wmedian(g["alk"], g["weight"])
        h = wmedian(g["hard"], g["weight"])
        names.append(regime_name(a, h))
        hards.append(h)
    return _unique_names(names, hards)


def _unique_names(names: list[str], hardness: list[float]) -> list[str]:
    out = list(names)
    for i, n in enumerate(names):
        if names.count(n) > 1:
            out[i] = f"{n} (hardness about {hardness[i]:.0f})"
    return out


def regime_name(alk: float, hard: float) -> str:
    if hard < 30 and alk > 60:
        return "softened: alkalinity kept, hardness removed"
    a = (
        "very low alkalinity"
        if alk < 25
        else "low alkalinity"
        if alk < 60
        else "moderate alkalinity"
        if alk < 120
        else "high alkalinity"
        if alk < 200
        else "very high alkalinity"
    )
    h = (
        "soft"
        if hard < 60
        else "moderately hard"
        if hard < 120
        else "hard"
        if hard < 180
        else "very hard"
    )
    return f"{a}, {h}"


def regime_means(model: RegimeModel) -> pd.DataFrame:
    zm, zsd = np.array(model.z_mean), np.array(model.z_sd)
    rows = []
    for i, m in enumerate(model.means_z):
        alk = 10 ** (m[0] * zsd[0] + zm[0])
        hard = 10 ** (m[1] * zsd[1] + zm[1])
        rows.append(
            {"regime": i + 1, "name": model.names[i], "alkalinity_mgl": alk, "hardness_mgl": hard}
        )
    return pd.DataFrame(rows)


def regime_summary(d: pd.DataFrame, labels: pd.Series, model: RegimeModel) -> pd.DataFrame:
    d = d.assign(regime=labels)
    total_w = d["weight"].sum()
    rows = []
    for r_raw, g in d.groupby("regime"):
        r = int(str(r_raw))
        by_country = (g.groupby("country_iso2")["weight"].sum() / g["weight"].sum()).round(3)
        top = g.sort_values("weight", ascending=False).head(5)
        examples = "; ".join(
            f"{loc} ({cc})" for loc, cc in zip(top["locality"], top["country_iso2"], strict=True)
        )
        rows.append(
            {
                "regime": r,
                "name": model.names[r - 1],
                "localities": len(g),
                "population_share": g["weight"].sum() / total_w,
                "alkalinity_median": wmedian(g["alk"], g["weight"]),
                "alkalinity_p10": wmedian(g["alk"], g["weight"], 0.1),
                "alkalinity_p90": wmedian(g["alk"], g["weight"], 0.9),
                "hardness_median": wmedian(g["hard"], g["weight"]),
                "alkalinity_median_unweighted": g["alk"].median(),
                "hardness_median_unweighted": float(g["hard"].median()),
                "share_imputed_alkalinity": g["alkalinity_imputed"].astype(bool).mean(),
                "population_known_share": g["population_known"].astype(bool).mean(),
                "country_population_shares": by_country.to_dict(),
                "examples_by_population": examples,
            }
        )
    return pd.DataFrame(rows)


def label_rule(rel: float) -> str:
    if rel < 0.5:
        return "fights (too flat)"
    if rel < 0.75:
        return "compensate (flatter)"
    if rel <= 1.25:
        return "works"
    if rel <= 1.5:
        return "compensate (sharper)"
    return "too sharp"


def matching_table(summary: pd.DataFrame, cations: CationParams = CATIONS) -> pd.DataFrame:
    """Regime × roast: relative residual acidity at the regime median water (central, low, high)."""
    rows = []
    for _, reg in summary.iterrows():
        for r in ROASTS:
            grid = Grid(
                alkalinity_mgl=np.array([reg["alkalinity_median"]]),
                hardness_mgl=np.array([reg["hardness_median"]]),
            )
            central = float(relative_residual(r, grid, cations, REF_ALK, REF_HARD, "central")[0, 0])
            low = float(relative_residual(r, grid, cations, REF_ALK, REF_HARD, "low")[0, 0])
            high = float(relative_residual(r, grid, cations, REF_ALK, REF_HARD, "high")[0, 0])
            # Range across the regime's own alkalinity spread (p10 to p90) at central parameters.
            g_lo = Grid(
                alkalinity_mgl=np.array([reg["alkalinity_p10"]]), hardness_mgl=grid.hardness_mgl
            )
            g_hi = Grid(
                alkalinity_mgl=np.array([reg["alkalinity_p90"]]), hardness_mgl=grid.hardness_mgl
            )
            at_p10 = float(relative_residual(r, g_lo, cations, REF_ALK, REF_HARD, "central")[0, 0])
            at_p90 = float(relative_residual(r, g_hi, cations, REF_ALK, REF_HARD, "central")[0, 0])
            rows.append(
                {
                    "regime": reg["regime"],
                    "regime_name": reg["name"],
                    "roast": r.name,
                    "relative_residual_central": central,
                    "relative_residual_param_low": min(low, high),
                    "relative_residual_param_high": max(low, high),
                    "relative_residual_at_regime_p10_alk": at_p10,
                    "relative_residual_at_regime_p90_alk": at_p90,
                    "label": label_rule(central),
                    "label_stable_across_params": label_rule(low)
                    == label_rule(high)
                    == label_rule(central),
                }
            )
    return pd.DataFrame(rows)


def build_regimes(
    wide: pd.DataFrame, out_dir: Path
) -> tuple[RegimeModel, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    d = clustering_frame(wide)
    model, labels = fit_regimes(d)
    summary = regime_summary(d, labels, model)
    match = matching_table(summary)
    out_dir.mkdir(parents=True, exist_ok=True)
    model.to_json(out_dir / "regimes_v0_model.json")
    d.assign(regime=labels)[
        [
            "source_id",
            "country_iso2",
            "admin1",
            "locality_key",
            "locality",
            "alk",
            "hard",
            "alkalinity_imputed",
            "weight",
            "population_known",
            "regime",
        ]
    ].to_parquet(out_dir / "regimes_v0_localities.parquet", index=False)
    summary.to_csv(out_dir / "regimes_v0_summary.csv", index=False)
    match.to_csv(out_dir / "matching_v0.csv", index=False)
    return model, d.assign(regime=labels), summary, match
