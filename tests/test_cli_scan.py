import json

from skills_inventory.cli import main


def test_scan_command_exits_zero(monkeypatch, tmp_path):
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    rc = main(["scan"])
    assert rc == 0


def test_scan_writes_default_json_and_prints_summary(monkeypatch, tmp_path, capsys):
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))

    root = home / ".agents" / "skills" / "brainstorming"
    root.mkdir(parents=True)
    (root / "SKILL.md").write_text("# skill", encoding="utf-8")

    rc = main(["scan"])
    assert rc == 0

    output_file = home / ".agents" / "superskills.json"
    assert output_file.exists()

    payload = json.loads(output_file.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "1.0"
    assert payload["summary"]["total_skills"] == 1
    assert payload["skills"][0]["name"] == "brainstorming"

    stdout = capsys.readouterr().out
    assert "total_skills=1" in stdout
