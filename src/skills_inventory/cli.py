from __future__ import annotations

import argparse
from pathlib import Path

from .output import print_summary, write_json
from .scanner import scan_roots


DEFAULT_SCAN_ROOTS = [Path("~/.codex/skills"), Path("~/.agents/skills"), Path("~/skills")]
DEFAULT_OUTPUT = Path("~/.agents/superskills.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="skills-inventory")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("scan")
    args = parser.parse_args(argv)

    if args.command != "scan":
        return 1

    result = scan_roots(DEFAULT_SCAN_ROOTS)
    print_summary(result)

    output_path = DEFAULT_OUTPUT.expanduser()
    try:
        write_json(
            result,
            output_path=output_path,
            scan_roots=[str(path.expanduser().resolve()) for path in DEFAULT_SCAN_ROOTS],
        )
    except OSError as exc:
        print(f"error: cannot write inventory json to {output_path}: {exc}")
        return 2

    return 0


def run() -> None:
    raise SystemExit(main())
