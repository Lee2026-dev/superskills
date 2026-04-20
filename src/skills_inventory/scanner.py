from __future__ import annotations

from datetime import datetime
from pathlib import Path
import hashlib
import time
from collections import defaultdict

from .models import ConflictRecord, ScanResult, SkillRecord

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
    visited: set[tuple[int, int]] = set()

    for root in roots:
        root_path = root.expanduser().resolve()
        if not root_path.exists():
            result.warnings.append(f"Root does not exist: {root_path}")
            continue

        stack = [root_path]
        while stack:
            current = stack.pop()
            try:
                stat_info = current.stat()
            except OSError as exc:
                result.warnings.append(f"Cannot stat directory: {current} ({exc})")
                continue

            identity = (stat_info.st_dev, stat_info.st_ino)
            if identity in visited:
                continue
            visited.add(identity)

            result.summary.scanned_dirs += 1
            if current.name in ignored:
                continue

            skill_md = current / "SKILL.md"
            if skill_md.is_file():
                error_text = None
                last_modified = ""
                skill_hash = ""
                try:
                    last_modified = _file_mtime_iso(skill_md)
                    skill_hash = _file_hash(skill_md)
                except OSError as exc:
                    error_text = f"metadata_error: {exc}"

                result.skills.append(
                    SkillRecord(
                        name=current.name,
                        path=str(current.resolve()),
                        source_root=str(root_path),
                        skill_md_path=str(skill_md.resolve()),
                        last_modified=last_modified,
                        skill_md_hash=skill_hash,
                        error=error_text,
                    )
                )

            if not recursive:
                continue

            try:
                children = list(current.iterdir())
            except OSError as exc:
                result.warnings.append(f"Cannot list directory: {current} ({exc})")
                continue

            for child in children:
                if child.name in ignored:
                    continue
                if child.is_symlink() and not follow_symlinks:
                    continue
                if child.is_dir():
                    stack.append(child)

    result.summary.total_skills = len(result.skills)
    by_name: dict[str, list[SkillRecord]] = defaultdict(list)
    for skill in result.skills:
        by_name[skill.name].append(skill)

    for name, records in sorted(by_name.items()):
        if len(records) > 1:
            result.summary.conflict_names += 1
            for record in records:
                record.has_conflict = True
            result.conflicts.append(
                ConflictRecord(
                    name=name,
                    count=len(records),
                    paths=[record.path for record in records],
                )
            )

    result.summary.duration_ms = int((time.monotonic() - start) * 1000)
    return result
