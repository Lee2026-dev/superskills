/* SuperSkills Dashboard — app.js
   Hash-based SPA router. All page rendering lives here.
   State: currentScan, activeFilter, conflictWizard
*/

'use strict';

// ── State ─────────────────────────────────────────────────────────────────────

let currentScan = null;
let activeFilter = 'all';
let scanInProgress = false;
let conflictWizard = null; // { groups, index, selectedKeep }

// ── Init ──────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', async () => {
  buildShell();
  window.addEventListener('hashchange', route);
  
  // Phase 1: Fast load (local cache only)
  await fetchScan(false, true);
  
  // Phase 2: Async background update (full git check)
  setTimeout(() => fetchScan(false, false), 100);
});

// ── Shell ─────────────────────────────────────────────────────────────────────

function buildShell() {
  document.body.innerHTML = `
    <div id="app">
      <aside class="sidebar">
        <div class="brand">
          <div class="brand-row">
            <div class="brand-icon">⚡</div>
            <span class="brand-name">superskills</span>
          </div>
          <div class="brand-sub">skills manager</div>
        </div>
        <nav class="nav" id="sidebar-nav">
          <div class="nav-section-label">Navigation</div>
          <a class="nav-item" data-page="overview" href="#overview">
            <span class="nav-icon">▦</span> 概览
          </a>
          <a class="nav-item" data-page="skills" href="#skills">
            <span class="nav-icon">◈</span> Skills
            <span class="nav-badge neutral" id="badge-skills">—</span>
          </a>
          <a class="nav-item" data-page="conflicts" href="#conflicts">
            <span class="nav-icon">△</span> 冲突
            <span class="nav-badge danger hidden" id="badge-conflicts">0</span>
          </a>
          <a class="nav-item" data-page="upgrades" href="#upgrades">
            <span class="nav-icon">↑</span> 升级
            <span class="nav-badge warning hidden" id="badge-upgrades">0</span>
          </a>
          <div class="nav-section-label">系统</div>
          <a class="nav-item" data-page="log" href="#log">
            <span class="nav-icon">≡</span> 操作日志
          </a>
          <a class="nav-item" data-page="settings" href="#settings">
            <span class="nav-icon">⚙</span> 设置
          </a>
        </nav>
        <div class="sidebar-footer">
          <button class="scan-btn" id="scan-btn" onclick="fetchScan()">↻ 立即扫描</button>
          <div class="last-scan" id="last-scan">扫描中...</div>
        </div>
      </aside>
      <main class="main">
        <div class="topbar" id="topbar">
          <div class="page-title" id="page-title">概览</div>
          <div class="page-meta" id="page-meta"></div>
          <div class="topbar-right" id="topbar-right"></div>
        </div>
        <div class="content" id="content"></div>
      </main>
    </div>
    <div id="toast-container"></div>
  `;
}

// ── Routing ───────────────────────────────────────────────────────────────────

function route() {
  const page = location.hash.replace('#', '') || 'overview';

  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.page === page);
  });

  const titles = {
    overview: '概览', skills: 'Skills', conflicts: '冲突',
    upgrades: '升级', log: '操作日志'
  };
  document.getElementById('page-title').textContent = titles[page] || page;
  document.getElementById('topbar-right').innerHTML = '';
  document.getElementById('page-meta').textContent = '';

  const content = document.getElementById('content');
  content.innerHTML = '';

  switch (page) {
    case 'overview':  renderOverview(content); break;
    case 'skills':    renderSkills(content); break;
    case 'conflicts': renderConflicts(content); break;
    case 'upgrades':  renderUpgrades(content); break;
    case 'log':       renderLog(content); break;
    case 'settings':  renderSettings(content); break;
    default:          content.innerHTML = '<p style="color:var(--text-3);padding:40px">Page not found.</p>';
  }
}

// ── API ───────────────────────────────────────────────────────────────────────

async function apiFetch(path, options = {}) {
  const resp = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  const json = await resp.json();
  return json;
}

async function fetchScan(force = false, fast = false) {
  if (scanInProgress) return;
  scanInProgress = true;

  const btn = document.getElementById('scan-btn');
  const lastScanEl = document.getElementById('last-scan');
  if (btn) { 
    btn.disabled = true; 
    btn.innerHTML = fast 
      ? '<span class="spin">↻</span> 快速加载中...' 
      : '<span class="spin">↻</span> 同步数据中...'; 
  }

  try {
    let url = '/api/scan?_t=' + Date.now();
    if (force) url += '&refresh=true';
    if (fast) url += '&fast=true';
    const result = await apiFetch(url);
    if (result.ok) {
      currentScan = result.data;
      updateBadges();
      if (lastScanEl) {
        const type = fast ? '快速缓存' : '全量更新';
        lastScanEl.textContent = `${type}完成 · ${currentScan.summary.duration_ms}ms`;
      }
      route();
    } else {
      toast('扫描失败: ' + result.error, 'error');
    }
  } catch (e) {
    toast('无法连接到 superskills 服务器', 'error');
  } finally {
    scanInProgress = false;
    if (btn) { btn.disabled = false; btn.innerHTML = '↻ 立即刷新'; }
  }
}

function updateBadges() {
  if (!currentScan) return;
  const { summary, skills, conflicts } = currentScan;

  setText('badge-skills', summary.total_skills);
  setVisible('badge-skills', true);

  const conflictCount = summary.conflict_names;
  setText('badge-conflicts', conflictCount);
  setVisible('badge-conflicts', conflictCount > 0);

  const updateCount = skills.filter(s => s.latest_version !== 'unknown' && s.current_version !== 'unknown' && s.latest_version !== s.current_version).length;
  setText('badge-upgrades', updateCount);
  setVisible('badge-upgrades', updateCount > 0);
}

// ── Overview ──────────────────────────────────────────────────────────────────

function renderOverview(el) {
  if (!currentScan) { el.innerHTML = loadingHTML(); return; }
  const { summary, skills, conflicts } = currentScan;

  const upToDate = skills.filter(s => !s.has_conflict && (s.current_version === s.latest_version || s.latest_version === 'unknown')).length;
  const updates  = skills.filter(s => !s.has_conflict && s.latest_version !== 'unknown' && s.current_version !== 'unknown' && s.latest_version !== s.current_version).length;

  let conflictCallout = '';
  if (conflicts.length > 0) {
    const names = conflicts.map(c => `<code>${c.name}</code>`).join(' 和 ');
    conflictCallout = `
      <div class="callout danger">
        <div class="callout-icon">⚠</div>
        <div class="callout-body">
          <div class="callout-title">发现 ${conflicts.length} 个 Skill 名称冲突</div>
          <div class="callout-desc">${names} 在多个目录下同时存在，可能导致 Agent 加载行为不一致。</div>
        </div>
        <div class="callout-action">
          <a class="btn btn-resolve" href="#conflicts">引导解决 →</a>
        </div>
      </div>`;
  }

  const scanRoots = (currentScan.scan_roots || []).map(r => shortenPath(r)).join(' · ');

  el.innerHTML = `
    <div class="stats-row">
      ${statCard('total', summary.total_skills, 'Total Skills', `${(currentScan.scan_roots||[]).length} 个扫描根目录`)}
      ${statCard('danger', summary.conflict_names, 'Conflicts', summary.conflict_names ? '需要处理' : '无冲突')}
      ${statCard('warning', updates, 'Updates', updates ? '可升级' : '已全部最新')}
      ${statCard('success', upToDate, 'Up to Date', '已是最新版本')}
    </div>
    ${conflictCallout}
    <div class="section-hdr">
      <div class="section-title">Skills 列表</div>
      <div class="section-count">${skills.length} 个</div>
    </div>
    ${renderSkillsTable(skills)}
  `;
}

// ── Skills ────────────────────────────────────────────────────────────────────

function renderSkills(el) {
  if (!currentScan) { el.innerHTML = loadingHTML(); return; }
  const { skills } = currentScan;

  const right = document.getElementById('topbar-right');
  right.innerHTML = `
    <div class="search-wrap">🔍 <input id="skill-search" placeholder="搜索 skills..." oninput="filterSkills()" /></div>
    <div class="filter-tabs">
      ${['all','current','updates','conflicts'].map(f => `
        <button class="filter-tab ${f === activeFilter ? 'active' : ''}" onclick="setFilter('${f}')">${{all:'全部',current:'已最新',updates:'可更新',conflicts:'冲突'}[f]}</button>
      `).join('')}
    </div>
  `;

  renderFilteredSkills(skills);
}

function setFilter(f) {
  activeFilter = f;
  document.querySelectorAll('.filter-tab').forEach(el => el.classList.toggle('active', el.getAttribute('onclick').includes(`'${f}'`)));
  renderFilteredSkills(currentScan.skills);
}

function filterSkills() {
  renderFilteredSkills(currentScan.skills);
}

function renderFilteredSkills(skills) {
  const search = (document.getElementById('skill-search')?.value || '').toLowerCase();
  const content = document.getElementById('content');

  let filtered = skills.filter(s => {
    if (search && !s.name.toLowerCase().includes(search) && !s.path.toLowerCase().includes(search)) return false;
    if (activeFilter === 'current') return !s.has_conflict && s.current_version === s.latest_version;
    if (activeFilter === 'updates') return !s.has_conflict && s.latest_version !== 'unknown' && s.current_version !== 'unknown' && s.latest_version !== s.current_version;
    if (activeFilter === 'conflicts') return s.has_conflict;
    return true;
  });

  const wrap = content.querySelector('.skills-table-wrap');
  if (wrap) {
    wrap.outerHTML = `<div class="skills-table-wrap">${renderSkillsTable(filtered)}</div>`;
  } else {
    content.innerHTML = `
      <div class="section-hdr">
        <div class="section-title">Skills</div>
        <div class="section-count">${filtered.length} / ${skills.length}</div>
      </div>
      <div class="skills-table-wrap">${renderSkillsTable(filtered)}</div>
    `;
  }
}

// ── Conflicts ─────────────────────────────────────────────────────────────────

function renderConflicts(el) {
  if (!currentScan) { el.innerHTML = loadingHTML(); return; }
  const { conflicts } = currentScan;

  if (conflictWizard) {
    renderWizard(el);
    return;
  }

  if (!conflicts.length) {
    el.innerHTML = `<div class="empty-state">
      <div class="empty-state-icon">✓</div>
      <div class="empty-state-label">没有冲突</div>
      <div class="empty-state-sub">所有 Skill 名称唯一，无需处理。</div>
    </div>`;
    return;
  }

  el.innerHTML = `
    <div class="section-hdr">
      <div class="section-title">冲突 Skill</div>
      <div class="section-count">${conflicts.length} 组</div>
    </div>
    <div class="conflict-list">
      ${conflicts.map((c, i) => `
        <div class="conflict-group">
          <div class="conflict-group-header" onclick="startWizard(${i})">
            <span class="badge badge-conflict"><span class="dot"></span>${c.count} 个重复</span>
            <span class="conflict-group-name">${escapeHTML(c.name)}</span>
            <span class="btn btn-resolve" style="margin-left:auto">引导解决 →</span>
          </div>
          <div class="conflict-path-list">
            ${c.paths.map(p => `<div class="conflict-path-item">${escapeHTML(shortenPath(p))}</div>`).join('')}
          </div>
        </div>
      `).join('')}
    </div>
  `;
}

function startWizard(index) {
  const groups = currentScan.conflicts.map(c => {
    // Attach skill info to each path
    const paths = c.paths.map(p => {
      const skill = currentScan.skills.find(s => s.path === p && s.name === c.name);
      return { path: p, skill };
    });
    return { name: c.name, paths };
  });
  conflictWizard = { groups, index, selectedKeep: null };
  renderConflicts(document.getElementById('content'));
}

function renderWizard(el) {
  const { groups, index, selectedKeep } = conflictWizard;
  const group = groups[index];

  if (!group) {
    conflictWizard = null;
    renderConflicts(el);
    return;
  }

  const [a, b] = group.paths;
  const keepPath = selectedKeep;
  const removePath = keepPath ? (keepPath === a.path ? b.path : a.path) : null;

  el.innerHTML = `
    <div class="stepper">
      <div class="step done"><div class="step-num">✓</div><div class="step-label">选择冲突</div></div>
      <div class="step-line done"></div>
      <div class="step active"><div class="step-num">2</div><div class="step-label">比较 & 选择</div></div>
      <div class="step-line"></div>
      <div class="step pending"><div class="step-num">3</div><div class="step-label">确认删除</div></div>
      <div class="step-line"></div>
      <div class="step pending"><div class="step-num">4</div><div class="step-label">完成</div></div>
    </div>

    <div style="margin-bottom:20px">
      <div style="font-size:17px;font-weight:700;color:var(--text-1);margin-bottom:6px;display:flex;align-items:center;gap:10px">
        <span class="badge badge-conflict">${group.name}</span>
        在 ${group.paths.length} 个位置重复安装
      </div>
      <div style="font-size:12.5px;color:var(--text-2)">选择需要<strong>保留</strong>的版本，另一个将被永久删除。</div>
    </div>

    <div class="compare-grid">
      ${optionCardHTML(a, keepPath, 0)}
      <div class="vs-divider"><div class="vs-badge">VS</div></div>
      ${optionCardHTML(b, keepPath, 1)}
    </div>

    ${keepPath ? `
    <div class="action-bar">
      <div class="action-bar-info">
        已选择保留 <strong>${escapeHTML(shortenPath(keepPath))}</strong>。<br>
        将永久删除 <code>${escapeHTML(removePath)}</code>。此操作不可撤销。
      </div>
      <button class="btn btn-ghost" onclick="conflictWizard.selectedKeep=null;renderConflicts(document.getElementById('content'))">← 重新选择</button>
      <button class="btn btn-primary" onclick="confirmResolve('${escapeHTML(keepPath)}','${escapeHTML(removePath)}')">确认删除 →</button>
    </div>
    <div style="margin-top:-10px;margin-bottom:20px;padding:0 4px">
      <label class="control-group">
        <input type="checkbox" id="resolve-symlink" checked>
        <span>保持路径兼容性（在旧路径创建符号链接指向新位置）</span>
      </label>
    </div>
    ` : `
    <div class="action-bar">
      <div class="action-bar-info" style="color:var(--text-3)">点击上方任意一个安装版本，选择要<strong style="color:var(--text-1)">保留</strong>的那个。</div>
    </div>
    `}

    <div class="pagination-row">
      <span style="color:var(--text-3)">冲突 ${index + 1} / ${groups.length}</span>
      <div class="pag-dots">
        ${groups.map((_, i) => `<div class="pag-dot ${i === index ? 'active' : ''}"></div>`).join('')}
      </div>
    </div>
  `;
}

function optionCardHTML(entry, keepPath, sideIndex) {
  const skill = entry.skill;
  const isKeep   = keepPath === entry.path;
  const isRemove = keepPath && keepPath !== entry.path;

  const rootLabel = skill?.source_root ? shortenPath(skill.source_root) : '未知';
  const curVer = skill?.current_version || 'unknown';
  const latVer = skill?.latest_version  || 'unknown';
  const lastMod = skill?.last_modified ? new Date(skill.last_modified).toLocaleDateString('zh-CN') : '—';
  const gitStatus = skill?.error ? '错误' : '干净';

  let ribbon = '';
  if (isKeep)   ribbon = `<div class="option-ribbon keep">✓ 保留此版本</div>`;
  if (isRemove) ribbon = `<div class="option-ribbon remove">✕ 将被移除</div>`;

  const classes = ['option-card', isKeep ? 'keep' : '', isRemove ? 'remove' : ''].filter(Boolean).join(' ');

  return `
    <div class="${classes}" onclick="selectKeep('${escapeHTML(entry.path)}')">
      ${ribbon}
      <div class="option-header">
        <div class="option-source">来源根目录: ${escapeHTML(rootLabel)}</div>
        <div class="option-path">${escapeHTML(entry.path)}</div>
      </div>
      <div class="option-body">
        <div class="meta-row"><span class="meta-label">当前版本</span><span class="meta-value ${curVer!=='unknown'?'good':'muted'}">${curVer}</span></div>
        <div class="meta-row"><span class="meta-label">最新版本</span><span class="meta-value ${latVer===curVer?'good':'warn'}">${latVer}</span></div>
        <div class="meta-row"><span class="meta-label">最后修改</span><span class="meta-value">${lastMod}</span></div>
        <div class="meta-row"><span class="meta-label">Git 状态</span><span class="meta-value good">${gitStatus}</span></div>
      </div>
    </div>
  `;
}

function selectKeep(path) {
  conflictWizard.selectedKeep = path;
  renderConflicts(document.getElementById('content'));
}

async function confirmResolve(keepPath, removePath) {
  const btn = event.currentTarget;
  btn.disabled = true;
  btn.innerHTML = '<span class="spin">↻</span> 删除中...';

  const symlink = document.getElementById('resolve-symlink')?.checked || false;

  try {
    const result = await apiFetch('/api/conflict/resolve', {
      method: 'POST',
      body: JSON.stringify({ keep_path: keepPath, remove_path: removePath, symlink }),
    });
    if (result.ok) {
      toast(`已删除 ${shortenPath(removePath)}`, 'success');
      const curIndex = conflictWizard.index;
      conflictWizard.selectedKeep = null;
      conflictWizard = null;
      await fetchScan();
      if (currentScan.conflicts.length > 0 && curIndex < currentScan.conflicts.length) {
        startWizard(curIndex);
      } else if (currentScan.conflicts.length > 0) {
        startWizard(0);
      } else {
        location.hash = '#conflicts';
      }
    } else {
      toast('删除失败: ' + result.error, 'error');
      btn.disabled = false;
      btn.innerHTML = '确认删除 →';
    }
  } catch (e) {
    toast('请求失败，请重试', 'error');
    btn.disabled = false;
    btn.innerHTML = '确认删除 →';
  }
}

// ── Upgrades ──────────────────────────────────────────────────────────────────

function renderUpgrades(el) {
  if (!currentScan) { el.innerHTML = loadingHTML(); return; }
  const upgradeable = currentScan.skills.filter(
    s => !s.has_conflict && s.latest_version !== 'unknown' && s.current_version !== 'unknown' && s.latest_version !== s.current_version
  );

  if (!upgradeable.length) {
    el.innerHTML = `<div class="empty-state">
      <div class="empty-state-icon">✓</div>
      <div class="empty-state-label">所有 Skill 已是最新版本</div>
      <div class="empty-state-sub">无需升级。</div>
    </div>`;
    return;
  }

  const rows = upgradeable.map(s => `
    <div class="upgrade-row">
      <div>
        <div class="upgrade-name">${escapeHTML(s.name)}</div>
        <div class="upgrade-path">${escapeHTML(shortenPath(s.path))}</div>
      </div>
      <div class="upgrade-arrow">
        <span class="upgrade-from">${s.current_version}</span>
        <span class="upgrade-chevron">→</span>
        <span class="upgrade-to">${s.latest_version}</span>
      </div>
      <button class="btn btn-upgrade" onclick="doUpgrade('${escapeHTML(s.name)}','${escapeHTML(s.path)}',this)">↑ 升级</button>
    </div>
  `).join('');

  el.innerHTML = `
    <div class="section-hdr">
      <div class="section-title">可用升级</div>
      <div class="section-count">${upgradeable.length} 个</div>
    </div>
    <div class="upgrades-table">${rows}</div>
  `;
}

async function doUpgrade(name, path, btn) {
  const origText = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = '<span class="spin">↻</span> 升级中...';

  try {
    const result = await apiFetch('/api/upgrade', {
      method: 'POST',
      body: JSON.stringify({ name, path, latest: true }),
    });
    if (result.ok) {
      const d = result.data;
      if (d.code === 'ALREADY_CURRENT') {
        toast(`${name} 已是最新版本`, 'info');
      } else {
        toast(`已升级 ${name}: ${d.from} → ${d.to}`, 'success');
      }
      await fetchScan();
    } else {
      toast(`升级失败: ${result.error}`, 'error');
      btn.disabled = false;
      btn.innerHTML = origText;
    }
  } catch (e) {
    toast('请求失败，请重试', 'error');
    btn.disabled = false;
    btn.innerHTML = origText;
  }
}

// ── Settings ──────────────────────────────────────────────────────────────────

async function renderSettings(el) {
  el.innerHTML = `
    <header class="content-header">
      <div class="header-main">
        <h1 class="header-title">系统设置</h1>
        <p class="header-subtitle">管理扫描路径和忽略规则</p>
      </div>
    </header>
    <div class="content-body" id="settings-container">
      ${loadingHTML()}
    </div>
  `;

  try {
    const res = await apiFetch('/api/config');
    if (!res.ok) throw new Error(res.error);
    const config = res.data;
    const container = document.getElementById('settings-container');
    
    function draw() {
      container.innerHTML = `
        <div class="settings-grid">
          <section class="settings-card">
            <h3 class="settings-card-title">扫描根目录</h3>
            <p class="settings-card-desc">这些目录及其子目录将被递归搜索以寻找 SKILL.md 文件。</p>
            <div class="settings-list" id="roots-list">
              ${config.scan_roots.map((r, i) => `
                <div class="settings-item">
                  <code class="path-code">${r}</code>
                  <button class="btn-icon danger" onclick="removeConfigItem('scan_roots', ${i})">✕</button>
                </div>
              `).join('')}
            </div>
            <div class="settings-add-group">
              <input type="text" id="add-root-input" placeholder="例如: ~/.custom/skills" class="settings-input">
              <button class="btn primary" onclick="addConfigItem('scan_roots', 'add-root-input')">添加</button>
            </div>
          </section>

          <section class="settings-card">
            <h3 class="settings-card-title">忽略目录名</h3>
            <p class="settings-card-desc">扫描时将跳过名称与以下模式匹配的任何目录。</p>
            <div class="settings-list" id="ignores-list">
              ${config.ignored_dirs.map((p, i) => `
                <div class="settings-item">
                  <span class="pattern-tag">${p}</span>
                  <button class="btn-icon danger" onclick="removeConfigItem('ignored_dirs', ${i})">✕</button>
                </div>
              `).join('')}
            </div>
            <div class="settings-add-group">
              <input type="text" id="add-ignore-input" placeholder="例如: tmp_files" class="settings-input">
              <button class="btn primary" onclick="addConfigItem('ignored_dirs', 'add-ignore-input')">添加</button>
            </div>
          </section>
        </div>
        <div class="settings-footer">
          <button class="btn primary" onclick="saveConfig()">保存配置</button>
          <span id="config-status" class="status-text"></span>
        </div>
      `;
    }

    window.addConfigItem = (key, inputId) => {
      const input = document.getElementById(inputId);
      const val = input.value.trim();
      if (!val) return;
      if (!config[key].includes(val)) {
        config[key].push(val);
        draw();
      }
      input.value = '';
    };

    window.removeConfigItem = (key, index) => {
      config[key].splice(index, 1);
      draw();
    };

    window.saveConfig = async () => {
      const status = document.getElementById('config-status');
      status.textContent = '保存中...';
      try {
        const saveRes = await apiFetch('/api/config', 'POST', config);
        if (saveRes.ok) {
          toast('配置已保存', 'success');
          status.textContent = '✓ 已保存';
          fetchScan(); // Refresh data with new config
        } else {
          toast('保存失败: ' + saveRes.error, 'error');
          status.textContent = '✕ 失败';
        }
      } catch (e) {
        toast('网络错误', 'error');
      }
    };

    draw();
  } catch (e) {
    el.innerHTML = errorHTML('无法加载配置: ' + e.message);
  }
}

// ── Log ───────────────────────────────────────────────────────────────────────

async function renderLog(el) {
  let log = [];
  try {
    const result = await apiFetch('/api/log');
    if (result.ok) log = result.data;
  } catch {}

  if (!log.length) {
    el.innerHTML = `<div class="empty-state">
      <div class="empty-state-icon">≡</div>
      <div class="empty-state-label">暂无操作记录</div>
      <div class="empty-state-sub">升级或解决冲突后，操作历史将显示在这里。</div>
    </div>`;
    return;
  }

  const entries = [...log].reverse().map(e => {
    const icon = e.action === 'upgrade' ? '↑' : '✕';
    const iconClass = e.action === 'upgrade' ? 'upgrade' : 'resolve';
    let detail = '';
    if (e.action === 'upgrade') detail = `${e.name}: ${e.from} → ${e.to} (${e.commit})`;
    if (e.action === 'resolve') detail = `已删除: ${e.removed}`;

    const ts = new Date(e.timestamp).toLocaleString('zh-CN');
    return `
      <div class="log-entry">
        <div class="log-icon ${iconClass}">${icon}</div>
        <div class="log-body">
          <div class="log-action">${e.action === 'upgrade' ? '升级 Skill' : '解决冲突'}</div>
          <div class="log-detail">${escapeHTML(detail)}</div>
        </div>
        <div class="log-time">${ts}</div>
      </div>
    `;
  }).join('');

  el.innerHTML = `
    <div class="section-hdr"><div class="section-title">操作日志</div><div class="section-count">${log.length} 条</div></div>
    <div class="log-list">${entries}</div>
  `;
}

// ── Shared render helpers ─────────────────────────────────────────────────────

function renderSkillsTable(skills) {
  if (!skills.length) {
    return `<div class="empty-state" style="padding:40px">
      <div class="empty-state-icon">◈</div>
      <div class="empty-state-label">没有匹配的 Skills</div>
    </div>`;
  }

  const sorted = [...skills].sort((a, b) => a.name.localeCompare(b.name) || a.path.localeCompare(b.path));

  const rows = sorted.map(s => {
    const badge = skillBadgeHTML(s);
    const action = skillActionHTML(s);
    const root = shortenPath(s.source_root);
    const rowClass = s.has_conflict ? 'table-row conflict-row' : 'table-row';
    return `
      <div class="${rowClass}">
        <div class="cell-name">
          <div class="skill-name ${s.has_conflict ? 'conflict-name' : ''}">${escapeHTML(s.name)} ${s.is_symlink ? '<span class="badge badge-link" style="font-size:9px;padding:1px 6px;margin-left:4px">软链接</span>' : ''}</div>
          <div class="skill-path">${s.is_symlink ? '<span style="color:var(--accent)">🔗</span> ' : ''}${escapeHTML(s.path)}</div>
        </div>
        <div class="cell-source">${escapeHTML(root)}</div>
        <div class="cell-version">${s.current_version}</div>
        <div>${badge}</div>
        <div class="cell-action">${action}</div>
      </div>
    `;
  }).join('');

  return `
    <div class="skills-table">
      <div class="table-head">
        <span>名称 / 路径</span>
        <span>来源</span>
        <span>当前版本</span>
        <span>状态</span>
        <span style="text-align:right">操作</span>
      </div>
      ${rows}
    </div>
  `;
}

function skillBadgeHTML(s) {
  if (s.has_conflict) return `<span class="badge badge-conflict"><span class="dot"></span>冲突</span>`;
  if (s.current_version === 'unknown' && s.latest_version === 'unknown') return `<span class="badge badge-unknown">无 git tag</span>`;
  if (s.latest_version !== 'unknown' && s.current_version !== 'unknown' && s.latest_version !== s.current_version) {
    return `<span class="badge badge-update"><span class="dot"></span>${s.latest_version} 可用</span>`;
  }
  return `<span class="badge badge-current"><span class="dot"></span>已最新</span>`;
}

function skillActionHTML(s) {
  if (s.has_conflict) {
    const idx = currentScan.conflicts.findIndex(c => c.name === s.name);
    return `<button class="btn btn-resolve" onclick="startWizardFrom(${idx})">解决</button>`;
  }
  if (s.latest_version !== 'unknown' && s.current_version !== 'unknown' && s.latest_version !== s.current_version) {
    return `<button class="btn btn-upgrade" onclick="doUpgrade('${escapeHTML(s.name)}','${escapeHTML(s.path)}',this)">↑ 升级</button>`;
  }
  return `<button class="btn btn-ghost" style="font-size:11px">详情</button>`;
}

function startWizardFrom(conflictIndex) {
  location.hash = '#conflicts';
  setTimeout(() => startWizard(conflictIndex), 50);
}

function statCard(type, value, label, note) {
  return `
    <div class="stat-card" data-type="${type}">
      <div class="stat-label">${label}</div>
      <div class="stat-value">${value}</div>
      <div class="stat-note">${note}</div>
    </div>
  `;
}

function loadingHTML() {
  return `<div class="empty-state"><div class="empty-state-icon" style="animation:spin 1s linear infinite">↻</div><div class="empty-state-label">加载中...</div></div>`;
}

// ── Utilities ─────────────────────────────────────────────────────────────────

function shortenPath(p) {
  if (!p) return '';
  return p.replace(/^\/Users\/[^/]+/, '~').replace(/^\/home\/[^/]+/, '~');
}

function escapeHTML(str) {
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

function setVisible(id, visible) {
  const el = document.getElementById(id);
  if (el) el.classList.toggle('hidden', !visible);
}

// ── Toasts ────────────────────────────────────────────────────────────────────

function toast(message, type = 'info') {
  const icons = { success: '✓', error: '✕', info: '↻' };
  const container = document.getElementById('toast-container');
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `<span>${icons[type] || '•'}</span> ${escapeHTML(message)}`;
  container.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

// ── CSS utility ───────────────────────────────────────────────────────────────

const style = document.createElement('style');
style.textContent = `.hidden { display: none !important; }`;
document.head.appendChild(style);
