# Skills Inventory Tool Design (MVP)

Date: 2026-04-20  
Status: Approved for planning  
Owner: wenli

## 1. Goal and Scope

This MVP solves one problem only: discover and inventory skills across common local agent directories.

In scope:
- Scan fixed roots for skills.
- Identify a skill by presence of `SKILL.md`.
- Produce human-readable terminal output.
- Produce machine-readable JSON output.
- Preserve duplicates and mark naming conflicts.

Out of scope:
- Installing, moving, deleting, or fixing skills.
- Unifying runtime lookup for agents.
- Version lifecycle management.

## 2. Command and Runtime

- Tech stack: Python CLI.
- Command: `skills-inventory scan`.
- Scan mode: recursive.
- Symlink behavior: follow symlinks by default.
- Ignore directories by default: `.git`, `node_modules`, `__pycache__`, `.venv`.

## 3. Scan Roots (MVP Fixed Set)

- `~/.codex/skills`
- `~/.agents/skills`
- `~/skills`

Notes:
- `~` is expanded before scanning.
- Non-existent roots are warnings, not fatal errors.

## 4. Skill Detection Rule

A directory is a skill if and only if it contains `SKILL.md`.

MVP does not parse frontmatter for identity. Skill name is the directory name.

## 5. Output

### 5.1 Terminal Output

- Summary line: total skills, conflict names, scanned directory count, duration.
- Skills table columns:
  - `name`
  - `source_root`
  - `path`
  - `has_conflict`
  - `last_modified`
- Conflicts table columns:
  - `name`
  - `count`
  - `paths`

### 5.2 JSON Output

- Default path: `~/.agents/superskills.json`.
- JSON contains top-level metadata, summary, skill list, and conflicts aggregation.

Schema (informal):

```json
{
  "schema_version": "1.0",
  "generated_at": "ISO-8601",
  "scan_roots": ["abs path", "abs path"],
  "settings": {
    "recursive": true,
    "follow_symlinks": true,
    "ignored_dirs": [".git", "node_modules", "__pycache__", ".venv"]
  },
  "summary": {
    "total_skills": 0,
    "conflict_names": 0,
    "scanned_dirs": 0,
    "duration_ms": 0
  },
  "skills": [
    {
      "name": "string",
      "path": "abs path",
      "source_root": "abs path",
      "skill_md_path": "abs path",
      "last_modified": "ISO-8601",
      "skill_md_hash": "sha256:<hex>",
      "has_conflict": false
    }
  ],
  "conflicts": [
    {
      "name": "string",
      "count": 2,
      "paths": ["abs path", "abs path"]
    }
  ]
}
```

## 6. Data Derivation Rules

- `name`: basename of skill directory.
- `path`: absolute path of skill directory.
- `source_root`: one of the configured roots that contains the path.
- `skill_md_path`: absolute path to `SKILL.md`.
- `last_modified`: file mtime of `SKILL.md` in ISO-8601 with timezone.
- `skill_md_hash`: SHA-256 of raw `SKILL.md` bytes, prefixed with `sha256:`.
- `has_conflict`: true when at least two entries share the same `name`.

## 7. Scan Algorithm

1. Expand roots and normalize to absolute paths.
2. For each root:
   - If missing: record warning and continue.
   - Walk recursively with symlink following enabled.
   - Skip directories in ignore set.
3. When a directory contains `SKILL.md`:
   - Build one skill record.
   - Continue scanning for other skills.
4. After traversal:
   - Group by `name`.
   - Mark conflicts in each skill record.
   - Build `conflicts` aggregation array.
5. Print terminal summary/tables.
6. Write JSON to `~/.agents/superskills.json`.

## 8. Error Handling

- Root missing: warning only.
- Single skill read/hash failure: keep scanning; include `error` in that record when applicable.
- JSON write failure: command exits non-zero with explicit path and reason.
- Symlink loops: maintain visited identity (`realpath` and/or inode tuple) to avoid infinite recursion.

## 9. Testing Strategy

Unit tests:
- Detect skill by `SKILL.md`.
- Compute hash and mtime formatting.
- Conflict grouping and flagging.
- Ignore directory filtering.

Integration tests (temp dirs):
- Multi-root scan.
- Duplicate names across roots.
- Symlink traversal and loop guard.
- Missing root handling.
- JSON shape and required field coverage.

## 10. Acceptance Criteria (MVP)

- Running `skills-inventory scan` scans fixed roots and finishes without fatal error for missing roots.
- Writes JSON to `~/.agents/superskills.json`.
- Each skill record includes:
  - `name`
  - `path`
  - `source_root`
  - `has_conflict`
  - `last_modified`
  - `skill_md_hash`
- Duplicate names are all preserved and flagged as conflicts.
- Terminal output includes summary and conflicts list.

## 11. Next Iteration (Explicitly Deferred)

- Unified runtime entry across agents.
- Install/migrate/deduplicate operations.
- Incremental cache and change reports.
- Configurable scan roots and rule customization.
