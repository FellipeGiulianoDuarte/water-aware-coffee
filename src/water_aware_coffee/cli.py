"""Command-line entry point. Subcommands are added as the pipeline grows."""

from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(prog="wac", description="Water-aware coffee tools.")
    parser.add_subparsers(dest="command")
    args = parser.parse_args()
    if args.command is None:
        parser.print_help()


if __name__ == "__main__":
    main()
