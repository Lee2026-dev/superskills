# Skill Version Management (Git Tag Based) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Git-tag-based skill version management with `scan` version visibility plus `list-versions` and `upgrade` commands for installed third-party skills.

**Architecture:** Keep `scanner.py` responsible for filesystem discovery and enrich each skill with Git-derived `current_version` and `latest_version`. Add small focused modules: `versions.py` (SemVer parsing/sorting), `git_ops.py` (git subprocess adapter), and `targets.py` (name/path resolution). Extend CLI with two new subcommands that reuse these modules and enforce safety checks.

**Tech Stack:** Python 3.11+, standard library (`argparse`, `subprocess`, `re`, `pathlib`), pytest

---

## File Structure

**Create:**
- `src/skills_inventory/versions.py` — SemVer normalization/validation/sorting.
- `src/skills_inventory/git_ops.py` — thin git command wrappers with typed return values.
- `src/skills_inventory/targets.py` — resolve `<name>` and optional `--path` into exactly one installed skill path.
- `tests/test_versions.py` — unit tests for SemVer logic.
- `tests/test_git_ops.py` — unit tests for git wrapper behavior with subprocess mocking.
- `tests/test_scanner_versions.py` — scanner version enrichment behavior tests.
- `tests/test_targets.py` — target resolution behavior tests.
- `tests/test_cli_versions.py` — CLI tests for `list-versions` and `upgrade`.

**Modify:**
- `src/skills_inventory/models.py` — add `current_version` and `latest_version`, bump schema version.
- `src/skills_inventory/scanner.py` — enrich discovered skills with version status.
- `src/skills_inventory/output.py` — render new columns in terminal table.
- `src/skills_inventory/cli.py` — add new subcommands and handlers.
- `tests/test_cli_scan.py` — assert version fields in JSON and table output.
- `README.md` and `README.zh-CN.md` — update command and output docs.

### Task 1: Implement SemVer Utilities

**Files:**
- Create: `src/skills_inventory/versions.py`
- Test: `tests/test_versions.py`

- [ ] **Step 1: Write the failing SemVer tests**

```python
# tests/test_versions.py
from skills_inventory.versions import highest_tag, normalize_tag, parse_semver


def test_parse_semver_accepts_plain_and_v_prefix():
    assert parse_semver("1.2.3") == (1, 2, 3)
    assert parse_semver("v1.2.3") == (1, 2, 3)


def test_parse_semver_rejects_non_core_formats():
    assert parse_semver("1.2") is None
    assert parse_semver("v1.2.3-beta.1") is None
    assert parse_semver("abc") is None


def test_normalize_tag_returns_plain_triplet():
    assert normalize_tag("v10.20.30") == "10.20.30"
    assert normalize_tag("10.20.30") == "10.20.30"


def test_highest_tag_returns_max_semver_and_skips_invalid():
    tags = ["foo", "v1.2.0", "1.10.0", "1.2.9"]
    assert highest_tag(tags) == "1.10.0"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_versions.py -v`
Expected: FAIL with `ModuleNotFoundError` for `skills_inventory.versions`

- [ ] **Step 3: Implement minimal SemVer module**

```python
# src/skills_inventory/versions.py
from __future__ import annotations

import re

SEMVER_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


def parse_semver(tag: str) -> tuple[int, int, int] | None:
    match = SEMVER_RE.fullmatch(tag.strip())
    if not match:
        return None
    major, minor, patch = match.groups()
    return (int(major), int(minor), int(patch))


def normalize_tag(tag: str) -> str:
    parsed = parse_semver(tag)
    if parsed is None:
        raise ValueError(f"invalid semver tag: {tag}")
    return f"{parsed[0]}.{parsed[1]}.{parsed[2]}"


def sort_semver_tags_desc(tags: list[str]) -> list[str]:
    valid = [tag for tag in tags if parse_semver(tag) is not None]
    return sorted(valid, key=lambda tag: parse_semver(tag), reverse=True)


def highest_tag(tags: list[str]) -> str | None:
    ordered = sort_semver_tags_desc(tags)
    if not ordered:
        return None
    return normalize_tag(ordered[0])
```

- [ ] **Step 4: Run tests to verify pass**

Run: `python3 -m pytest tests/test_versions.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/skills_inventory/versions.py tests/test_versions.py
git commit -m "feat: add semver tag parsing utilities"
```

### Task 2: Add Git Command Adapter

**Files:**
- Create: `src/skills_inventory/git_ops.py`
- Test: `tests/test_git_ops.py`

- [ ] **Step 1: Write failing tests for git wrappers**

```python
# tests/test_git_ops.py
from pathlib import Path

from skills_inventory import git_ops


def test_is_git_repo_false_when_rev_parse_fails(monkeypatch, tmp_path: Path):
    def fake_run(*args, **kwargs):
        raise git_ops.GitCommandError("rev-parse failed")

    monkeypatch.setattr(git_ops, "_run_git", fake_run)
    assert git_ops.is_git_repo(tmp_path) is False


def test_list_tags_returns_lines(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(git_ops, "_run_git", lambda *a, **k: "v1.0.0\n1.2.0\n")
    assert git_ops.list_tags(tmp_path) == ["v1.0.0", "1.2.0"]


def test_worktree_dirty_when_status_has_output(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(git_ops, "_run_git", lambda *a, **k: " M SKILL.md\n")
    assert git_ops.is_worktree_clean(tmp_path) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_git_ops.py -v`
Expected: FAIL with `ImportError` for `skills_inventory.git_ops`

- [ ] **Step 3: Implement git adapter**

```python
# src/skills_inventory/git_ops.py
from __future__ import annotations

from pathlib import Path
import subprocess


class GitCommandError(RuntimeError):
    pass


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
```

- [ ] **Step 4: Run tests to verify pass**

Run: `python3 -m pytest tests/test_git_ops.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/skills_inventory/git_ops.py tests/test_git_ops.py
git commit -m "feat: add git operation helpers"
```

### Task 3: Extend Data Model and Output for Version Fields

**Files:**
- Modify: `src/skills_inventory/models.py`
- Modify: `src/skills_inventory/output.py`
- Modify: `tests/test_cli_scan.py`

- [ ] **Step 1: Write failing test updates for scan output fields**

```python
# tests/test_cli_scan.py (add assertions)
    assert payload["schema_version"] == "1.1"
    assert payload["skills"][0]["current_version"]
    assert payload["skills"][0]["latest_version"]

    assert "Current Version" in stdout
    assert "Latest Version" in stdout
```

- [ ] **Step 2: Run targeted test to see failure**

Run: `python3 -m pytest tests/test_cli_scan.py::test_scan_writes_default_json_and_prints_summary -v`
Expected: FAIL on missing keys/columns

- [ ] **Step 3: Update model serialization and table rendering**

```python
# src/skills_inventory/models.py (SkillRecord and schema)
@dataclass(slots=True)
class SkillRecord:
    name: str
    path: str
    source_root: str
    skill_md_path: str
    last_modified: str
    skill_md_hash: str
    current_version: str = "unknown"
    latest_version: str = "unknown"
    has_conflict: bool = False
    error: str | None = None


def scan_result_to_dict(result: ScanResult, scan_roots: list[str]) -> dict:
    return {
        "schema_version": "1.1",
        # ... unchanged fields
    }
```

```python
# src/skills_inventory/output.py (skill table rows/headers)
skill_rows = [
    [
        skill.name,
        skill.current_version,
        skill.latest_version,
        "Yes" if skill.has_conflict else "No",
        skill.source_root,
        skill.path,
    ]
    for skill in sorted(result.skills, key=lambda item: (item.name, item.path))
]
print(_render_table(["Name", "Current Version", "Latest Version", "Conflict", "Source Root", "Path"], skill_rows))
```

- [ ] **Step 4: Re-run scan CLI tests**

Run: `python3 -m pytest tests/test_cli_scan.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/skills_inventory/models.py src/skills_inventory/output.py tests/test_cli_scan.py
git commit -m "feat: include current/latest version fields in scan output"
```

### Task 4: Enrich Scanner with Git-Based Version Detection

**Files:**
- Modify: `src/skills_inventory/scanner.py`
- Create: `tests/test_scanner_versions.py`

- [ ] **Step 1: Write failing scanner version behavior tests**

```python
# tests/test_scanner_versions.py
from pathlib import Path

from skills_inventory.scanner import scan_roots


def test_non_git_skill_marks_unknown_versions(tmp_path: Path):
    root = tmp_path / "skills"
    skill = root / "brainstorming"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# x", encoding="utf-8")

    result = scan_roots([root])
    record = result.skills[0]
    assert record.current_version == "unknown"
    assert record.latest_version == "unknown"
    assert any("not a git repository" in msg for msg in result.warnings)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_scanner_versions.py -v`
Expected: FAIL on warning/version assertions

- [ ] **Step 3: Implement version probing in scanner**

```python
# src/skills_inventory/scanner.py (new imports)
from . import git_ops
from .versions import highest_tag, normalize_tag, sort_semver_tags_desc


def _resolve_versions_for_skill(skill_path: Path, warnings: list[str]) -> tuple[str, str]:
    if not git_ops.is_git_repo(skill_path):
        warnings.append(f"not a git repository: {skill_path}")
        return ("unknown", "unknown")

    current_version = "unknown"
    latest_version = "unknown"

    try:
        git_ops.fetch_tags(skill_path)
    except git_ops.GitCommandError as exc:
        warnings.append(f"cannot fetch tags for {skill_path}: {exc}")
        return (current_version, latest_version)

    tags = git_ops.list_tags(skill_path)
    latest = highest_tag(tags)
    if latest is not None:
        latest_version = latest

    for tag in sort_semver_tags_desc(git_ops.tags_pointing_at_head(skill_path)):
        current_version = normalize_tag(tag)
        break

    return (current_version, latest_version)
```

```python
# src/skills_inventory/scanner.py (when creating SkillRecord)
current_version, latest_version = _resolve_versions_for_skill(current, result.warnings)
result.skills.append(
    SkillRecord(
        name=current.name,
        path=str(current.resolve()),
        source_root=str(root_path),
        skill_md_path=str(skill_md.resolve()),
        last_modified=last_modified,
        skill_md_hash=skill_hash,
        current_version=current_version,
        latest_version=latest_version,
        error=error_text,
    )
)
```

- [ ] **Step 4: Run scanner test suite**

Run: `python3 -m pytest tests/test_scanner_detection.py tests/test_scanner_conflicts.py tests/test_scanner_filters_and_symlinks.py tests/test_scanner_versions.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/skills_inventory/scanner.py tests/test_scanner_versions.py
git commit -m "feat: probe git current/latest versions during scan"
```

### Task 5: Add Name/Path Target Resolver

**Files:**
- Create: `src/skills_inventory/targets.py`
- Create: `tests/test_targets.py`

- [ ] **Step 1: Write failing tests for ambiguity and path validation**

```python
# tests/test_targets.py
from pathlib import Path

import pytest

from skills_inventory.targets import TargetResolutionError, resolve_skill_target


def test_resolve_unique_name(tmp_path: Path):
    root = tmp_path / "skills"
    skill = root / "brainstorming"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# x", encoding="utf-8")

    path = resolve_skill_target("brainstorming", None, [root])
    assert path == skill.resolve()


def test_resolve_ambiguous_name_requires_path(tmp_path: Path):
    a = tmp_path / "a" / "brainstorming"
    b = tmp_path / "b" / "brainstorming"
    a.mkdir(parents=True)
    b.mkdir(parents=True)
    (a / "SKILL.md").write_text("# x", encoding="utf-8")
    (b / "SKILL.md").write_text("# x", encoding="utf-8")

    with pytest.raises(TargetResolutionError):
        resolve_skill_target("brainstorming", None, [tmp_path / "a", tmp_path / "b"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_targets.py -v`
Expected: FAIL with import error

- [ ] **Step 3: Implement resolver module**

```python
# src/skills_inventory/targets.py
from __future__ import annotations

from pathlib import Path


class TargetResolutionError(RuntimeError):
    pass


def _find_matches(name: str, roots: list[Path]) -> list[Path]:
    matches: list[Path] = []
    for root in roots:
        root_path = root.expanduser().resolve()
        if not root_path.exists():
            continue
        for path in root_path.rglob(name):
            if path.is_dir() and (path / "SKILL.md").is_file() and path.name == name:
                matches.append(path.resolve())
    return sorted(set(matches))


def resolve_skill_target(name: str, path: str | None, roots: list[Path]) -> Path:
    if path is not None:
        candidate = Path(path).expanduser()
        if not candidate.is_absolute():
            raise TargetResolutionError("--path must be absolute")
        if candidate.name != name:
            raise TargetResolutionError("--path directory name must match <name>")
        if not (candidate / "SKILL.md").is_file():
            raise TargetResolutionError("--path must point to a skill directory containing SKILL.md")
        return candidate.resolve()

    matches = _find_matches(name, roots)
    if not matches:
        raise TargetResolutionError(f"skill not found: {name}")
    if len(matches) > 1:
        lines = "\n".join(str(item) for item in matches)
        raise TargetResolutionError(f"ambiguous skill name '{name}', provide --path:\n{lines}")
    return matches[0]
```

- [ ] **Step 4: Run target resolver tests**

Run: `python3 -m pytest tests/test_targets.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/skills_inventory/targets.py tests/test_targets.py
git commit -m "feat: add skill name/path target resolution"
```

### Task 6: Add `list-versions` and `upgrade` CLI Commands

**Files:**
- Modify: `src/skills_inventory/cli.py`
- Create: `tests/test_cli_versions.py`

- [ ] **Step 1: Write failing CLI command tests**

```python
# tests/test_cli_versions.py
from pathlib import Path

from skills_inventory.cli import main


def test_upgrade_requires_to_or_latest(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("HOME", str(tmp_path))
    rc = main(["upgrade", "brainstorming"])
    assert rc != 0


def test_list_versions_command_exists(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("HOME", str(tmp_path))
    rc = main(["list-versions", "brainstorming"])
    assert rc != 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_cli_versions.py -v`
Expected: FAIL due missing commands

- [ ] **Step 3: Implement CLI handlers and argument parsing**

```python
# src/skills_inventory/cli.py (add imports)
from . import git_ops
from .targets import TargetResolutionError, resolve_skill_target
from .versions import highest_tag, normalize_tag, parse_semver, sort_semver_tags_desc
```

```python
# src/skills_inventory/cli.py (new parser setup)
list_parser = subparsers.add_parser("list-versions")
list_parser.add_argument("name")
list_parser.add_argument("--path")

upgrade_parser = subparsers.add_parser("upgrade")
upgrade_parser.add_argument("name")
upgrade_parser.add_argument("--path")
mode = upgrade_parser.add_mutually_exclusive_group(required=True)
mode.add_argument("--to")
mode.add_argument("--latest", action="store_true")
```

```python
# src/skills_inventory/cli.py (new handlers)
def _handle_list_versions(args: argparse.Namespace) -> int:
    try:
        target = resolve_skill_target(args.name, args.path, DEFAULT_SCAN_ROOTS)
    except TargetResolutionError as exc:
        print(f"error: {exc}")
        return 2

    if not git_ops.is_git_repo(target):
        print(f"error: not a git repository: {target}")
        return 2

    try:
        git_ops.fetch_tags(target)
        tags = sort_semver_tags_desc(git_ops.list_tags(target))
        if not tags:
            print("error: no valid semver tags found")
            return 2
        current = {normalize_tag(t) for t in git_ops.tags_pointing_at_head(target) if parse_semver(t)}
    except (git_ops.GitCommandError, ValueError) as exc:
        print(f"error: {exc}")
        return 2

    for tag in tags:
        normalized = normalize_tag(tag)
        marker = "*" if normalized in current else " "
        print(f"{marker} {normalized}")
    return 0


def _handle_upgrade(args: argparse.Namespace) -> int:
    try:
        target = resolve_skill_target(args.name, args.path, DEFAULT_SCAN_ROOTS)
    except TargetResolutionError as exc:
        print(f"error: {exc}")
        return 2

    if not git_ops.is_git_repo(target):
        print(f"error: not a git repository: {target}")
        return 2

    try:
        if not git_ops.is_worktree_clean(target):
            print(f"error: working tree is dirty: {target}")
            return 2
        git_ops.fetch_tags(target)
        tags = git_ops.list_tags(target)
        latest = highest_tag(tags)
        if latest is None:
            print("error: no valid semver tags found")
            return 2
        target_version = normalize_tag(args.to) if args.to else latest
        if args.to and normalize_tag(args.to) not in {normalize_tag(t) for t in tags if parse_semver(t)}:
            print(f"error: tag not found: {args.to}")
            return 2

        current_versions = [normalize_tag(t) for t in git_ops.tags_pointing_at_head(target) if parse_semver(t)]
        current = current_versions[0] if current_versions else "unknown"
        if current == target_version:
            print(f"already at {target_version}")
            return 0

        checkout_ref = args.to if args.to else next(t for t in tags if normalize_tag(t) == target_version)
        git_ops.checkout_tag(target, checkout_ref)
        commit = git_ops.head_commit(target)
        print(f"upgraded {args.name}: {current} -> {target_version} ({commit})")
        return 0
    except (git_ops.GitCommandError, ValueError, StopIteration) as exc:
        print(f"error: {exc}")
        return 2
```

- [ ] **Step 4: Run CLI test suite**

Run: `python3 -m pytest tests/test_cli_scan.py tests/test_cli_versions.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/skills_inventory/cli.py tests/test_cli_versions.py
git commit -m "feat: add list-versions and upgrade commands"
```

### Task 7: Documentation and Full Verification

**Files:**
- Modify: `README.md`
- Modify: `README.zh-CN.md`

- [ ] **Step 1: Update README command and output sections**

```markdown
# README.md additions
- New commands:
  - `skills-inventory list-versions <name> [--path <abs>]`
  - `skills-inventory upgrade <name> [--path <abs>] (--to <tag> | --latest)`
- `scan` output now includes `current_version` and `latest_version`.
- `upgrade` refuses dirty working trees.
```

- [ ] **Step 2: Update Chinese README with equivalent content**

```markdown
# README.zh-CN.md additions
- 新增命令：`list-versions`、`upgrade`。
- `scan` 默认输出 `current_version` 和 `latest_version`。
- 工作区有未提交改动时，`upgrade` 会拒绝执行。
```

- [ ] **Step 3: Run complete test suite**

Run: `python3 -m pytest -v`
Expected: PASS

- [ ] **Step 4: Run CLI smoke checks**

Run: `PYTHONPATH=src python3 -m skills_inventory.cli --help`
Expected: includes `scan`, `list-versions`, `upgrade`

Run: `PYTHONPATH=src python3 -m skills_inventory.cli upgrade --help`
Expected: includes mutually exclusive `--to` and `--latest`

- [ ] **Step 5: Commit**

```bash
git add README.md README.zh-CN.md
git commit -m "docs: document git tag based skill version management"
```

## Self-Review

Spec coverage check:
- Git tag as source: Task 1 + Task 2 + Task 4 + Task 6.
- `scan` includes current/latest in terminal + JSON: Task 3 + Task 4.
- `list-versions` and `upgrade`: Task 6.
- Highest SemVer for latest: Task 1 + Task 6.
- Dirty tree rejection: Task 2 + Task 6.
- Name resolution with optional `--path`: Task 5 + Task 6.
- Per-skill fetch failure in scan is non-fatal: Task 4.

Placeholder scan:
- No TODO/TBD placeholders.
- All test steps include concrete commands and expected outcomes.

Type/signature consistency:
- SemVer functions used consistently from `versions.py`.
- Git errors consistently surfaced via `GitCommandError`.
- Target resolver consistently raises `TargetResolutionError`.
