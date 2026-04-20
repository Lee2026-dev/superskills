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
```

### Dev Mode (without install)

```bash
PYTHONPATH=src python3 -m skills_inventory.cli scan
```

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

## Current Scope (MVP)

This version is discovery + inventory only (read-focused behavior).  
Install/migrate/deduplicate/version-management workflows are intentionally deferred.

