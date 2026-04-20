# SuperSkills Dashboard — Design Spec

**Date:** 2026-04-20  
**Status:** Approved  
**Scope:** Add a browser-based dashboard to the existing `skills-inventory` CLI tool

---

## Overview

`superskills` currently provides a CLI for scanning skill directories, checking versions, and upgrading skills. This spec adds a browser-based dashboard that exposes the same capabilities through a polished web UI — making it easier to get a visual overview of installed skills, spot conflicts, and take action without memorising CLI commands.

The dashboard is served by a local HTTP server started via `skills-inventory serve`. All operations proxy through the existing Python logic (`scanner.py`, `git_ops.py`, etc.); the web layer is purely a presentation and coordination layer.

---

## Goals

1. **Visibility** — See all installed skills, their versions, and status at a glance.
2. **Conflict resolution** — Guided flow to compare duplicates and remove one.
3. **Upgrades** — Trigger git-tag-based upgrades from the browser.
4. **Zero new runtime dependencies** — Use Python stdlib only (`http.server`, `threading`, `importlib.resources`).

## Non-Goals

- No authentication (local tool, localhost only).
- No persistent database — state is ephemeral per server session (log in memory).
- No hot-reload of skills directory — user triggers rescan manually.
- No skill installation from remote sources (out of scope for this version).

---

## Architecture

### New module: `src/skills_inventory/web/`

```
src/skills_inventory/web/
  __init__.py
  server.py      # ThreadingHTTPServer subclass + request router
  api.py         # API handler functions (scan, versions, upgrade, resolve)
  assets/
    index.html   # Single-page dashboard (self-contained, vanilla JS)
    style.css    # All dashboard styles
    app.js       # All frontend logic (fetch API, state, DOM updates)
```

### CLI integration

`cli.py` gains a new `serve` subcommand:

```bash
skills-inventory serve
skills-inventory serve --port 9090
skills-inventory serve --no-open          # don't auto-open browser
skills-inventory serve --host 127.0.0.1   # default
```

`serve` starts `ThreadingHTTPServer`, then opens `http://localhost:<port>` in the default browser (via `webbrowser.open`), unless `--no-open` is passed. The process runs until the user sends SIGINT (Ctrl+C).

### Data flow

```
Browser JS  ──→  GET /api/scan             ──→  scanner.scan_roots()  ──→  JSON
Browser JS  ──→  GET /api/versions?...     ──→  git_ops.*             ──→  JSON
Browser JS  ──→  POST /api/upgrade         ──→  git_ops.checkout_tag  ──→  JSON
Browser JS  ──→  POST /api/conflict/resolve ─→  os.rmdir (validated)  ──→  JSON
Browser JS  ──→  GET /api/log              ──→  in-memory log list     ──→  JSON
```

---

## REST API

All API responses use `Content-Type: application/json`.

### Success envelope
```json
{ "ok": true, "data": { ... } }
```

### Error envelope
```json
{ "ok": false, "error": "human readable message", "code": "SNAKE_CASE_CODE" }
```

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Serve `index.html` |
| `GET` | `/assets/*` | Static assets (CSS, JS) |
| `GET` | `/api/scan` | Run `scan_roots()`, return `ScanResult` as JSON |
| `GET` | `/api/versions?name=X[&path=Y]` | List semver tags for a skill; `path` is optional — if omitted, resolves via scan roots same as CLI |
| `POST` | `/api/upgrade` | Upgrade a skill; body: `{name, path?, to?: string, latest?: bool}` — exactly one of `to` or `latest` must be set |
| `POST` | `/api/conflict/resolve` | Remove one of two conflicting installs; body: `{keep_path, remove_path}` |
| `GET` | `/api/log` | Return in-memory log of operations performed this session |

### Error codes

| Code | HTTP | Meaning |
|------|------|---------|
| `NOT_GIT_REPO` | 400 | Skill path is not a git repo |
| `DIRTY_WORKTREE` | 409 | Working tree has uncommitted changes |
| `TAG_NOT_FOUND` | 404 | Requested version tag does not exist |
| `NO_SEMVER_TAGS` | 404 | No valid semver tags found in repo |
| `ALREADY_CURRENT` | 200 | Skill is already at the requested version; response `ok: true` with message, no git operation performed |
| `PATH_NOT_ALLOWED` | 403 | `remove_path` is not under a known scan root |
| `NOT_A_SKILL` | 400 | `remove_path` does not contain `SKILL.md` |
| `GIT_ERROR` | 500 | Underlying git command failed |

---

## UI Design

### Visual language

- **Font pair:** `JetBrains Mono` (structural / monospace elements) + `Sora` (body / labels)
- **Color scheme:** Deep charcoal sidebar (`#0c0e12`) + bright white content area (`#f7f8fa`), amber accent (`#f5b942`), teal success (`#2dd4a0`), coral danger (`#f25c54`)
- **Accent top-border:** Each stat card has a 2px coloured top border indicating its semantic (neutral / danger / warning / success)
- **Sidebar:** Fixed-width (220px), dark, always visible; active nav item highlighted in amber with a left accent bar

### Pages (sidebar navigation)

#### 1. 概览 (Overview)
- 4 stat cards: Total Skills / Conflicts / Updates / Up to Date
- Conflict callout banner (if conflicts > 0) with "引导解决 →" button
- Full skills table: name + path / source root / current version / status badge / action button

#### 2. Skills
- Same table as overview but full-page, with search box and status filter tabs (All / Conflicts / Updates / Current)

#### 3. 冲突 (Conflicts)
- List of all conflict groups
- Clicking a conflict launches the guided resolution wizard (see below)

#### 4. 升级 (Upgrades)
- List of skills with `latest_version > current_version`
- Inline "升级" button per skill; shows version delta (`v1.3 → v1.4`)
- Progress indicator while upgrade is in flight

#### 5. 操作日志 (Log)
- Chronological list of operations taken this session (upgrade, resolve) with timestamps and outcomes

### Status badges

| State | Colour | Label |
|-------|--------|-------|
| Current | Teal | `● 已最新` |
| Update available | Amber | `● v1.x.x 可用` |
| Conflict | Coral | `● 冲突` |
| Unknown (no git tag) | Grey | `无 git tag` |

---

## Conflict Resolution Flow

Four-step guided wizard:

### Step 1 — Select conflict
List all detected conflict groups. User clicks one to begin resolution.

### Step 2 — Compare & choose
Side-by-side card comparison showing for each installation:
- Full path
- Current version & latest available version
- Last modified date
- Git working tree status (clean / dirty)
- `SKILL.md` SHA-256 hash

User clicks the card they want to **keep**. The other card is visually marked "将被移除". A bottom action bar summarises the decision. Two buttons: `← 重新选择` and `确认删除 →`.

### Step 3 — Confirm
Confirmation screen restating exactly what will be deleted (full path), with a final destructive `POST /api/conflict/resolve` call on confirm.

### Step 4 — Done
Success state. If more conflicts remain, a "Next conflict →" button advances to the next one. Otherwise "返回概览".

### Safety constraints on `/api/conflict/resolve`
1. `remove_path` must be a subdirectory of one of the configured `DEFAULT_SCAN_ROOTS` (expanded and resolved). Reject with `PATH_NOT_ALLOWED` otherwise.
2. `remove_path` must contain a `SKILL.md` file. Reject with `NOT_A_SKILL` otherwise.
3. If `remove_path` is a git repo with a dirty working tree, reject with `DIRTY_WORKTREE`.
4. Use `shutil.rmtree` (not `os.rmdir`) to recursively remove the directory.
5. Log the deletion (path, timestamp, keep_path) to the in-memory log.

---

## Server implementation notes

- Use `http.server.ThreadingHTTPServer` so concurrent browser requests don't block each other.
- Router is a simple `if/elif` chain on `(method, path_prefix)` inside `do_GET` / `do_POST` — no third-party routing library.
- Static assets are read via `importlib.resources` from the `web/assets/` package directory, keeping the package self-contained.
- CORS: set `Access-Control-Allow-Origin: *` on all API responses (localhost only, acceptable risk).
- POST body is parsed with `json.loads(self.rfile.read(content_length))`.

---

## Frontend implementation notes

- Single `index.html` loads `style.css` and `app.js`.
- `app.js` manages all routing (hash-based: `#overview`, `#skills`, `#conflicts`, `#upgrades`, `#log`).
- State management: plain JS module-level variables — `currentScan`, `pendingConflicts`, `log[]`.
- On page load, immediately calls `GET /api/scan` and renders results.
- Upgrade and resolve operations disable the triggering button and show a spinner while in-flight.
- No build step, no npm, no bundler.

---

## Verification Plan

### Automated tests (extend existing pytest suite)

- Unit test `api.py` handlers with mock scanner/git_ops results.
- Test safety constraints in `/api/conflict/resolve` (path not under scan root, no SKILL.md, dirty repo).
- Test router dispatches correct handler for each path.

### Manual verification

1. `skills-inventory serve` starts server, opens browser, shows real local skills.
2. Dashboard shows correct counts matching `skills-inventory scan` output.
3. Upgrade flow: select an outdated skill, click upgrade, verify `git log` shows correct HEAD.
4. Conflict resolution: create a manual duplicate skill dir, scan, run guided flow, verify duplicate is deleted.
5. Error handling: try to resolve with a path outside scan roots — expect `PATH_NOT_ALLOWED` error shown in UI.
