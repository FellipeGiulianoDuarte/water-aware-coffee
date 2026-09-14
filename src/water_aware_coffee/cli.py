"""Command-line entry point.

wac build <source_id> [...]   read raw files, write data/interim/<source_id>.parquet
wac build --all
wac sources                   list registered source ids
"""

from __future__ import annotations

import argparse
import sys

from water_aware_coffee.sources import LOADERS, available
from water_aware_coffee.sources.base import INTERIM_DIR, RAW_DIR


def cmd_sources(_: argparse.Namespace) -> None:
    for s in available():
        print(s)


def cmd_build(args: argparse.Namespace) -> None:
    known = available()  # imports loader modules so LOADERS is populated
    ids = known if args.all else args.source_id
    if not ids:
        sys.exit("give one or more source ids, or --all")
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    for sid in ids:
        if sid not in LOADERS:
            sys.exit(f"unknown source {sid!r}; known: {', '.join(available())}")
        df = LOADERS[sid](RAW_DIR)
        out = INTERIM_DIR / f"{sid}.parquet"
        df.to_parquet(out, index=False)
        by_q = df.groupby("quantity").size().to_dict()
        print(f"{sid}: {len(df):,} rows -> {out.relative_to(INTERIM_DIR.parent.parent)} {by_q}")


def cmd_atlas(_: argparse.Namespace) -> None:
    from water_aware_coffee.atlas.aggregate import build_atlas_v0
    from water_aware_coffee.atlas.impute import fit_alkalinity, fit_report, impute_alkalinity
    from water_aware_coffee.atlas.population import attach_population, load_population

    out_dir = INTERIM_DIR.parent / "processed"
    long, wide = build_atlas_v0(INTERIM_DIR, out_dir)
    wide = attach_population(wide, load_population(RAW_DIR / "population"))
    pop_by = wide.groupby("source_id")["population"].apply(lambda s: int(s.notna().sum()))
    print(f"  population attached: {pop_by.to_dict()}")
    print(f"atlas v0: {len(long):,} locality×quantity rows, {len(wide):,} localities -> {out_dir}")
    for q in ("hardness", "alkalinity", "calcium", "magnesium"):
        col = f"{q}_median"
        if col in wide.columns:
            print(f"  {q}: {wide[col].notna().sum():,} localities")
    fit = fit_alkalinity(wide)
    report = fit_report(fit)
    (out_dir / "alkalinity_fit_v0.txt").write_text(report + "\n")
    imputed = impute_alkalinity(wide, fit)
    imputed.to_parquet(out_dir / "atlas_v0_wide.parquet", index=False)
    print(report)
    print(f"  imputed alkalinity for {int(imputed['alkalinity_imputed'].sum()):,} localities")


def cmd_regimes(_: argparse.Namespace) -> None:
    import pandas as pd

    from water_aware_coffee.atlas.regimes import build_regimes

    out_dir = INTERIM_DIR.parent / "processed"
    wide = pd.read_parquet(out_dir / "atlas_v0_wide.parquet")
    model, d, summary, match = build_regimes(wide, out_dir)
    print(
        f"regimes v0: k={model.k} from {len(d):,} localities; BIC by k: "
        + ", ".join(f"{k}:{v:,.0f}" for k, v in model.bic.items())
    )
    pd.set_option("display.width", 200)
    print(
        summary[
            [
                "regime",
                "name",
                "localities",
                "population_share",
                "alkalinity_median",
                "hardness_median",
                "share_imputed_alkalinity",
            ]
        ]
        .round(3)
        .to_string(index=False)
    )
    print(
        match[
            ["regime", "roast", "relative_residual_central", "label", "label_stable_across_params"]
        ]
        .round(2)
        .to_string(index=False)
    )


def main() -> None:
    parser = argparse.ArgumentParser(prog="wac", description="Water-aware coffee tools.")
    sub = parser.add_subparsers(dest="command")
    p_sources = sub.add_parser("sources", help="list registered sources")
    p_sources.set_defaults(func=cmd_sources)
    p_build = sub.add_parser("build", help="build interim measurement tables")
    p_build.add_argument("source_id", nargs="*")
    p_build.add_argument("--all", action="store_true")
    p_build.set_defaults(func=cmd_build)
    p_atlas = sub.add_parser("atlas", help="aggregate interim tables into per-locality atlas v0")
    p_atlas.set_defaults(func=cmd_atlas)
    p_reg = sub.add_parser(
        "regimes", help="cluster the atlas into water regimes and build the matching table"
    )
    p_reg.set_defaults(func=cmd_regimes)
    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
