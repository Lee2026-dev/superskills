import pytest

from skills_inventory.cli import main


def test_scan_command_exits_zero(monkeypatch):
    monkeypatch.setenv("HOME", "/tmp")
    rc = main(["scan"])
    assert rc == 0
