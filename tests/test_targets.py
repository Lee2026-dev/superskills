from pathlib import Path

import pytest

from skills_inventory.targets import TargetResolutionError, resolve_skill_target


def _make_skill(path: Path) -> Path:
    path.mkdir(parents=True)
    (path / "SKILL.md").write_text("# skill\n", encoding="utf-8")
    return path


def test_resolve_skill_target_returns_unique_match_from_existing_roots(tmp_path: Path):
    missing_root = tmp_path / "missing"
    root = tmp_path / "skills"
    skill = _make_skill(root / "brainstorming")

    resolved = resolve_skill_target("brainstorming", None, [missing_root, root])

    assert resolved == skill.resolve()


def test_resolve_skill_target_raises_when_not_found(tmp_path: Path):
    with pytest.raises(TargetResolutionError, match=r"skill not found: brainstorming"):
        resolve_skill_target("brainstorming", None, [tmp_path / "skills"])


def test_resolve_skill_target_raises_ambiguous_with_candidate_paths(tmp_path: Path):
    first = _make_skill(tmp_path / "a" / "brainstorming")
    second = _make_skill(tmp_path / "b" / "brainstorming")

    with pytest.raises(TargetResolutionError) as exc:
        resolve_skill_target("brainstorming", None, [tmp_path / "a", tmp_path / "b"])

    text = str(exc.value)
    assert "ambiguous skill name 'brainstorming'" in text
    assert str(first.resolve()) in text
    assert str(second.resolve()) in text


def test_resolve_skill_target_rejects_relative_path(tmp_path: Path):
    _make_skill(tmp_path / "skills" / "brainstorming")

    with pytest.raises(TargetResolutionError, match=r"--path must be absolute"):
        resolve_skill_target("brainstorming", "skills/brainstorming", [tmp_path / "skills"])


def test_resolve_skill_target_rejects_path_name_mismatch(tmp_path: Path):
    candidate = _make_skill(tmp_path / "skills" / "other")

    with pytest.raises(TargetResolutionError, match=r"--path directory name must match <name>"):
        resolve_skill_target("brainstorming", str(candidate.resolve()), [tmp_path / "skills"])


def test_resolve_skill_target_rejects_path_without_skill_md(tmp_path: Path):
    candidate = tmp_path / "skills" / "brainstorming"
    candidate.mkdir(parents=True)

    with pytest.raises(
        TargetResolutionError,
        match=r"--path must point to a skill directory containing SKILL\.md",
    ):
        resolve_skill_target("brainstorming", str(candidate.resolve()), [tmp_path / "skills"])


def test_resolve_skill_target_accepts_valid_absolute_path(tmp_path: Path):
    candidate = _make_skill(tmp_path / "skills" / "brainstorming")

    resolved = resolve_skill_target("brainstorming", str(candidate.resolve()), [])

    assert resolved == candidate.resolve()
