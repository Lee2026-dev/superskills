from __future__ import annotations

from datetime import datetime
from pathlib import Path
import hashlib
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from . import git_ops
from .cache import CacheManager
from .models import ConflictRecord, ScanResult, SkillRecord
from .versions import highest_tag, normalize_tag, sort_semver_tags_desc

DEFAULT_IGNORED_DIRS = {".git", "node_modules", "__pycache__", ".venv"}


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"


def _file_mtime_iso(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat()


def _resolve_versions_for_skill(
    skill_path: Path, 
    warnings: list[str], 
    cache_manager: CacheManager | None = None,
    force_fetch: bool = False,
    fast_mode: bool = False,
) -> tuple[str, str]:
    if not git_ops.is_git_repo(skill_path):
        return ("unknown", "unknown")

    current_version = "unknown"
    latest_version = "unknown"
    
    # Check cache first for latest_version and last_fetch_ts
    path_key = str(skill_path.resolve())
    use_cache = False
    if cache_manager and not force_fetch:
        is_expired = cache_manager.is_git_fetch_expired(path_key)
        if not is_expired or fast_mode:
            entry = cache_manager.get(path_key)
            if entry and "latest_version" in entry:
                latest_version = entry["latest_version"]
                if not is_expired:
                    use_cache = True
                elif fast_mode:
                    use_cache = True # Skip network, even if expired

    try:
        if not use_cache and not fast_mode:
            git_ops.fetch_tags(skill_path)
    except git_ops.GitCommandError as exc:
        warnings.append(f"cannot fetch tags for {skill_path}: {exc}")
        return (current_version, latest_version)

    # We still list tags to get the most accurate latest_version if we fetched
    if not use_cache:
        tags = git_ops.list_tags(skill_path)
        latest = highest_tag(tags)
        if latest is not None:
            latest_version = latest
        
        # Update cache last_fetch_ts
        if cache_manager:
            entry = cache_manager.get(path_key) or {}
            entry["latest_version"] = latest_version
            if not fast_mode:
                entry["last_git_fetch_ts"] = time.time()
            cache_manager.set(path_key, entry)

    # current_version is always fast as it's local (points-at HEAD)
    try:
        for tag in sort_semver_tags_desc(git_ops.tags_pointing_at_head(skill_path)):
            current_version = normalize_tag(tag)
            break
    except git_ops.GitCommandError:
        pass

    return (current_version, latest_version)


def scan_roots(
    roots: list[Path],
    recursive: bool = True,
    follow_symlinks: bool = True,
    ignored_dirs: set[str] | None = None,
    cache_manager: CacheManager | None = None,
    refresh: bool = False,
    fast_mode: bool = False,
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
                        path=str(current),
                        source_root=str(root_path),
                        skill_md_path=str(skill_md),
                        last_modified=last_modified,
                        skill_md_hash=skill_hash,
                        is_symlink=current.is_symlink(),
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

    # ── Parallel Version Resolution ──────────────────────────────────────────
    def resolve_one(skill: SkillRecord) -> None:
        p = Path(skill.path)
        # Check cache for mtime/hash to potentially skip some git logic
        path_key = str(p.resolve())
        cached = cache_manager.get(path_key) if cache_manager else None
        
        if cached and not refresh:
            if cached.get("mtime") == skill.last_modified and cached.get("hash") == skill.skill_md_hash:
                # We can reuse everything if last_fetch_ts is still valid
                if not cache_manager.is_git_fetch_expired(path_key):
                    skill.current_version = cached.get("current_version", "unknown")
                    skill.latest_version = cached.get("latest_version", "unknown")
                    return
        
        cur, lat = _resolve_versions_for_skill(p, result.warnings, cache_manager, force_fetch=refresh, fast_mode=fast_mode)
        skill.current_version = cur
        skill.latest_version = lat
        
        if cache_manager:
            entry = cache_manager.get(path_key) or {}
            entry.update({
                "mtime": skill.last_modified,
                "hash": skill.skill_md_hash,
                "current_version": cur,
                "latest_version": lat,
            })
            cache_manager.set(path_key, entry)

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(resolve_one, result.skills))

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
