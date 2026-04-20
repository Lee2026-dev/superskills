from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from skills_inventory import git_ops


def test_run_git_returns_stdout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    calls: list[list[str]] = []

    def fake_run(cmd, capture_output, text):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="ok\n", stderr="")

    monkeypatch.setattr(git_ops.subprocess, "run", fake_run)

    out = git_ops._run_git(tmp_path, ["status", "--porcelain"])

    assert out == "ok\n"
    assert calls == [["git", "-C", str(tmp_path), "status", "--porcelain"]]


def test_run_git_raises_git_command_error_with_stderr(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    def fake_run(cmd, capture_output, text):
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="fatal: not a git repo\n")

    monkeypatch.setattr(git_ops.subprocess, "run", fake_run)

    with pytest.raises(git_ops.GitCommandError, match="fatal: not a git repo"):
        git_ops._run_git(tmp_path, ["status"])


def test_run_git_raises_git_command_error_with_stdout_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    def fake_run(cmd, capture_output, text):
        return subprocess.CompletedProcess(cmd, 1, stdout="error from stdout\n", stderr="")

    monkeypatch.setattr(git_ops.subprocess, "run", fake_run)

    with pytest.raises(git_ops.GitCommandError, match="error from stdout"):
        git_ops._run_git(tmp_path, ["status"])


def test_is_git_repo_false_when_rev_parse_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    def fake_run(*args, **kwargs):
        raise git_ops.GitCommandError("rev-parse failed")

    monkeypatch.setattr(git_ops, "_run_git", fake_run)
    assert git_ops.is_git_repo(tmp_path) is False


def test_is_git_repo_true_when_rev_parse_returns_true(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setattr(git_ops, "_run_git", lambda *a, **k: "true\n")
    assert git_ops.is_git_repo(tmp_path) is True


def test_fetch_tags_invokes_expected_command(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    captured: list[tuple[Path, list[str]]] = []

    def fake_run(repo_path: Path, args: list[str]):
        captured.append((repo_path, args))
        return ""

    monkeypatch.setattr(git_ops, "_run_git", fake_run)

    git_ops.fetch_tags(tmp_path)

    assert captured == [(tmp_path, ["fetch", "--tags", "--prune", "--quiet"])]


def test_list_tags_returns_lines(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setattr(git_ops, "_run_git", lambda *a, **k: "v1.0.0\n1.2.0\n")
    assert git_ops.list_tags(tmp_path) == ["v1.0.0", "1.2.0"]


def test_tags_pointing_at_head_returns_lines(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setattr(git_ops, "_run_git", lambda *a, **k: "v1.0.0\n")
    assert git_ops.tags_pointing_at_head(tmp_path) == ["v1.0.0"]


def test_worktree_dirty_when_status_has_output(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setattr(git_ops, "_run_git", lambda *a, **k: " M SKILL.md\n")
    assert git_ops.is_worktree_clean(tmp_path) is False


def test_worktree_clean_when_status_empty(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setattr(git_ops, "_run_git", lambda *a, **k: "")
    assert git_ops.is_worktree_clean(tmp_path) is True


def test_checkout_tag_invokes_expected_command(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    captured: list[tuple[Path, list[str]]] = []

    def fake_run(repo_path: Path, args: list[str]):
        captured.append((repo_path, args))
        return ""

    monkeypatch.setattr(git_ops, "_run_git", fake_run)

    git_ops.checkout_tag(tmp_path, "v1.2.3")

    assert captured == [(tmp_path, ["checkout", "v1.2.3"])]


def test_head_commit_returns_trimmed_short_sha(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setattr(git_ops, "_run_git", lambda *a, **k: "abc1234\n")
    assert git_ops.head_commit(tmp_path) == "abc1234"
