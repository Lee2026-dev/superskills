# Conflict Bulk Resolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace per-group wizard entry on the conflicts list with a single bulk action that resolves all conflicts by deterministic keep-path rules and shows a live progress bar.

**Architecture:** Keep backend unchanged and reuse `POST /api/conflict/resolve` for each remove operation. Implement deterministic keep-path selection in frontend (`app.js`) and add a lightweight progress UI in the conflicts page while operations run. Preserve existing manual per-path actions as fallback.

**Tech Stack:** Vanilla JavaScript SPA (`app.js`), CSS (`style.css`), pytest string-based frontend tests.

---

### Task 1: Plan-Safe Test Coverage For New Bulk UX

**Files:**
- Modify: `tests/test_dashboard_app_js.py`
- Test: `tests/test_dashboard_app_js.py`

- [ ] **Step 1: Write failing assertions for new UX contract**

```python
assert "一键解决冲突" in js
assert "向导处理 →" not in js
assert "let batchResolveState = null;" in js
```

- [ ] **Step 2: Add assertions for deterministic strategy + progress execution**

```python
assert "function chooseKeepPath(conflict)" in js
assert "function buildBulkResolveOps(conflicts)" in js
assert "symlink: true" in js
assert "resolveAllConflicts" in js
assert "正在处理" in js
```

- [ ] **Step 3: Run the target test and confirm it fails first**

Run: `pytest tests/test_dashboard_app_js.py -q`  
Expected: FAIL because the code still contains wizard CTA and no bulk-progress state.

- [ ] **Step 4: Commit test-only changes**

```bash
git add tests/test_dashboard_app_js.py
git commit -m "test: cover conflict bulk resolve UX contract"
```

### Task 2: Implement Deterministic Bulk Resolve In Frontend

**Files:**
- Modify: `src/skills_inventory/web/assets/app.js`

- [ ] **Step 1: Add new state for bulk run progress**

```js
let batchResolveState = null; // { running, total, done, success, failures, currentName }
```

- [ ] **Step 2: Add deterministic keep-path helpers**

```js
function chooseKeepPath(conflict) { ... }
function buildBulkResolveOps(conflicts) { ... }
```

Rules to encode:
- Prefer `~/.agents/skills/<name>`
- If all from one root, prefer `<root>/skills/<name>`
- Else priority chain `~/.agents/skills` > `~/.codex/skills` > `~/.hermes/skills` > other `*/skills` > rest
- Tie-breaker: lexicographic path

- [ ] **Step 3: Add `resolveAllConflicts()` batch executor**

```js
async function resolveAllConflicts() {
  // confirm -> loop ops -> POST /api/conflict/resolve with symlink:true
  // update progress state each operation
  // continue on failures, summarize at end
}
```

- [ ] **Step 4: Update conflicts page render**

Changes:
- Add top CTA button: `一键解决冲突`
- Add progress section with bar + `正在处理 X / Y`
- Remove per-group `向导处理 →` button
- Keep existing quick actions

- [ ] **Step 5: Run JS contract tests**

Run: `pytest tests/test_dashboard_app_js.py -q`  
Expected: PASS.

- [ ] **Step 6: Commit frontend implementation**

```bash
git add src/skills_inventory/web/assets/app.js
git commit -m "feat: add bulk conflict resolution with deterministic keep rules"
```

### Task 3: Style Progress UI And Verify Full Suite

**Files:**
- Modify: `src/skills_inventory/web/assets/style.css`
- Test: `tests/test_dashboard_app_js.py`, `tests/test_web_api.py`

- [ ] **Step 1: Add conflict bulk progress styles**

```css
.conflict-batch-progress { ... }
.progress-track { ... }
.progress-fill { ... }
```

- [ ] **Step 2: Ensure section header action alignment on conflicts page**

```css
.section-hdr-actions { margin-left: auto; display: flex; gap: 8px; }
```

- [ ] **Step 3: Run focused regression tests**

Run:
- `pytest tests/test_dashboard_app_js.py -q`
- `pytest tests/test_web_api.py -q`

Expected: PASS for both.

- [ ] **Step 4: Commit style + verification**

```bash
git add src/skills_inventory/web/assets/style.css
git commit -m "style: add progress UI for bulk conflict resolution"
```

### Task 4: Final Local Verification And Handoff

**Files:**
- Modify: none (verification only)

- [ ] **Step 1: Run final targeted test batch**

Run: `pytest tests/test_dashboard_app_js.py tests/test_web_api.py -q`  
Expected: all pass.

- [ ] **Step 2: Capture resulting git diff summary**

Run: `git status --short`

- [ ] **Step 3: Handoff notes**

Include:
- Where button appears
- Keep-path selection behavior
- Progress behavior
- Failure handling behavior
