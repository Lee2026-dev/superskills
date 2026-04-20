"""Unit tests for web/api.py handlers."""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from skills_inventory.web import api as web_api


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_skill(tmp_path):
    """Create a minimal skill directory with SKILL.md."""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# My Skill\n")
    return skill_dir


@pytest.fixture
def scan_roots(tmp_path):
    root = tmp_path / "skills_root"
    root.mkdir()
    return [root]


# ── ok / err helpers ──────────────────────────────────────────────────────────

def test_ok_returns_bytes():
    body = web_api.ok({"hello": "world"})
    payload = json.loads(body)
    assert payload["ok"] is True
    assert payload["data"]["hello"] == "world"


def test_err_returns_tuple():
    body, status = web_api.err("something went wrong", "NOT_GIT_REPO")
    payload = json.loads(body)
    assert payload["ok"] is False
    assert payload["code"] == "NOT_GIT_REPO"
    assert status == 400


def test_err_path_not_allowed():
    _, status = web_api.err("bad path", "PATH_NOT_ALLOWED")
    assert status == 403


# ── handle_scan ───────────────────────────────────────────────────────────────

def test_handle_scan_returns_ok(tmp_path, scan_roots):
    body, status = web_api.handle_scan(scan_roots)
    payload = json.loads(body)
    assert status == 200
    assert payload["ok"] is True
    assert "skills" in payload["data"]


# ── handle_versions ───────────────────────────────────────────────────────────

def test_handle_versions_not_found(scan_roots):
    body, status = web_api.handle_versions("nonexistent-skill", None, scan_roots)
    payload = json.loads(body)
    assert status == 404
    assert payload["code"] == "NOT_FOUND"


def test_handle_versions_not_git_repo(tmp_skill, scan_roots):
    # Move skill into scan root
    dest = scan_roots[0] / tmp_skill.name
    shutil.copytree(tmp_skill, dest)

    with patch("skills_inventory.web.api.git_ops.is_git_repo", return_value=False):
        body, status = web_api.handle_versions(tmp_skill.name, str(dest), scan_roots)

    payload = json.loads(body)
    assert status == 400
    assert payload["code"] == "NOT_GIT_REPO"


# ── handle_upgrade ────────────────────────────────────────────────────────────

def test_handle_upgrade_missing_name(scan_roots):
    body, status = web_api.handle_upgrade({}, scan_roots)
    payload = json.loads(body)
    assert payload["code"] == "BAD_REQUEST"


def test_handle_upgrade_missing_to_or_latest(scan_roots):
    body, status = web_api.handle_upgrade({"name": "foo"}, scan_roots)
    payload = json.loads(body)
    assert payload["code"] == "BAD_REQUEST"


def test_handle_upgrade_skill_not_found(scan_roots):
    body, status = web_api.handle_upgrade({"name": "ghost-skill", "latest": True}, scan_roots)
    payload = json.loads(body)
    assert payload["code"] == "NOT_FOUND"


# ── handle_resolve (safety constraints) ──────────────────────────────────────

def test_resolve_path_not_under_scan_root(tmp_path, scan_roots):
    outside = tmp_path / "outside" / "some-skill"
    outside.mkdir(parents=True)
    (outside / "SKILL.md").write_text("# Skill\n")

    body, status = web_api.handle_resolve(
        {"keep_path": "/some/keep", "remove_path": str(outside)},
        scan_roots,
    )
    payload = json.loads(body)
    assert status == 403
    assert payload["code"] == "PATH_NOT_ALLOWED"


def test_resolve_not_a_skill(scan_roots):
    # Put a directory under scan root with NO SKILL.md
    not_a_skill = scan_roots[0] / "not-a-skill"
    not_a_skill.mkdir()

    body, status = web_api.handle_resolve(
        {"keep_path": str(scan_roots[0] / "other"), "remove_path": str(not_a_skill)},
        scan_roots,
    )
    payload = json.loads(body)
    assert status == 400
    assert payload["code"] == "NOT_A_SKILL"


def test_resolve_dirty_worktree(scan_roots, tmp_skill):
    # Place skill inside scan root
    dest = scan_roots[0] / tmp_skill.name
    shutil.copytree(tmp_skill, dest)

    with (
        patch("skills_inventory.web.api.git_ops.is_git_repo", return_value=True),
        patch("skills_inventory.web.api.git_ops.is_worktree_clean", return_value=False),
    ):
        body, status = web_api.handle_resolve(
            {"keep_path": str(scan_roots[0] / "other"), "remove_path": str(dest)},
            scan_roots,
        )

    payload = json.loads(body)
    assert status == 409
    assert payload["code"] == "DIRTY_WORKTREE"


def test_resolve_success(scan_roots, tmp_skill):
    dest = scan_roots[0] / tmp_skill.name
    shutil.copytree(tmp_skill, dest)
    keep = scan_roots[0] / "keep-skill"

    with (
        patch("skills_inventory.web.api.git_ops.is_git_repo", return_value=False),
    ):
        body, status = web_api.handle_resolve(
            {"keep_path": str(keep), "remove_path": str(dest)},
            scan_roots,
        )

    payload = json.loads(body)
    assert status == 200
    assert payload["ok"] is True
    assert not dest.exists(), "remove_path should have been deleted"


# ── _is_under_scan_roots ──────────────────────────────────────────────────────

def test_is_under_scan_roots_positive(tmp_path):
    root = tmp_path / "r1"
    root.mkdir()
    child = root / "a" / "b"
    child.mkdir(parents=True)
    assert web_api._is_under_scan_roots(child, [root]) is True


def test_is_under_scan_roots_negative(tmp_path):
    root = tmp_path / "r1"
    root.mkdir()
    outside = tmp_path / "r2" / "x"
    outside.mkdir(parents=True)
    assert web_api._is_under_scan_roots(outside, [root]) is False
