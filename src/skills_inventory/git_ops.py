from __future__ import annotations

from pathlib import Path
import subprocess


class GitCommandError(RuntimeError):
    """Raised when a git command exits with a non-zero code."""


def _run_git(repo_path: Path, args: list[str]) -> str:
    cmd = ["git", "-C", str(repo_path), *args]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        message = proc.stderr.strip() or proc.stdout.strip() or "git command failed"
        raise GitCommandError(message)
    return proc.stdout


def is_git_repo(repo_path: Path) -> bool:
    try:
        out = _run_git(repo_path, ["rev-parse", "--is-inside-work-tree"])
    except GitCommandError:
        return False
    return out.strip() == "true"


def fetch_tags(repo_path: Path) -> None:
    _run_git(repo_path, ["fetch", "--tags", "--prune", "--quiet"])


def list_tags(repo_path: Path) -> list[str]:
    out = _run_git(repo_path, ["tag", "--list"])
    return [line.strip() for line in out.splitlines() if line.strip()]


def tags_pointing_at_head(repo_path: Path) -> list[str]:
    out = _run_git(repo_path, ["tag", "--points-at", "HEAD"])
    return [line.strip() for line in out.splitlines() if line.strip()]


def is_worktree_clean(repo_path: Path) -> bool:
    out = _run_git(repo_path, ["status", "--porcelain"])
    return out.strip() == ""


def checkout_tag(repo_path: Path, tag: str) -> None:
    _run_git(repo_path, ["checkout", tag])


def head_commit(repo_path: Path) -> str:
    out = _run_git(repo_path, ["rev-parse", "--short", "HEAD"])
    return out.strip()
