from __future__ import annotations

import argparse
import webbrowser
from pathlib import Path

from . import git_ops
from .cache import CacheManager
from .output import print_summary, write_json
from .scanner import scan_roots
from .targets import TargetResolutionError, resolve_skill_target
from .versions import highest_tag, normalize_tag, parse_semver, sort_semver_tags_desc

DEFAULT_SCAN_ROOTS = [
    Path("~/.codex"),
    Path("~/.agents"),
    Path("~/.skills"),
    Path("~/.gemini"),
    Path("~/.hermes"),
    Path("~/.openclaw"),
]
DEFAULT_OUTPUT = Path("~/.agents/superskills.json")
DEFAULT_SERVE_PORT = 8080
DEFAULT_SERVE_HOST = "127.0.0.1"


def _resolve_target_or_error(name: str, path: str | None) -> Path | None:
    try:
        return resolve_skill_target(name, path, DEFAULT_SCAN_ROOTS)
    except TargetResolutionError as exc:
        print(f"error: {exc}")
        return None


def _semver_tags_by_normalized(tags: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for tag in tags:
        if parse_semver(tag) is None:
            continue
        normalized = normalize_tag(tag)
        if normalized not in mapping:
            mapping[normalized] = tag
    return mapping


def _handle_list_versions(args: argparse.Namespace) -> int:
    target = _resolve_target_or_error(args.name, args.path)
    if target is None:
        return 2

    if not git_ops.is_git_repo(target):
        print(f"error: not a git repository: {target}")
        return 2

    try:
        git_ops.fetch_tags(target)
        ordered = sort_semver_tags_desc(git_ops.list_tags(target))
        if not ordered:
            print("error: no valid semver tags found")
            return 2

        current = {
            normalize_tag(tag)
            for tag in git_ops.tags_pointing_at_head(target)
            if parse_semver(tag) is not None
        }
    except (git_ops.GitCommandError, ValueError) as exc:
        print(f"error: {exc}")
        return 2

    for tag in ordered:
        normalized = normalize_tag(tag)
        marker = "*" if normalized in current else " "
        print(f"{marker} {normalized}")
    return 0


def _handle_upgrade(args: argparse.Namespace) -> int:
    target = _resolve_target_or_error(args.name, args.path)
    if target is None:
        return 2

    if not git_ops.is_git_repo(target):
        print(f"error: not a git repository: {target}")
        return 2

    try:
        if not git_ops.is_worktree_clean(target):
            print(f"error: working tree is dirty: {target}")
            return 2

        git_ops.fetch_tags(target)
        tags = git_ops.list_tags(target)
        semver_tag_map = _semver_tags_by_normalized(tags)
        if not semver_tag_map:
            print("error: no valid semver tags found")
            return 2

        if args.to:
            target_version = normalize_tag(args.to)
            checkout_ref = semver_tag_map.get(target_version)
            if checkout_ref is None:
                print(f"error: tag not found: {args.to}")
                return 2
        else:
            latest = highest_tag(list(semver_tag_map.values()))
            if latest is None:
                print("error: no valid semver tags found")
                return 2
            target_version = latest
            checkout_ref = semver_tag_map[target_version]

        current_versions = [
            normalize_tag(tag)
            for tag in git_ops.tags_pointing_at_head(target)
            if parse_semver(tag) is not None
        ]
        current = current_versions[0] if current_versions else "unknown"
        if current == target_version:
            print(f"already at {target_version}")
            return 0

        git_ops.checkout_tag(target, checkout_ref)
        commit = git_ops.head_commit(target)
    except (git_ops.GitCommandError, ValueError) as exc:
        print(f"error: {exc}")
        return 2

    print(f"upgraded {args.name}: {current} -> {target_version} ({commit})")
    return 0


def _handle_scan(args: argparse.Namespace) -> int:
    roots = [Path(r) for r in args.root] if args.root else DEFAULT_SCAN_ROOTS
    cache = CacheManager()
    result = scan_roots(roots, cache_manager=cache, refresh=args.refresh)
    cache.save()
    print_summary(result)

    if args.json:
        output_path = DEFAULT_OUTPUT.expanduser()
        try:
            write_json(
                result,
                output_path=output_path,
                scan_roots=[str(path.expanduser().resolve()) for path in roots],
            )
        except OSError as exc:
            print(f"error: cannot write inventory json to {output_path}: {exc}")
            return 2
    return 0


def _handle_serve(args: argparse.Namespace) -> int:
    from .web.server import serve

    host = args.host
    port = args.port
    url = f"http://{host}:{port}"

    print(f"SuperSkills Dashboard running at {url}")
    print("Press Ctrl+C to stop.")

    if not args.no_open:
        webbrowser.open(url)

    httpd = serve(DEFAULT_SCAN_ROOTS, host=host, port=port, refresh=args.refresh)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard stopped.")
    finally:
        httpd.server_close()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="skills-inventory")
    subparsers = parser.add_subparsers(dest="command", required=True)

    args_scan = subparsers.add_parser("scan")
    args_scan.add_argument("--root", action="append", help="Root directory to scan (can be repeated)")
    args_scan.add_argument("--json", action="store_true", help="Output full inventory as JSON")
    args_scan.add_argument("--refresh", action="store_true", help="Force rescan (bypass cache)")

    list_versions_parser = subparsers.add_parser("list-versions")
    list_versions_parser.add_argument("name")
    list_versions_parser.add_argument("--path")

    upgrade_parser = subparsers.add_parser("upgrade")
    upgrade_parser.add_argument("name")
    upgrade_parser.add_argument("--path")
    mode = upgrade_parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--to")
    mode.add_argument("--latest", action="store_true")

    args_serve = subparsers.add_parser("serve", help="Start the browser dashboard")
    args_serve.add_argument("--port", type=int, default=DEFAULT_SERVE_PORT)
    args_serve.add_argument("--host", default=DEFAULT_SERVE_HOST)
    args_serve.add_argument("--no-open", action="store_true", help="Don't open browser automatically")
    args_serve.add_argument("--refresh", action="store_true", help="Force initial scan to bypass cache")

    args = parser.parse_args(argv)

    if args.command == "scan":
        return _handle_scan(args)

    if args.command == "list-versions":
        return _handle_list_versions(args)

    if args.command == "upgrade":
        return _handle_upgrade(args)

    if args.command == "serve":
        return _handle_serve(args)

    return 1


def run() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    run()
