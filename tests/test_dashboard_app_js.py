from pathlib import Path


def _quick_resolve_block(js: str) -> str:
    marker = "async function quickResolve"
    next_marker = "function renderWizard"
    after_start = js.split(marker, 1)[1]
    return after_start.split(next_marker, 1)[0]


def test_quick_resolve_posts_json_and_checks_result() -> None:
    js = Path("src/skills_inventory/web/assets/app.js").read_text(encoding="utf-8")
    block = _quick_resolve_block(js)

    assert "apiFetch('/api/conflict/resolve', {" in block
    assert "method: 'POST'" in block
    assert "body: JSON.stringify" in block
    assert "if (!result.ok)" in block
    assert "apiFetch('/api/conflict/resolve', 'POST'," not in block


def test_fetch_scan_queues_when_scan_is_running() -> None:
    js = Path("src/skills_inventory/web/assets/app.js").read_text(encoding="utf-8")

    assert "let scanQueued = false;" in js
    assert "let queuedForce = false;" in js
    assert "let queuedFast = true;" in js
    assert "if (scanInProgress) {" in js
    assert "scanQueued = true;" in js
    assert "queuedForce = queuedForce || force;" in js
    assert "queuedFast = queuedFast && fast;" in js
    assert "if (!scanQueued) break;" in js


def test_conflict_bulk_resolve_ui_and_state_contract() -> None:
    js = Path("src/skills_inventory/web/assets/app.js").read_text(encoding="utf-8")

    assert "let batchResolveState = null;" in js
    assert "一键解决冲突" in js
    assert "向导处理 →" not in js
    assert "正在处理 ${done} / ${total}" in js
    assert "function chooseKeepPath(conflict)" in js
    assert "function buildBulkResolveOps(conflicts)" in js
    assert "async function resolveAllConflicts()" in js
    assert "symlink: true" in js
