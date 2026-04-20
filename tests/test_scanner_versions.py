from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from skills_inventory import git_ops
import skills_inventory.scanner as scanner


def _make_skill(root: Path, name: str) -> Path:
    skill = root / name
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# skill\n", encoding="utf-8")
    return skill


def _patch_git_ops(
    monkeypatch: pytest.MonkeyPatch,
    *,
    is_git_repo,
    fetch_tags,
    list_tags,
    tags_pointing_at_head,
) -> None:
    fake = SimpleNamespace(
        GitCommandError=git_ops.GitCommandError,
        is_git_repo=is_git_repo,
        fetch_tags=fetch_tags,
        list_tags=list_tags,
        tags_pointing_at_head=tags_pointing_at_head,
    )
    monkeypatch.setattr(scanner, "git_ops", fake, raising=False)


def test_non_git_skill_marks_unknown_versions_and_warning(tmp_path: Path):
    root = tmp_path / "skills"
    _make_skill(root, "brainstorming")

    result = scanner.scan_roots([root])

    assert result.summary.total_skills == 1
    record = result.skills[0]
    assert record.current_version == "unknown"
    assert record.latest_version == "unknown"
    assert any("not a git repository" in warning for warning in result.warnings)


def test_fetch_failure_is_non_fatal_and_marks_latest_unknown(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "skills"
    broken = _make_skill(root, "broken")
    healthy = _make_skill(root, "healthy")

    def fake_is_git_repo(_path: Path) -> bool:
        return True

    def fake_fetch_tags(path: Path) -> None:
        if path.resolve() == broken.resolve():
            raise git_ops.GitCommandError("network down")

    def fake_list_tags(path: Path) -> list[str]:
        if path.resolve() == healthy.resolve():
            return ["1.2.0", "v1.3.0"]
        return []

    def fake_tags_pointing_at_head(path: Path) -> list[str]:
        if path.resolve() == healthy.resolve():
            return ["v1.3.0"]
        return []

    _patch_git_ops(
        monkeypatch,
        is_git_repo=fake_is_git_repo,
        fetch_tags=fake_fetch_tags,
        list_tags=fake_list_tags,
        tags_pointing_at_head=fake_tags_pointing_at_head,
    )

    result = scanner.scan_roots([root])

    assert result.summary.total_skills == 2
    by_name = {item.name: item for item in result.skills}
    assert by_name["broken"].latest_version == "unknown"
    assert by_name["healthy"].latest_version == "1.3.0"
    assert by_name["healthy"].current_version == "1.3.0"
    assert any("cannot fetch tags" in warning and "broken" in warning for warning in result.warnings)


def test_current_version_unknown_when_head_has_no_semver_tag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "skills"
    _make_skill(root, "brainstorming")

    _patch_git_ops(
        monkeypatch,
        is_git_repo=lambda _path: True,
        fetch_tags=lambda _path: None,
        list_tags=lambda _path: ["v1.2.0", "2.0.0"],
        tags_pointing_at_head=lambda _path: ["release-candidate"],
    )

    result = scanner.scan_roots([root])

    assert result.skills[0].current_version == "unknown"
    assert result.skills[0].latest_version == "2.0.0"


def test_semver_tag_resolution_supports_v_prefix_and_plain(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "skills"
    _make_skill(root, "brainstorming")

    _patch_git_ops(
        monkeypatch,
        is_git_repo=lambda _path: True,
        fetch_tags=lambda _path: None,
        list_tags=lambda _path: ["v1.2.0", "1.10.0", "bad-tag"],
        tags_pointing_at_head=lambda _path: ["v1.2.0", "1.1.0"],
    )

    result = scanner.scan_roots([root])

    record = result.skills[0]
    assert record.latest_version == "1.10.0"
    assert record.current_version == "1.2.0"
