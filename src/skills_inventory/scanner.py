from __future__ import annotations

from datetime import datetime
from pathlib import Path
import hashlib
import time

from .models import ScanResult, SkillRecord

DEFAULT_IGNORED_DIRS = {".git", "node_modules", "__pycache__", ".venv"}


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"


def _file_mtime_iso(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat()


def scan_roots(
    roots: list[Path],
    recursive: bool = True,
    follow_symlinks: bool = True,
    ignored_dirs: set[str] | None = None,
) -> ScanResult:
    ignored = ignored_dirs or DEFAULT_IGNORED_DIRS
    start = time.monotonic()
    result = ScanResult()

    for root in roots:
        root_path = root.expanduser().resolve()
        if not root_path.exists():
            result.warnings.append(f"Root does not exist: {root_path}")
            continue

        stack = [root_path]
        while stack:
            current = stack.pop()
            result.summary.scanned_dirs += 1
            if current.name in ignored:
                continue

            skill_md = current / "SKILL.md"
            if skill_md.is_file():
                result.skills.append(
                    SkillRecord(
                        name=current.name,
                        path=str(current.resolve()),
                        source_root=str(root_path),
                        skill_md_path=str(skill_md.resolve()),
                        last_modified=_file_mtime_iso(skill_md),
                        skill_md_hash=_file_hash(skill_md),
                    )
                )

            if not recursive:
                continue

            for child in current.iterdir():
                if child.is_dir() and (follow_symlinks or not child.is_symlink()):
                    stack.append(child)

    result.summary.total_skills = len(result.skills)
    result.summary.duration_ms = int((time.monotonic() - start) * 1000)
    return result
