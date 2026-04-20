# Skills Inventory MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI command `skills-inventory scan` that discovers local skills from fixed roots and writes a machine-readable inventory JSON plus terminal summary.

**Architecture:** The CLI layer parses `scan` and delegates to a pure scanner module. The scanner returns structured records (skills, conflicts, warnings, metrics), and an output module renders both terminal tables and JSON. Tests are file-system based with temporary directories and focus on behavior from spec: detection, metadata, conflicts, ignore rules, symlink loops, and error tolerance.

**Tech Stack:** Python 3.11+, standard library (`argparse`, `hashlib`, `pathlib`, `json`), `pytest`

---

## Planned File Structure

- Create: `pyproject.toml`
- Create: `src/skills_inventory/__init__.py`
- Create: `src/skills_inventory/models.py`
- Create: `src/skills_inventory/scanner.py`
- Create: `src/skills_inventory/output.py`
- Create: `src/skills_inventory/cli.py`
- Create: `tests/test_scanner_detection.py`
- Create: `tests/test_scanner_conflicts.py`
- Create: `tests/test_scanner_filters_and_symlinks.py`
- Create: `tests/test_cli_scan.py`

### Task 1: Bootstrap CLI package and first failing CLI contract test

**Files:**
- Create: `pyproject.toml`
- Create: `src/skills_inventory/__init__.py`
- Create: `src/skills_inventory/cli.py`
- Test: `tests/test_cli_scan.py`

- [ ] **Step 1: Write the failing CLI test for command parsing**

```python
# tests/test_cli_scan.py
import pytest

from skills_inventory.cli import main


def test_scan_command_exits_zero(monkeypatch):
    monkeypatch.setenv("HOME", "/tmp")
    rc = main(["scan"])
    assert rc == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli_scan.py::test_scan_command_exits_zero -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'skills_inventory'`

- [ ] **Step 3: Create minimal package + CLI implementation**

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "skills-inventory"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = []

[project.scripts]
skills-inventory = "skills_inventory.cli:run"

[tool.pytest.ini_options]
pythonpath = ["src"]
```

```python
# src/skills_inventory/__init__.py
__all__ = ["__version__"]
__version__ = "0.1.0"
```

```python
# src/skills_inventory/cli.py
from __future__ import annotations

import argparse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="skills-inventory")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("scan")
    args = parser.parse_args(argv)

    if args.command == "scan":
        return 0
    return 1


def run() -> None:
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli_scan.py::test_scan_command_exits_zero -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/skills_inventory/__init__.py src/skills_inventory/cli.py tests/test_cli_scan.py
git commit -m "chore: bootstrap skills-inventory cli package"
```

### Task 2: Implement recursive skill detection across fixed roots

**Files:**
- Create: `src/skills_inventory/models.py`
- Create: `src/skills_inventory/scanner.py`
- Create: `tests/test_scanner_detection.py`
- Modify: `src/skills_inventory/cli.py`

- [ ] **Step 1: Write failing detection tests (SKILL.md => skill record)**

```python
# tests/test_scanner_detection.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_scanner_detection.py::test_detects_skill_directories_by_skill_md -v`
Expected: FAIL with `ImportError` for `skills_inventory.scanner`

- [ ] **Step 3: Implement models and baseline scanner**

```python
# src/skills_inventory/models.py
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class SkillRecord:
    name: str
    path: str
    source_root: str
    skill_md_path: str
    last_modified: str
    skill_md_hash: str
    has_conflict: bool = False
    error: str | None = None


@dataclass(slots=True)
class ConflictRecord:
    name: str
    count: int
    paths: list[str]


@dataclass(slots=True)
class Summary:
    total_skills: int = 0
    conflict_names: int = 0
    scanned_dirs: int = 0
    duration_ms: int = 0


@dataclass(slots=True)
class ScanResult:
    skills: list[SkillRecord] = field(default_factory=list)
    conflicts: list[ConflictRecord] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    summary: Summary = field(default_factory=Summary)
```

```python
# src/skills_inventory/scanner.py
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import hashlib
import time

from .models import ScanResult, SkillRecord

DEFAULT_IGNORED_DIRS = {".git", "node_modules", "__pycache__", ".venv"}


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"


def _file_mtime_iso(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat()


def scan_roots(
    roots: list[Path],
    recursive: bool = True,
    follow_symlinks: bool = True,
    ignored_dirs: set[str] | None = None,
) -> ScanResult:
    ignored = ignored_dirs or DEFAULT_IGNORED_DIRS
    start = time.monotonic()
    result = ScanResult()

    for root in roots:
        root_path = root.expanduser().resolve()
        if not root_path.exists():
            result.warnings.append(f"Root does not exist: {root_path}")
            continue

        stack = [root_path]
        while stack:
            current = stack.pop()
            result.summary.scanned_dirs += 1
            if current.name in ignored:
                continue

            skill_md = current / "SKILL.md"
            if skill_md.is_file():
                result.skills.append(
                    SkillRecord(
                        name=current.name,
                        path=str(current.resolve()),
                        source_root=str(root_path),
                        skill_md_path=str(skill_md.resolve()),
                        last_modified=_file_mtime_iso(skill_md),
                        skill_md_hash=_file_hash(skill_md),
                    )
                )

            if not recursive:
                continue

            for child in current.iterdir():
                if child.is_dir() and (follow_symlinks or not child.is_symlink()):
                    stack.append(child)

    result.summary.total_skills = len(result.skills)
    result.summary.duration_ms = int((time.monotonic() - start) * 1000)
    return result
```

```python
# src/skills_inventory/cli.py
from __future__ import annotations

import argparse
from pathlib import Path

from .scanner import scan_roots


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="skills-inventory")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("scan")
    args = parser.parse_args(argv)

    if args.command == "scan":
        scan_roots([Path("~/.codex/skills"), Path("~/.agents/skills"), Path("~/skills")])
        return 0
    return 1


def run() -> None:
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify detection behavior passes**

Run: `pytest tests/test_scanner_detection.py tests/test_cli_scan.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/skills_inventory/models.py src/skills_inventory/scanner.py src/skills_inventory/cli.py tests/test_scanner_detection.py
git commit -m "feat: detect skills by SKILL.md across fixed roots"
```

### Task 3: Add conflict aggregation and required metadata fields

**Files:**
- Modify: `src/skills_inventory/scanner.py`
- Create: `tests/test_scanner_conflicts.py`

- [ ] **Step 1: Write failing conflict and metadata tests**

```python
# tests/test_scanner_conflicts.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_scanner_conflicts.py::test_marks_conflicts_when_same_name_exists_in_multiple_roots -v`
Expected: FAIL because conflicts are not populated

- [ ] **Step 3: Implement conflict grouping in scanner**

```python
# src/skills_inventory/scanner.py (additions near end of scan_roots)
from collections import defaultdict
from .models import ConflictRecord

    by_name: dict[str, list[SkillRecord]] = defaultdict(list)
    for skill in result.skills:
        by_name[skill.name].append(skill)

    for name, records in sorted(by_name.items()):
        if len(records) > 1:
            result.summary.conflict_names += 1
            for record in records:
                record.has_conflict = True
            result.conflicts.append(
                ConflictRecord(
                    name=name,
                    count=len(records),
                    paths=[record.path for record in records],
                )
            )
```

- [ ] **Step 4: Run tests to verify conflicts and metadata pass**

Run: `pytest tests/test_scanner_conflicts.py tests/test_scanner_detection.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/skills_inventory/scanner.py tests/test_scanner_conflicts.py
git commit -m "feat: aggregate conflicts and flag duplicate skill names"
```

### Task 4: Enforce ignore list and symlink loop protection

**Files:**
- Modify: `src/skills_inventory/scanner.py`
- Create: `tests/test_scanner_filters_and_symlinks.py`

- [ ] **Step 1: Write failing tests for ignore and symlink behavior**

```python
# tests/test_scanner_filters_and_symlinks.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_scanner_filters_and_symlinks.py -v`
Expected: FAIL or hang risk without loop guard

- [ ] **Step 3: Add ignore enforcement + visited identity guard**

```python
# src/skills_inventory/scanner.py (core traversal replacement)
    visited: set[tuple[int, int]] = set()

    for root in roots:
        root_path = root.expanduser().resolve()
        if not root_path.exists():
            result.warnings.append(f"Root does not exist: {root_path}")
            continue

        stack = [root_path]
        while stack:
            current = stack.pop()
            try:
                stat_info = current.stat()
            except OSError as exc:
                result.warnings.append(f"Cannot stat directory: {current} ({exc})")
                continue

            identity = (stat_info.st_dev, stat_info.st_ino)
            if identity in visited:
                continue
            visited.add(identity)

            result.summary.scanned_dirs += 1
            if current.name in ignored:
                continue

            skill_md = current / "SKILL.md"
            if skill_md.is_file():
                error_text = None
                last_modified = ""
                skill_hash = ""
                try:
                    last_modified = _file_mtime_iso(skill_md)
                    skill_hash = _file_hash(skill_md)
                except OSError as exc:
                    error_text = f"metadata_error: {exc}"

                result.skills.append(
                    SkillRecord(
                        name=current.name,
                        path=str(current.resolve()),
                        source_root=str(root_path),
                        skill_md_path=str(skill_md.resolve()),
                        last_modified=last_modified,
                        skill_md_hash=skill_hash,
                        error=error_text,
                    )
                )

            if not recursive:
                continue

            try:
                children = list(current.iterdir())
            except OSError as exc:
                result.warnings.append(f"Cannot list directory: {current} ({exc})")
                continue

            for child in children:
                if not child.is_dir():
                    continue
                if child.name in ignored:
                    continue
                if child.is_symlink() and not follow_symlinks:
                    continue
                stack.append(child)
```

- [ ] **Step 4: Run tests to verify ignore and symlink protection pass**

Run: `pytest tests/test_scanner_filters_and_symlinks.py tests/test_scanner_conflicts.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/skills_inventory/scanner.py tests/test_scanner_filters_and_symlinks.py
git commit -m "feat: ignore noisy directories and prevent symlink recursion loops"
```

### Task 5: Render terminal summary and write JSON to default path

**Files:**
- Create: `src/skills_inventory/output.py`
- Modify: `src/skills_inventory/cli.py`
- Modify: `src/skills_inventory/models.py`
- Modify: `tests/test_cli_scan.py`

- [ ] **Step 1: Write failing CLI integration test for JSON output and stdout summary**

```python
# tests/test_cli_scan.py
import json
from pathlib import Path

from skills_inventory.cli import main


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli_scan.py::test_scan_writes_default_json_and_prints_summary -v`
Expected: FAIL because JSON writing and summary rendering are not implemented

- [ ] **Step 3: Implement output serialization + CLI wiring**

```python
# src/skills_inventory/models.py (append)
from datetime import datetime
from dataclasses import asdict


def scan_result_to_dict(result: ScanResult, scan_roots: list[str]) -> dict:
    return {
        "schema_version": "1.0",
        "generated_at": datetime.now().astimezone().isoformat(),
        "scan_roots": scan_roots,
        "settings": {
            "recursive": True,
            "follow_symlinks": True,
            "ignored_dirs": [".git", "node_modules", "__pycache__", ".venv"],
        },
        "summary": asdict(result.summary),
        "skills": [asdict(item) for item in result.skills],
        "conflicts": [asdict(item) for item in result.conflicts],
    }
```

```python
# src/skills_inventory/output.py
from __future__ import annotations

import json
from pathlib import Path

from .models import ScanResult, scan_result_to_dict


def print_summary(result: ScanResult) -> None:
    print(
        f"total_skills={result.summary.total_skills} "
        f"conflict_names={result.summary.conflict_names} "
        f"scanned_dirs={result.summary.scanned_dirs} "
        f"duration_ms={result.summary.duration_ms}"
    )
    if result.conflicts:
        print("conflicts:")
        for item in result.conflicts:
            joined_paths = "; ".join(item.paths)
            print(f"- {item.name} ({item.count}): {joined_paths}")


def write_json(result: ScanResult, output_path: Path, scan_roots: list[str]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = scan_result_to_dict(result, scan_roots=scan_roots)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
```

```python
# src/skills_inventory/cli.py
from __future__ import annotations

import argparse
from pathlib import Path

from .output import print_summary, write_json
from .scanner import scan_roots


DEFAULT_SCAN_ROOTS = [Path("~/.codex/skills"), Path("~/.agents/skills"), Path("~/skills")]
DEFAULT_OUTPUT = Path("~/.agents/superskills.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="skills-inventory")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("scan")
    args = parser.parse_args(argv)

    if args.command != "scan":
        return 1

    result = scan_roots(DEFAULT_SCAN_ROOTS)
    print_summary(result)

    output_path = DEFAULT_OUTPUT.expanduser()
    try:
        write_json(result, output_path=output_path, scan_roots=[str(p.expanduser()) for p in DEFAULT_SCAN_ROOTS])
    except OSError as exc:
        print(f"error: cannot write inventory json to {output_path}: {exc}")
        return 2

    return 0


def run() -> None:
    raise SystemExit(main())
```

- [ ] **Step 4: Run CLI and test suite to verify pass**

Run: `pytest tests/test_cli_scan.py tests/test_scanner_detection.py tests/test_scanner_conflicts.py tests/test_scanner_filters_and_symlinks.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/skills_inventory/output.py src/skills_inventory/models.py src/skills_inventory/cli.py tests/test_cli_scan.py
git commit -m "feat: write inventory json and print scan summary"
```

### Task 6: Add missing-root and partial-failure tolerance coverage

**Files:**
- Modify: `tests/test_scanner_detection.py`
- Modify: `src/skills_inventory/scanner.py`

- [ ] **Step 1: Write failing tests for warning and partial failure behavior**

```python
# tests/test_scanner_detection.py (append)
from skills_inventory.scanner import scan_roots


def test_missing_root_generates_warning(tmp_path):
    missing = tmp_path / "does-not-exist"
    result = scan_roots([missing])
    assert result.summary.total_skills == 0
    assert len(result.warnings) == 1
    assert "Root does not exist" in result.warnings[0]
```

- [ ] **Step 2: Run test to verify behavior currently fails if warning contract differs**

Run: `pytest tests/test_scanner_detection.py::test_missing_root_generates_warning -v`
Expected: FAIL if warning format is inconsistent; otherwise PASS and continue

- [ ] **Step 3: Normalize warning text and ensure non-fatal continuation in scanner**

```python
# src/skills_inventory/scanner.py (ensure this exact warning path is used)
        if not root_path.exists():
            result.warnings.append(f"Root does not exist: {root_path}")
            continue
```

- [ ] **Step 4: Run full tests and smoke-run CLI command**

Run: `pytest -v`
Expected: PASS

Run: `PYTHONPATH=src python -m skills_inventory.cli scan`
Expected: exit code 0, summary printed, JSON written to `~/.agents/superskills.json`

- [ ] **Step 5: Commit**

```bash
git add src/skills_inventory/scanner.py tests/test_scanner_detection.py
git commit -m "test: enforce missing-root warning and non-fatal scan behavior"
```

## Self-Review Checklist (Completed)

- Spec coverage: every confirmed MVP requirement maps to tasks above (fixed roots, detection by `SKILL.md`, recursive scan, symlink follow with loop guard, ignored dirs, conflicts preserved and marked, JSON and terminal output, non-fatal missing roots).
- Placeholder scan: no `TODO`, `TBD`, or undefined "implement later" steps remain.
- Type consistency: `SkillRecord`, `ConflictRecord`, `ScanResult`, and `scan_roots` naming is consistent across tests and implementation snippets.
