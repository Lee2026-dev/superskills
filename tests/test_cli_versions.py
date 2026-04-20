from __future__ import annotations

from pathlib import Path

import pytest

from skills_inventory import cli, git_ops


def _make_skill(home: Path, name: str = "brainstorming") -> Path:
    skill = home / ".agents" / "skills" / name
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# skill\n", encoding="utf-8")
    return skill


def test_list_versions_prints_sorted_semver_and_marks_current(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys):
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    _make_skill(home)

    monkeypatch.setattr(cli.git_ops, "is_git_repo", lambda *_: True)
    monkeypatch.setattr(cli.git_ops, "fetch_tags", lambda *_: None)
    monkeypatch.setattr(cli.git_ops, "list_tags", lambda *_: ["v1.2.0", "foo", "1.10.0", "1.2.3"])
    monkeypatch.setattr(cli.git_ops, "tags_pointing_at_head", lambda *_: ["v1.2.0"])

    rc = cli.main(["list-versions", "brainstorming"])

    assert rc == 0
    out = capsys.readouterr().out
    lines = [line for line in out.splitlines() if line.strip()]
    assert lines == ["  1.10.0", "  1.2.3", "* 1.2.0"]


def test_list_versions_returns_non_zero_with_clear_error_when_target_not_found(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys
):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    rc = cli.main(["list-versions", "brainstorming"])

    assert rc != 0
    out = capsys.readouterr().out
    assert "error:" in out
    assert "skill not found" in out


def test_upgrade_latest_checks_clean_fetches_and_checks_out(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys):
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    _make_skill(home)

    called: dict[str, str] = {}

    monkeypatch.setattr(cli.git_ops, "is_git_repo", lambda *_: True)
    monkeypatch.setattr(cli.git_ops, "is_worktree_clean", lambda *_: True)
    monkeypatch.setattr(cli.git_ops, "fetch_tags", lambda *_: None)
    monkeypatch.setattr(cli.git_ops, "list_tags", lambda *_: ["v1.2.0", "1.10.0", "1.2.3"])
    monkeypatch.setattr(cli.git_ops, "tags_pointing_at_head", lambda *_: ["v1.2.0"])

    def fake_checkout(_repo: Path, tag: str) -> None:
        called["tag"] = tag

    monkeypatch.setattr(cli.git_ops, "checkout_tag", fake_checkout)
    monkeypatch.setattr(cli.git_ops, "head_commit", lambda *_: "abc1234")

    rc = cli.main(["upgrade", "brainstorming", "--latest"])

    assert rc == 0
    assert called["tag"] == "1.10.0"
    out = capsys.readouterr().out
    assert "upgraded brainstorming: 1.2.0 -> 1.10.0 (abc1234)" in out


def test_upgrade_refuses_dirty_worktree(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys):
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    _make_skill(home)

    monkeypatch.setattr(cli.git_ops, "is_git_repo", lambda *_: True)
    monkeypatch.setattr(cli.git_ops, "is_worktree_clean", lambda *_: False)

    rc = cli.main(["upgrade", "brainstorming", "--latest"])

    assert rc != 0
    out = capsys.readouterr().out
    assert "error: working tree is dirty" in out


def test_upgrade_to_tag_requires_existing_semver_tag(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys):
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    _make_skill(home)

    monkeypatch.setattr(cli.git_ops, "is_git_repo", lambda *_: True)
    monkeypatch.setattr(cli.git_ops, "is_worktree_clean", lambda *_: True)
    monkeypatch.setattr(cli.git_ops, "fetch_tags", lambda *_: None)
    monkeypatch.setattr(cli.git_ops, "list_tags", lambda *_: ["v1.2.0", "1.3.0"])

    rc = cli.main(["upgrade", "brainstorming", "--to", "1.4.0"])

    assert rc != 0
    out = capsys.readouterr().out
    assert "error: tag not found: 1.4.0" in out


def test_upgrade_returns_zero_without_checkout_when_already_on_target(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys
):
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    _make_skill(home)

    called = {"checkout": 0}

    monkeypatch.setattr(cli.git_ops, "is_git_repo", lambda *_: True)
    monkeypatch.setattr(cli.git_ops, "is_worktree_clean", lambda *_: True)
    monkeypatch.setattr(cli.git_ops, "fetch_tags", lambda *_: None)
    monkeypatch.setattr(cli.git_ops, "list_tags", lambda *_: ["v1.2.0", "1.3.0"])
    monkeypatch.setattr(cli.git_ops, "tags_pointing_at_head", lambda *_: ["1.3.0"])

    def fake_checkout(*_args, **_kwargs):
        called["checkout"] += 1

    monkeypatch.setattr(cli.git_ops, "checkout_tag", fake_checkout)

    rc = cli.main(["upgrade", "brainstorming", "--to", "v1.3.0"])

    assert rc == 0
    assert called["checkout"] == 0
    out = capsys.readouterr().out
    assert "already at 1.3.0" in out


def test_upgrade_with_missing_mode_is_non_zero(tmp_path: Path):
    home = tmp_path / "home"
    _make_skill(home)

    with pytest.raises(SystemExit) as exc:
        cli.main(["upgrade", "brainstorming"])

    assert exc.value.code != 0


def test_list_versions_returns_non_zero_for_non_git_repo(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys):
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    _make_skill(home)

    monkeypatch.setattr(cli.git_ops, "is_git_repo", lambda *_: False)

    rc = cli.main(["list-versions", "brainstorming"])

    assert rc != 0
    out = capsys.readouterr().out
    assert "error: not a git repository" in out


def test_clear_error_when_git_command_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys):
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    _make_skill(home)

    monkeypatch.setattr(cli.git_ops, "is_git_repo", lambda *_: True)
    monkeypatch.setattr(
        cli.git_ops,
        "fetch_tags",
        lambda *_: (_ for _ in ()).throw(git_ops.GitCommandError("fetch failed")),
    )

    rc = cli.main(["list-versions", "brainstorming"])

    assert rc != 0
    out = capsys.readouterr().out
    assert "error: fetch failed" in out
