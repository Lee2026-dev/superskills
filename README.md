# superskills

English | [简体中文](README.zh-CN.md)

`superskills` currently provides a Python CLI tool to discover local skill directories and generate a consolidated inventory file.

## What It Does

- Scans fixed roots recursively:
  - `~/.codex/skills`
  - `~/.agents/skills`
  - `~/skills`
- Detects a skill only when a directory contains `SKILL.md`
- Follows symlinks by default
- Ignores common noisy directories by default:
  - `.git`
  - `node_modules`
  - `__pycache__`
  - `.venv`
- Preserves duplicate skill names and marks conflicts
- Detects per-skill Git-based version status:
  - `current_version` (SemVer tag pointing at current `HEAD`, or `unknown`)
  - `latest_version` (highest SemVer tag after fetching tags, or `unknown`)
- Lists available versions from Git tags for an installed skill
- Upgrades an installed skill to a specific tag or latest SemVer tag
- Prints a terminal summary and writes JSON output to:
  - `~/.agents/superskills.json`

## Installation

From repository root:

```bash
pip3 install -e .
```

## Usage

### Installed CLI

```bash
skills-inventory scan
skills-inventory list-versions <name> [--path <abs-path>]
skills-inventory upgrade <name> [--path <abs-path>] (--to <tag> | --latest)
```

### Dev Mode (without install)

```bash
PYTHONPATH=src python3 -m skills_inventory.cli scan
PYTHONPATH=src python3 -m skills_inventory.cli list-versions <name> [--path <abs-path>]
PYTHONPATH=src python3 -m skills_inventory.cli upgrade <name> [--path <abs-path>] (--to <tag> | --latest)
```

### Command Notes

- `scan` now includes `current_version` and `latest_version` in terminal table and JSON.
- `list-versions` fetches tags and prints SemVer versions in descending order.
- `upgrade` refuses to run when the target repository has uncommitted changes.

## Output

The command writes JSON to `~/.agents/superskills.json` with fields like:

- `schema_version`
- `generated_at`
- `scan_roots`
- `settings`
- `summary`
- `skills`
- `conflicts`

Example summary in terminal:

```text
total_skills=12 conflict_names=2 scanned_dirs=406 duration_ms=139
```

## Development

Run tests:

```bash
python3 -m pytest -v
```

## Project Layout

```text
src/skills_inventory/
  cli.py
  scanner.py
  models.py
  output.py
tests/
docs/
```

## Current Scope (v1)

This version covers discovery/inventory plus Git-tag-based version visibility and upgrade workflows.
