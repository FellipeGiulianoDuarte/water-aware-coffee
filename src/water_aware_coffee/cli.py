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


def main() -> None:
    parser = argparse.ArgumentParser(prog="wac", description="Water-aware coffee tools.")
    sub = parser.add_subparsers(dest="command")
    p_sources = sub.add_parser("sources", help="list registered sources")
    p_sources.set_defaults(func=cmd_sources)
    p_build = sub.add_parser("build", help="build interim measurement tables")
    p_build.add_argument("source_id", nargs="*")
    p_build.add_argument("--all", action="store_true")
    p_build.set_defaults(func=cmd_build)
    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
