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


def cmd_bands(_: argparse.Namespace) -> None:
    import pandas as pd

    from water_aware_coffee.atlas.bands import build_bands, edge_acid_loss

    out_dir = INTERIM_DIR.parent / "processed"
    wide = pd.read_parquet(out_dir / "atlas_v0_wide.parquet")
    d, summary, match = build_bands(wide, out_dir)
    pd.set_option("display.width", 200)
    print(f"bands v0: {len(d):,} localities")
    print(edge_acid_loss().round(3).to_string(index=False))
    print(
        summary[
            [
                "band",
                "name",
                "localities",
                "population_share",
                "population_share_measured_only",
                "alkalinity_median",
                "hardness_median",
                "share_softened",
                "share_imputed_alkalinity",
            ]
        ]
        .round(3)
        .to_string(index=False)
    )
    print(
        match[
            [
                "band",
                "roast",
                "relative_residual_at_median",
                "relative_residual_at_upper_edge",
                "label_at_median",
                "label_at_upper_edge",
            ]
        ]
        .round(2)
        .to_string(index=False)
    )


def cmd_dialin(args: argparse.Namespace) -> None:
    from water_aware_coffee.model.params import ROASTS
    from water_aware_coffee.model.sensory import AdditiveSensory, dial_in

    sens = AdditiveSensory.from_frost_csv()
    roast = next(r for r in ROASTS if r.name == args.roast)
    d = dial_in(args.alkalinity, roast, sens)
    print(f"{roast.name} roast in water with alkalinity {args.alkalinity:g} mg/L as CaCO3")
    print(f"  acid neutralised vs reference (40 mg/L): {d.acid_neutralised_meq:+.2f} meq/L")
    print(f"  predicted sourness change: {d.sourness_change_points:+.1f} points (0 to 100 scale)")
    print(
        f"  strength route: TDS {d.tds_delta_percent:+.2f} to {d.tds_delta_percent_sensory:+.2f} %"
        f" (dose {100 * d.dose_change_fraction:+.0f} to"
        f" {100 * d.dose_change_fraction_sensory:+.0f} %),"
        " chemistry to sensory estimate; side effects at the chemistry value: "
        + ", ".join(f"{k} {v:+.1f}" for k, v in d.side_effects_tds_route.items())
    )
    print(
        f"  extraction route: PE {d.pe_delta_percent:+.1f} %; side effects: "
        + ", ".join(f"{k} {v:+.1f}" for k, v in d.side_effects_pe_route.items())
    )
    print(
        f"  dilution route: blend {100 * d.dilution_fraction_zero_alk_water:.0f} % zero-alkalinity "
        "water (distilled / reverse osmosis / near-zero-bicarbonate bottled) to reach 40 mg/L"
    )
    print(f"  {d.note}")


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
    p_bands = sub.add_parser(
        "bands", help="Task 4 (decision 29): fixed alkalinity bands + matching table"
    )
    p_bands.set_defaults(func=cmd_bands)
    p_dial = sub.add_parser("dialin", help="Task 5: compensation for a water alkalinity and roast")
    p_dial.add_argument("--alkalinity", type=float, required=True, help="mg/L as CaCO3")
    p_dial.add_argument("--roast", choices=["light", "medium", "dark"], default="medium")
    p_dial.set_defaults(func=cmd_dialin)
    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
