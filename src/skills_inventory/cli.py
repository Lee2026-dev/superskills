from __future__ import annotations

import argparse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="skills-inventory")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("scan")
    args = parser.parse_args(argv)

    if args.command == "scan":
        return 0
    return 1


def run() -> None:
    raise SystemExit(main())
