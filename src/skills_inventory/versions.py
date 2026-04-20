from __future__ import annotations

import re

_CORE_SEMVER_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


def parse_semver(tag: str) -> tuple[int, int, int] | None:
    match = _CORE_SEMVER_RE.fullmatch(tag)
    if match is None:
        return None

    major, minor, patch = match.groups()
    return (int(major), int(minor), int(patch))


def normalize_tag(tag: str) -> str:
    parsed = parse_semver(tag)
    if parsed is None:
        raise ValueError(f"invalid semver tag: {tag}")

    return f"{parsed[0]}.{parsed[1]}.{parsed[2]}"


def sort_semver_tags_desc(tags: list[str]) -> list[str]:
    valid = [tag for tag in tags if parse_semver(tag) is not None]
    return sorted(valid, key=lambda tag: parse_semver(tag), reverse=True)


def highest_tag(tags: list[str]) -> str | None:
    ordered = sort_semver_tags_desc(tags)
    if not ordered:
        return None

    return normalize_tag(ordered[0])
