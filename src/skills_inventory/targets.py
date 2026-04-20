from __future__ import annotations

from pathlib import Path


class TargetResolutionError(RuntimeError):
    pass


def _find_matches(name: str, roots: list[Path]) -> list[Path]:
    matches: list[Path] = []
    for root in roots:
        root_path = root.expanduser().resolve()
        if not root_path.exists():
            continue
        for candidate in root_path.rglob(name):
            if candidate.name != name or not candidate.is_dir():
                continue
            if not (candidate / "SKILL.md").is_file():
                continue
            matches.append(candidate.resolve())
    return sorted(set(matches), key=str)


def resolve_skill_target(name: str, path: str | None, roots: list[Path]) -> Path:
    if path is not None:
        candidate = Path(path).expanduser()
        if not candidate.is_absolute():
            raise TargetResolutionError("--path must be absolute")
        if candidate.name != name:
            raise TargetResolutionError("--path directory name must match <name>")
        if not (candidate / "SKILL.md").is_file():
            raise TargetResolutionError("--path must point to a skill directory containing SKILL.md")
        return candidate.resolve()

    matches = _find_matches(name, roots)
    if not matches:
        raise TargetResolutionError(f"skill not found: {name}")
    if len(matches) > 1:
        lines = "\n".join(str(item) for item in matches)
        raise TargetResolutionError(f"ambiguous skill name '{name}', provide --path:\n{lines}")
    return matches[0]
