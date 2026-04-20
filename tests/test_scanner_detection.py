from pathlib import Path

from skills_inventory.scanner import scan_roots


def test_detects_skill_directories_by_skill_md(tmp_path: Path):
    root = tmp_path / ".agents" / "skills"
    skill_dir = root / "brainstorming"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Brainstorming\n", encoding="utf-8")

    result = scan_roots([root])

    assert result.summary.total_skills == 1
    assert len(result.skills) == 1
    record = result.skills[0]
    assert record.name == "brainstorming"
    assert record.path == str(skill_dir.resolve())
    assert record.source_root == str(root.resolve())
    assert record.skill_md_path == str((skill_dir / "SKILL.md").resolve())


def test_missing_root_generates_warning(tmp_path: Path):
    missing = tmp_path / "does-not-exist"
    result = scan_roots([missing])
    assert result.summary.total_skills == 0
    assert len(result.warnings) == 1
    assert "Root does not exist" in result.warnings[0]
