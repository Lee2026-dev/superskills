from pathlib import Path

from skills_inventory.scanner import scan_roots


def test_ignores_common_large_directories(tmp_path: Path):
    root = tmp_path / "skills"
    (root / ".git" / "abc").mkdir(parents=True)
    (root / "node_modules" / "pkg").mkdir(parents=True)
    (root / "real_skill").mkdir(parents=True)

    (root / ".git" / "abc" / "SKILL.md").write_text("x", encoding="utf-8")
    (root / "node_modules" / "pkg" / "SKILL.md").write_text("x", encoding="utf-8")
    (root / "real_skill" / "SKILL.md").write_text("x", encoding="utf-8")

    result = scan_roots([root])
    assert [s.name for s in result.skills] == ["real_skill"]


def test_follow_symlink_without_infinite_loop(tmp_path: Path):
    root = tmp_path / "skills"
    a = root / "a"
    b = root / "b"
    a.mkdir(parents=True)
    b.mkdir(parents=True)
    (a / "SKILL.md").write_text("a", encoding="utf-8")
    (b / "to_a").symlink_to(a, target_is_directory=True)
    (a / "to_b").symlink_to(b, target_is_directory=True)

    result = scan_roots([root])
    assert result.summary.total_skills >= 1
    assert result.summary.total_skills < 10
