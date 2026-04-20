"""API handler functions for the dashboard HTTP server."""
from __future__ import annotations

import json
import os
import shutil
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .. import git_ops
from ..cache import CacheManager
from ..models import scan_result_to_dict
from ..scanner import scan_roots
from ..targets import TargetResolutionError, resolve_skill_target
from ..versions import highest_tag, normalize_tag, parse_semver, sort_semver_tags_desc

# ── In-memory operation log ───────────────────────────────────────────────────

_log: list[dict] = []


def get_log() -> list[dict]:
    return list(_log)


def _log_op(action: str, detail: dict) -> None:
    _log.append(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            **detail,
        }
    )


# ── Response helpers ──────────────────────────────────────────────────────────


def ok(data: Any) -> bytes:
    return json.dumps({"ok": True, "data": data}, ensure_ascii=False).encode()


def err(message: str, code: str) -> tuple[bytes, int]:
    """Return (body_bytes, http_status)."""
    status_map = {
        "NOT_GIT_REPO": 400,
        "DIRTY_WORKTREE": 409,
        "TAG_NOT_FOUND": 404,
        "NO_SEMVER_TAGS": 404,
        "ALREADY_CURRENT": 200,
        "PATH_NOT_ALLOWED": 403,
        "NOT_A_SKILL": 400,
        "GIT_ERROR": 500,
        "BAD_REQUEST": 400,
        "NOT_FOUND": 404,
    }
    body = json.dumps({"ok": False, "error": message, "code": code}, ensure_ascii=False).encode()
    return body, status_map.get(code, 500)


# ── Shared helpers ────────────────────────────────────────────────────────────


def _semver_tags_by_normalized(tags: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for tag in tags:
        if parse_semver(tag) is None:
            continue
        normalized = normalize_tag(tag)
        if normalized not in mapping:
            mapping[normalized] = tag
    return mapping


def _resolve_target(name: str, path: str | None, scan_roots_paths: list[Path]) -> Path | None:
    try:
        return resolve_skill_target(name, path, scan_roots_paths)
    except TargetResolutionError:
        return None


def _is_under_scan_roots(path: Path, scan_root_paths: list[Path]) -> bool:
    resolved = path.resolve()
    for root in scan_root_paths:
        root_resolved = root.expanduser().resolve()
        try:
            resolved.relative_to(root_resolved)
            return True
        except ValueError:
            continue
    return False


# ── Handler: scan ─────────────────────────────────────────────────────────────


def handle_scan(scan_root_paths: list[Path], refresh: bool = False, fast_mode: bool = False) -> tuple[bytes, int]:
    cache = CacheManager()
    result = scan_roots(scan_root_paths, cache_manager=cache, refresh=refresh, fast_mode=fast_mode)
    cache.save()
    data = scan_result_to_dict(
        result,
        scan_roots=[str(p.expanduser().resolve()) for p in scan_root_paths],
    )
    return ok(data), 200


# ── Handler: versions ─────────────────────────────────────────────────────────


def handle_versions(name: str, path: str | None, scan_root_paths: list[Path]) -> tuple[bytes, int]:
    target = _resolve_target(name, path, scan_root_paths)
    if target is None:
        body, status = err(f"skill not found: {name}", "NOT_FOUND")
        return body, status

    if not git_ops.is_git_repo(target):
        body, status = err(f"not a git repository: {target}", "NOT_GIT_REPO")
        return body, status

    try:
        git_ops.fetch_tags(target)
        all_tags = git_ops.list_tags(target)
        ordered = sort_semver_tags_desc(all_tags)
        current_set = {
            normalize_tag(t)
            for t in git_ops.tags_pointing_at_head(target)
            if parse_semver(t) is not None
        }
    except git_ops.GitCommandError as exc:
        body, status = err(str(exc), "GIT_ERROR")
        return body, status

    versions = [
        {"version": normalize_tag(t), "current": normalize_tag(t) in current_set}
        for t in ordered
    ]
    return ok({"name": name, "path": str(target), "versions": versions}), 200


# ── Handler: upgrade ──────────────────────────────────────────────────────────


def handle_upgrade(body: dict, scan_root_paths: list[Path]) -> tuple[bytes, int]:
    name = body.get("name")
    path = body.get("path")
    to_tag = body.get("to")
    use_latest = body.get("latest", False)

    if not name:
        return err("'name' is required", "BAD_REQUEST")
    if not to_tag and not use_latest:
        return err("either 'to' or 'latest' must be set", "BAD_REQUEST")

    target = _resolve_target(name, path, scan_root_paths)
    if target is None:
        return err(f"skill not found: {name}", "NOT_FOUND")

    if not git_ops.is_git_repo(target):
        return err(f"not a git repository: {target}", "NOT_GIT_REPO")

    try:
        if not git_ops.is_worktree_clean(target):
            return err(f"working tree is dirty: {target}", "DIRTY_WORKTREE")

        git_ops.fetch_tags(target)
        tags = git_ops.list_tags(target)
        semver_map = _semver_tags_by_normalized(tags)
        if not semver_map:
            return err("no valid semver tags found", "NO_SEMVER_TAGS")

        if to_tag:
            target_version = normalize_tag(to_tag)
            checkout_ref = semver_map.get(target_version)
            if checkout_ref is None:
                return err(f"tag not found: {to_tag}", "TAG_NOT_FOUND")
        else:
            latest = highest_tag(list(semver_map.values()))
            if latest is None:
                return err("no valid semver tags found", "NO_SEMVER_TAGS")
            target_version = latest
            checkout_ref = semver_map[target_version]

        current_versions = [
            normalize_tag(t)
            for t in git_ops.tags_pointing_at_head(target)
            if parse_semver(t) is not None
        ]
        current = current_versions[0] if current_versions else "unknown"

        if current == target_version:
            return ok({"name": name, "message": f"already at {target_version}", "code": "ALREADY_CURRENT"}), 200

        git_ops.checkout_tag(target, checkout_ref)
        commit = git_ops.head_commit(target)

    except git_ops.GitCommandError as exc:
        return err(str(exc), "GIT_ERROR")

    _log_op("upgrade", {"name": name, "path": str(target), "from": current, "to": target_version, "commit": commit})
    return ok({"name": name, "from": current, "to": target_version, "commit": commit}), 200


# ── Handler: conflict resolve ─────────────────────────────────────────────────


def handle_resolve(body: dict, scan_root_paths: list[Path]) -> tuple[bytes, int]:
    keep_path_str = body.get("keep_path")
    remove_path_str = body.get("remove_path")
    create_symlink = body.get("symlink", False)

    if not keep_path_str or not remove_path_str:
        return err("'keep_path' and 'remove_path' are required", "BAD_REQUEST")

    remove_path = Path(remove_path_str).expanduser().resolve()
    keep_path = Path(keep_path_str).expanduser().resolve()

    # Safety constraint 1: must be under a scan root
    if not _is_under_scan_roots(remove_path, scan_root_paths):
        return err(f"path is not under a known scan root: {remove_path}", "PATH_NOT_ALLOWED")

    # Safety constraint 2: must contain SKILL.md
    if not (remove_path / "SKILL.md").is_file():
        return err(f"path does not contain SKILL.md: {remove_path}", "NOT_A_SKILL")

    # Safety constraint 3: dirty worktree
    if git_ops.is_git_repo(remove_path):
        try:
            if not git_ops.is_worktree_clean(remove_path):
                return err(f"working tree is dirty: {remove_path}", "DIRTY_WORKTREE")
        except git_ops.GitCommandError as exc:
            return err(str(exc), "GIT_ERROR")

    try:
        shutil.rmtree(remove_path)
    except OSError as exc:
        return err(f"failed to remove directory: {exc}", "GIT_ERROR")

    # Symlink creation
    symlink_created = False
    if create_symlink:
        try:
            os.symlink(str(keep_path), str(remove_path))
            symlink_created = True
        except OSError as exc:
            return err(f"failed to create symbolic link: {exc}", "GIT_ERROR")

    _log_op("resolve", {"removed": str(remove_path), "kept": str(keep_path), "symlink": symlink_created})
    return ok({"removed": str(remove_path), "kept": str(keep_path), "symlink": symlink_created}), 200
