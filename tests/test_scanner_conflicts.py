from pathlib import Path

from skills_inventory.scanner import scan_roots


def test_marks_conflicts_when_same_name_exists_in_multiple_roots(tmp_path: Path):
    root_a = tmp_path / "a"
    root_b = tmp_path / "b"
    (root_a / "brainstorming").mkdir(parents=True)
    (root_b / "brainstorming").mkdir(parents=True)
    (root_a / "brainstorming" / "SKILL.md").write_text("a", encoding="utf-8")
    (root_b / "brainstorming" / "SKILL.md").write_text("b", encoding="utf-8")

    result = scan_roots([root_a, root_b])

    assert result.summary.total_skills == 2
    assert result.summary.conflict_names == 1
    assert len(result.conflicts) == 1
    assert result.conflicts[0].name == "brainstorming"
    assert result.conflicts[0].count == 2
    assert all(s.has_conflict for s in result.skills)
    assert all(s.skill_md_hash.startswith("sha256:") for s in result.skills)
    assert all("T" in s.last_modified for s in result.skills)
