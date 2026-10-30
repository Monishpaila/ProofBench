/* ProofBench UI — framework-free, same-origin, accessible and intentionally dependency-light. */
(() => {
  const state = { datasets: [], models: [], providers: [], dashboard: null, pollingRun: null, pollingTimer: null };
  const root = document.getElementById('app');
  const toastRegion = document.getElementById('toast-region');

  const icons = {
    dashboard: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="4" rx="1.5"/><rect x="14" y="10" width="7" height="11" rx="1.5"/><rect x="3" y="13" width="7" height="8" rx="1.5"/>',
    play: '<path d="m8 5 11 7-11 7z"/>',
    layers: '<path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5M3 16l9 5 9-5"/>',
    history: '<path d="M3 12a9 9 0 1 0 2.64-6.36L3 8"/><path d="M3 3v5h5M12 7v5l3 2"/>',
    settings: '<circle cx="12" cy="12" r="3"/><path d="m19.4 15 .1.1a1.7 1.7 0 0 1-2.4 2.4l-.1-.1a1.7 1.7 0 0 0-2.9 1.2v.2a1.7 1.7 0 0 1-3.4 0v-.2a1.7 1.7 0 0 0-2.9-1.2l-.1.1a1.7 1.7 0 0 1-2.4-2.4l.1-.1a1.7 1.7 0 0 0-1.2-2.9H4a1.7 1.7 0 0 1 0-3.4h.2a1.7 1.7 0 0 0 1.2-2.9l-.1-.1a1.7 1.7 0 0 1 2.4-2.4l.1.1a1.7 1.7 0 0 0 2.9-1.2V2a1.7 1.7 0 0 1 3.4 0v.2a1.7 1.7 0 0 0 2.9 1.2l.1-.1a1.7 1.7 0 0 1 2.4 2.4l-.1.1a1.7 1.7 0 0 0 1.2 2.9h.2a1.7 1.7 0 0 1 0 3.4h-.2a1.7 1.7 0 0 0-1.2 2.9Z"/>',
    chart: '<path d="M3 3v18h18"/><path d="m7 14 4-4 4 3 5-7"/><path d="M17 6h3v3"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    arrow: '<path d="M5 12h14M12 5l7 7-7 7"/>',
    chevron: '<path d="m9 18 6-6-6-6"/>',
    refresh: '<path d="M20 7v5h-5M4 17v-5h5"/><path d="M5.5 9a7 7 0 0 1 11.8-2L20 12M4 12l2.7 5a7 7 0 0 0 11.8-2"/>',
    spark: '<path d="m12 3 1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3Z"/><path d="m19 15 .9 2.1L22 18l-2.1.9L19 21l-.9-2.1L16 18l2.1-.9L19 15Z"/>',
    database: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
    check: '<path d="m5 12 4 4L19 6"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    cpu: '<rect x="5" y="5" width="14" height="14" rx="2"/><path d="M9 9h6v6H9zM9 1v4m6-4v4M9 19v4m6-4v4M1 9h4m-4 6h4m14-6h4m-4 6h4"/>',
    book: '<path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v17H6.5A2.5 2.5 0 0 0 4 22z"/><path d="M4 5v17M8 7h8M8 11h8"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
    shield: '<path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11Z"/><path d="m9 12 2 2 4-4"/>',
    file: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M8 13h8M8 17h8"/>',
    close: '<path d="m18 6-12 12M6 6l12 12"/>',
    trash: '<path d="M3 6h18M8 6V4h8v2m-11 0 1 14h10l1-14M10 11v5m4-5v5"/>',
    edit: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4Z"/>',
    target: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
    list: '<path d="M9 6h11M9 12h11M9 18h11M4 6h.01M4 12h.01M4 18h.01"/>',
    message: '<path d="M21 11.5a8.4 8.4 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.4 8.4 0 0 1-3.8-.9L3 21l1.9-5.7a8.4 8.4 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.4 8.4 0 0 1 3.8-.9h.5a8.5 8.5 0 0 1 8 8z"/>',
    zap: '<path d="m13 2-3 8H4l7 12 3-8h6z"/>',
  };
  const icon = (name, size = 17) => `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[name] || icons.info}</svg>`;
  const esc = (value) => String(value ?? '').replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#39;');
  const fmtNum = (value, digits = 0) => value === null || value === undefined || Number.isNaN(Number(value)) ? '—' : Number(value).toLocaleString(undefined, { maximumFractionDigits: digits, minimumFractionDigits: digits });
  const fmtUsd = (value) => value === null || value === undefined ? '—' : (Number(value) < 0.01 && Number(value) > 0 ? '<$0.01' : `$${Number(value).toFixed(2)}`);
  const dateFmt = (raw) => { if (!raw) return 'Not started'; const d = new Date(raw); return Number.isNaN(d.valueOf()) ? raw : d.toLocaleString([], { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' }); };
  const statusLabel = (status) => ({ queued: 'Queued', running: 'Running', completed: 'Completed', completed_with_errors: 'Completed with errors', failed: 'Failed' }[status] || status || 'Unknown');
  const statusTag = (status) => `<span class="status ${esc(status || 'neutral')}">${esc(statusLabel(status))}</span>`;
  const scoreClass = (value) => value === null || value === undefined ? 'score-na' : Number(value) >= 85 ? 'score-high' : Number(value) >= 65 ? 'score-mid' : 'score-low';
  const scorePill = (value) => `<span class="score-pill ${scoreClass(value)}">${value === null || value === undefined ? 'N/A' : `${fmtNum(value, 1)}%`}</span>`;
  const providerInitial = (p) => ({ openai: 'O', gemini: 'G', anthropic: 'A', openai_compatible: '↗' }[p] || 'AI');
  const workflowLabel = (id) => ({ direct: 'Direct answer', tool_agent: 'Tool-using agent' }[id] || id || 'Tool-using agent');
  const selectedWorkflows = () => [...document.querySelectorAll('input[name="workflow_ids"]:checked')].map(el => el.value);
  const providerClass = (p) => ['openai', 'gemini', 'anthropic', 'openai_compatible'].includes(p) ? p : 'compatible';
  const selectedModels = () => [...document.querySelectorAll('input[name="model_ids"]:checked')].map(el => el.value);
  const getHash = () => { const raw = (location.hash || '#/dashboard').replace(/^#/, ''); const [path, query = ''] = raw.split('?'); return { path: path || '/dashboard', params: new URLSearchParams(query) }; };
  const navItems = [
    { path: '/dashboard', label: 'Overview', icon: 'dashboard' },
    { path: '/new-run', label: 'New benchmark', icon: 'play' },
    { path: '/models', label: 'Model explorer', icon: 'cpu' },
    { path: '/datasets', label: 'Datasets', icon: 'database' },
    { path: '/runs', label: 'Run history', icon: 'history' },
    { path: '/settings', label: 'Settings & methodology', icon: 'settings' },
  ];

  async function api(path, options = {}) {
    const headers = { 'Accept': 'application/json', ...(options.headers || {}) };
    if (options.body && !headers['Content-Type']) headers['Content-Type'] = 'application/json';
    const response = await fetch(path, { ...options, headers });
    if (response.status === 204) return null;
    let data = {};
    try { data = await response.json(); } catch (_) { /* handled below */ }
    if (!response.ok) {
      const detail = data.detail || data.message || `Request failed (${response.status})`;
      throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
    }
    return data;
  }

  function toast(title, message, type = 'success') {
    const node = document.createElement('div');
    node.className = `toast ${type}`;
    node.innerHTML = `<div>${icon(type === 'error' ? 'info' : 'check', 17)}</div><div><strong>${esc(title)}</strong><span>${esc(message)}</span></div>`;
    toastRegion.appendChild(node);
    window.setTimeout(() => node.remove(), 4800);
  }

  function stopPolling() {
    if (state.pollingTimer) window.clearTimeout(state.pollingTimer);
    state.pollingTimer = null;
    state.pollingRun = null;
  }

  function renderShell(path) {
    const activePath = path.startsWith('/runs/') ? '/runs' : path;
    const activeItem = navItems.find(item => item.path === activePath) || navItems[0];
    const readyCount = state.providers.filter(p => p.configured).length;
    root.className = 'app-shell';
    root.innerHTML = `
      <aside class="sidebar">
        <a class="brand" href="#/dashboard" aria-label="ProofBench dashboard"><span class="brand-mark"></span><span class="brand-copy"><span class="brand-name">ProofBench</span><span class="brand-caption">AI evaluation lab</span></span></a>
        <div class="nav-section">Workspace</div>
        <nav class="nav-list" aria-label="Primary navigation">
          ${navItems.map(item => `<a class="nav-item ${activeItem.path === item.path ? 'active' : ''}" href="#${item.path}">${icon(item.icon, 18)}<span>${esc(item.label)}</span></a>`).join('')}
        </nav>
        <div class="nav-spacer"></div>
        <div class="sidebar-divider"></div>
        <div class="workspace-card"><div class="workspace-avatar">PB</div><div class="workspace-copy"><div class="workspace-title">ProofBench Lab</div><div class="workspace-caption">Local workspace · v1.0</div></div><span class="workspace-dot"></span></div>
      </aside>
      <main class="main">
        <header class="topbar">
          <div class="breadcrumb"><span>ProofBench</span>${icon('chevron', 13)}<strong>${esc(activeItem.label)}</strong></div>
          <div class="top-actions"><span class="environment-pill"><span class="status-dot" style="background:${readyCount ? 'var(--mint)' : 'var(--amber)'}"></span>${readyCount} provider${readyCount === 1 ? '' : 's'} configured</span><button class="icon-button" aria-label="Refresh current view" title="Refresh" data-action="refresh">${icon('refresh', 16)}</button><a class="btn btn-primary" href="#/new-run">${icon('plus', 15)} New benchmark</a></div>
        </header>
        <div class="page-wrap" id="view"><div style="padding:60px 0;text-align:center;color:#8c97a7">Loading workspace…</div></div>
      </main>`;
  }

  async function loadCommon() {
    const [datasetsResult, modelsResult] = await Promise.all([api('/api/datasets'), api('/api/models')]);
    state.datasets = datasetsResult.datasets || [];
    state.models = modelsResult.models || [];
    state.providers = modelsResult.providers || [];
  }

  async function route() {
    stopPolling();
    const { path, params } = getHash();
    if (!path || path === '/') { location.hash = '#/dashboard'; return; }
    renderShell(path);
    const view = document.getElementById('view');
    try {
      await loadCommon();
      // Update header status after the first asynchronous catalog load.
      const readyCount = state.providers.filter(p => p.configured).length;
      const env = document.querySelector('.environment-pill');
      if (env) env.innerHTML = `<span class="status-dot" style="background:${readyCount ? 'var(--mint)' : 'var(--amber)'}"></span>${readyCount} provider${readyCount === 1 ? '' : 's'} configured`;
      if (path === '/dashboard') return await renderDashboard(view);
      if (path === '/new-run') return renderNewRun(view, params);
      if (path === '/models') return await renderModels(view);
      if (path === '/datasets') return renderDatasets(view);
      if (path === '/runs') return await renderRuns(view);
      if (path.startsWith('/runs/')) return await renderRunDetail(view, path.split('/')[2]);
      if (path === '/settings') return await renderSettings(view);
      view.innerHTML = `<div class="empty-chart"><strong>Page not found</strong><p>This route is not available.</p><a class="btn btn-primary" href="#/dashboard">Go to overview</a></div>`;
    } catch (error) {
      view.innerHTML = `<div class="info-banner warning">${icon('info')}<div><strong>Couldn't load this view</strong><p>${esc(error.message)}. Check that the ProofBench backend is running, then refresh.</p><button class="btn btn-secondary btn-sm" data-action="refresh" style="margin-top:10px">Try again</button></div></div>`;
    }
  }

  function heading(eyebrow, title, subtitle, actions = '') {
    return `<div class="page-heading"><div><div class="eyebrow">${esc(eyebrow)}</div><h1>${esc(title)}</h1><p class="subtitle">${esc(subtitle)}</p></div><div class="heading-actions">${actions}</div></div>`;
  }

  function emptyState(title, body, actionLabel = 'Run your first benchmark', actionRoute = '/new-run') {
    return `<div class="empty-chart"><div class="empty-chart-icon">${icon('chart', 21)}</div><strong>${esc(title)}</strong><p>${esc(body)}</p><a class="btn btn-primary btn-sm" href="#${actionRoute}">${icon('plus', 14)} ${esc(actionLabel)}</a></div>`;
  }

  function leaderboardBars(models, limit = 5) {
    const sorted = (models || []).filter(m => m.accuracy !== null && m.accuracy !== undefined).slice(0, limit);
    if (!sorted.length) return emptyState('No evaluation evidence yet', 'Once a benchmark finishes, model scores and run-local efficiency comparisons will appear here.');
    return `<div class="leader-list">${sorted.map(m => `<div class="leader-row"><div class="leader-name" title="${esc(m.model_id)} · ${esc(workflowLabel(m.workflow_id))}">${esc(m.model_id)}<span class="td-sub">${esc(workflowLabel(m.workflow_id))}</span></div><div class="leader-track"><div class="leader-fill" style="width:${Math.max(0, Math.min(100, Number(m.accuracy)))}%"></div></div><div class="leader-score">${fmtNum(m.accuracy, 0)}%</div></div>`).join('')}</div><div class="mini" style="margin-top:18px">Task accuracy shown. Open a specific run for apples-to-apples latency and cost comparisons.</div>`;
  }

  function providerMiniCards(providers) {
    return `<div class="provider-grid">${providers.map(p => `<div class="provider-mini"><div class="provider-logo ${providerClass(p.id)}">${esc(providerInitial(p.id))}</div><div style="min-width:0"><div class="provider-mini-name">${esc(p.label)}</div><div class="provider-mini-status">${p.configured ? 'Ready to benchmark' : 'Add environment key'}</div></div><span class="provider-state ${p.configured ? 'ready' : ''}"></span></div>`).join('')}</div>`;
  }

  async function renderDashboard(view) {
    const data = await api('/api/dashboard');
    state.dashboard = data;
    const s = data.stats || {};
    const actions = `<a href="#/datasets" class="btn btn-secondary">${icon('database', 15)} Browse datasets</a><a href="#/new-run" class="btn btn-primary">${icon('play', 14)} Run a benchmark</a>`;
    view.innerHTML = `
      ${heading('YOUR AI BENCHMARK LAB', 'Measure what matters.', 'Evaluate models and agent workflows with reproducible tests, inspectable failures, and evidence you can take to a decision meeting.', actions)}
      <div class="grid grid-4">
        <div class="card stat-card"><div class="stat-top"><span>Completed runs</span><span class="stat-icon">${icon('history', 16)}</span></div><div class="stat-value mono">${fmtNum(s.completed_runs || 0)}</div><div class="stat-caption">${fmtNum(s.total_runs || 0)} total runs created</div></div>
        <div class="card stat-card"><div class="stat-top"><span>Models evaluated</span><span class="stat-icon mint">${icon('cpu', 16)}</span></div><div class="stat-value mono">${fmtNum(s.evaluated_models || 0)}</div><div class="stat-caption">Unique models with real results</div></div>
        <div class="card stat-card"><div class="stat-top"><span>Benchmark datasets</span><span class="stat-icon blue">${icon('database', 16)}</span></div><div class="stat-value mono">${fmtNum(s.datasets || 0)}</div><div class="stat-caption">${fmtNum(state.datasets.reduce((sum, ds) => sum + ds.case_count, 0))} ready-to-run test cases</div></div>
        <div class="card stat-card"><div class="stat-top"><span>Average task accuracy</span><span class="stat-icon amber">${icon('target', 16)}</span></div><div class="stat-value mono">${s.average_accuracy == null ? '—' : `${fmtNum(s.average_accuracy, 1)}%`}</div><div class="stat-caption">Across completed case evaluations</div></div>
      </div>
      <div class="section-grid">
        <section class="card chart-card"><div class="card-head"><div><h2>Model signal</h2><p class="subtle">Task accuracy across completed evaluations</p></div><span class="tag">LIVE FROM DATABASE</span></div><div class="chart-wrap">${leaderboardBars(data.leaderboard, 5)}</div></section>
        <section class="card workflow-card"><div class="card-head" style="padding:0"><div><h2>From test to decision</h2><p class="subtle">A transparent evaluation workflow</p></div>${icon('spark', 19)}</div>
          <div class="workflow-step"><div class="step-number">01</div><div><h3>Choose your test set</h3><p>Use the included support scenarios or build your own rubric and evidence anchors.</p><a class="inline-link" href="#/datasets" style="margin-top:7px">Explore datasets ${icon('arrow', 12)}</a></div></div>
          <div class="workflow-step"><div class="step-number">02</div><div><h3>Run providers side by side</h3><p>Use real API calls with deterministic settings, native tool calling, latency and token capture.</p><a class="inline-link" href="#/new-run" style="margin-top:7px">Configure a run ${icon('arrow', 12)}</a></div></div>
          <div class="workflow-step"><div class="step-number">03</div><div><h3>Inspect evidence, not just a score</h3><p>Review per-case responses, missing rubric checks, grounding anchors and tool traces.</p><a class="inline-link" href="#/runs" style="margin-top:7px">View run history ${icon('arrow', 12)}</a></div></div>
        </section>
      </div>
      <div class="section-grid" style="grid-template-columns:minmax(0,1fr) minmax(0,1.55fr)">
        <section class="card card-pad"><div style="display:flex;align-items:center;justify-content:space-between;gap:10px"><div><h2>Provider connections</h2><p class="subtle">Secrets stay in your server environment.</p></div><a class="inline-link" href="#/settings">Configure ${icon('arrow', 12)}</a></div>${providerMiniCards(data.providers || [])}<p class="mini" style="margin:14px 0 0">${(data.providers || []).filter(p => p.configured).length ? 'Configured providers are available in the benchmark selector.' : 'Add at least one API key to .env, restart the backend, and refresh this page.'}</p></section>
        <section class="card table-card" style="margin-top:0"><div class="card-head"><div><h2>Recent runs</h2><p class="subtle">A durable history of every benchmark attempt</p></div><a class="inline-link" href="#/runs">All runs ${icon('arrow', 12)}</a></div>
          ${recentRunsTable(data.recent_runs || [])}</section>
      </div>
      <div class="footer-note">ProofBench uses auditable rubrics and local tool fixtures. Review the methodology before using scores for production decisions.</div>`;
  }

  function recentRunsTable(runs) {
    if (!runs.length) return `<div class="empty-table"><strong>No benchmark runs yet</strong><span class="mini">Your real results will appear here after the first run.</span><div style="margin-top:13px"><a class="btn btn-secondary btn-sm" href="#/new-run">Start first run ${icon('arrow', 12)}</a></div></div>`;
    return `<div class="table-scroll"><table><thead><tr><th>Benchmark</th><th>Status</th><th>Models</th><th>Created</th><th></th></tr></thead><tbody>${runs.map(run => `<tr class="clickable" data-action="open-run" data-id="${esc(run.id)}"><td><span class="td-title">${esc(run.name)}</span><span class="td-sub">${esc(run.dataset_name)} · ${fmtNum(run.case_count)} cases</span></td><td>${statusTag(run.status)}</td><td>${fmtNum(run.model_count)}</td><td>${esc(dateFmt(run.created_at))}</td><td>${icon('chevron', 14)}</td></tr>`).join('')}</tbody></table></div>`;
  }

  function modelSelectCard(model, selected) {
    const price = model.pricing ? `Input $${model.pricing.input_per_1m}/1M · Output $${model.pricing.output_per_1m}/1M` : 'Pricing not configured';
    return `<label class="model-select-card ${selected ? 'selected' : ''} ${model.configured ? '' : 'unconfigured'}"><input type="checkbox" name="model_ids" value="${esc(model.id)}" ${selected ? 'checked' : ''} ${model.configured ? '' : 'disabled'} /><div class="provider-logo ${providerClass(model.provider)}" style="width:28px;height:28px;font-size:11px">${esc(providerInitial(model.provider))}</div><div class="model-meta"><div class="model-name">${esc(model.id)}</div><div class="model-provider">${esc(model.provider_label)}</div><div class="model-cost">${esc(price)}</div><span class="model-card-status ${model.configured ? 'ready' : ''}">${model.configured ? 'Ready' : 'Needs credentials'}</span></div></label>`;
  }

  function renderNewRun(view, params = new URLSearchParams()) {
    const requestedDataset = params.get('dataset');
    const requestedModel = params.get('model');
    const chosenDataset = state.datasets.some(ds => ds.id === requestedDataset) ? requestedDataset : state.datasets[0]?.id;
    const configured = state.models.filter(m => m.configured);
    const initialModels = requestedModel && configured.some(m => m.id === requestedModel) ? [requestedModel] : [];
    const modelOptions = state.models.map(m => modelSelectCard(m, initialModels.includes(m.id))).join('');
    const datasetOptions = state.datasets.map(ds => `<option value="${esc(ds.id)}" ${ds.id === chosenDataset ? 'selected' : ''}>${esc(ds.name)} · ${fmtNum(ds.case_count)} cases</option>`).join('');
    view.innerHTML = `${heading('REPRODUCIBLE EXPERIMENT', 'New benchmark run', 'Choose a versioned dataset and configured model APIs. ProofBench stores the dataset snapshot and every case-level response with its scores.', `<a class="btn btn-secondary" href="#/datasets">${icon('database', 14)} Manage datasets</a>`)}
      ${configured.length ? '' : `<div class="info-banner warning" style="margin-bottom:18px">${icon('info')}<div><strong>No provider API is configured yet</strong><p>Open Settings for environment variable names. API keys are never entered in this browser or stored in the app database.</p><a href="#/settings" class="inline-link" style="margin-top:7px">Open setup instructions ${icon('arrow', 12)}</a></div></div>`}
      <form id="start-run-form" class="form-layout">
        <div class="card form-card">
          <div class="form-section-title">01 / Define the experiment</div><div class="form-section-subtitle">Name this run and choose the benchmark workload.</div>
          <div class="form-field"><label for="run-name">Run name <span style="color:#9aa4b2;font-weight:500">(optional)</span></label><input id="run-name" name="name" maxlength="120" placeholder="e.g. Support agent — October model review" /><span class="field-hint">A meaningful label makes the run history easier to audit.</span></div>
          <div class="form-field"><label for="dataset-id">Benchmark dataset</label><select id="dataset-id" name="dataset_id" required>${datasetOptions}</select><span class="field-hint" id="dataset-description">${esc(state.datasets.find(d => d.id === chosenDataset)?.description || '')}</span></div>
          <div style="height:1px;background:#eff1f6;margin:22px 0"></div>
          <div class="select-top"><div><div class="form-section-title">02 / Select models</div><div class="form-section-subtitle" style="margin:4px 0 0">Only providers with environment credentials can be run.</div></div><span class="tag" id="selected-count">${initialModels.length} selected</span></div>
          <div class="model-select-grid">${modelOptions}</div>
          <div class="field-hint" style="margin-top:13px">Cost estimates use the configured rate card and provider-reported token usage. Unknown prices are shown as unavailable, not zero.</div>
        </div>
        <aside class="grid" style="gap:15px;align-content:start">
          <div class="card form-card"><div class="form-section-title">03 / Compare workflows</div><div class="form-section-subtitle">Run the same model with different orchestration capabilities to separate model quality from tool use.</div>
            <label class="model-select-card selected" style="margin-bottom:9px;align-items:flex-start"><input type="checkbox" name="workflow_ids" value="direct" checked /><span class="step-number" style="margin-top:0">D</span><span class="model-meta"><span class="model-name" style="display:block">Direct model answer</span><span class="model-provider" style="display:block;white-space:normal">No tools are exposed. Best for measuring baseline reasoning and source-only response quality.</span><span class="model-card-status ready">No tool calls</span></span></label>
            <label class="model-select-card selected" style="align-items:flex-start"><input type="checkbox" name="workflow_ids" value="tool_agent" checked /><span class="step-number" style="margin-top:0">A</span><span class="model-meta"><span class="model-name" style="display:block">Tool-using agent</span><span class="model-provider" style="display:block;white-space:normal">Native function calling with safe order lookup, policy retrieval, and refund calculation fixtures.</span><span class="model-card-status ready">Native tool use</span></span></label>
            <p class="field-hint" style="margin-top:12px">Select one workflow for a focused benchmark, or both to compare baseline vs. tool-augmented behavior. Every selected model is evaluated against every selected workflow.</p>
          </div>
          <div class="card form-card"><div class="form-section-title">Experiment preview</div><p class="subtle" style="margin:5px 0 14px">A quick look at the workload you are about to run.</p><div class="run-config-summary"><div class="summary-row"><span>Test cases</span><strong id="summary-cases">${fmtNum(state.datasets.find(d => d.id === chosenDataset)?.case_count || 0)}</strong></div><div class="summary-row"><span>Models selected</span><strong id="summary-models">${initialModels.length}</strong></div><div class="summary-row"><span>Workflows selected</span><strong id="summary-workflows">2</strong></div><div class="summary-row"><span>Provider calls</span><strong id="summary-calls">${(state.datasets.find(d => d.id === chosenDataset)?.case_count || 0) * initialModels.length * 2}</strong></div><div class="summary-row"><span>Scoring</span><strong>Rubric v1</strong></div><div class="summary-row"><span>Temperature</span><strong>0 · deterministic</strong></div></div>
            <p class="run-config-foot">Every run captures a dataset version snapshot, responses, wall-clock latency, token usage, estimated cost where priced, tool traces, and failure notes. Temperature 0 improves repeatability but does not guarantee identical provider outputs.</p>
            <button type="submit" class="btn btn-primary" id="submit-run" style="width:100%;margin-top:17px" ${initialModels.length ? '' : 'disabled'}>${icon('play', 14)} Start benchmark</button>
          </div>
        </aside>
      </form>`;
    updateRunPreview();
  }

  function updateRunPreview() {
    const datasetSelect = document.getElementById('dataset-id');
    if (!datasetSelect) return;
    const dataset = state.datasets.find(d => d.id === datasetSelect.value);
    const count = selectedModels().length;
    const workflowCount = selectedWorkflows().length;
    document.querySelectorAll('.model-select-card').forEach(card => {
      const input = card.querySelector('input');
      card.classList.toggle('selected', !!input?.checked);
    });
    const countNode = document.getElementById('selected-count');
    if (countNode) countNode.textContent = `${count} selected`;
    const desc = document.getElementById('dataset-description');
    if (desc) desc.textContent = dataset?.description || '';
    const c = document.getElementById('summary-cases'); if (c) c.textContent = fmtNum(dataset?.case_count || 0);
    const m = document.getElementById('summary-models'); if (m) m.textContent = fmtNum(count);
    const workflows = document.getElementById('summary-workflows'); if (workflows) workflows.textContent = fmtNum(workflowCount);
    const calls = document.getElementById('summary-calls'); if (calls) calls.textContent = fmtNum((dataset?.case_count || 0) * count * workflowCount);
    const submit = document.getElementById('submit-run'); if (submit) submit.disabled = count === 0 || workflowCount === 0;
  }

  async function handleStartRun(form) {
    const modelIds = selectedModels();
    const workflowIds = selectedWorkflows();
    if (!modelIds.length) { toast('Select a model', 'Choose at least one configured model before starting.', 'error'); return; }
    if (!workflowIds.length) { toast('Select a workflow', 'Choose Direct answer, Tool-using agent, or both.', 'error'); return; }
    const btn = document.getElementById('submit-run');
    if (btn) { btn.disabled = true; btn.innerHTML = `${icon('clock', 14)} Queuing benchmark…`; }
    const formData = new FormData(form);
    try {
      const run = await api('/api/runs', { method: 'POST', body: JSON.stringify({
        name: String(formData.get('name') || '').trim() || null,
        dataset_id: String(formData.get('dataset_id') || ''),
        model_ids: modelIds,
        workflow_ids: workflowIds,
      }) });
      toast('Benchmark queued', 'Your run is saved. Results will appear as each case completes.');
      location.hash = `#/runs/${run.id}`;
    } catch (error) {
      toast('Could not start benchmark', error.message, 'error');
      if (btn) { btn.disabled = false; btn.innerHTML = `${icon('play', 14)} Start benchmark`; }
    }
  }

  async function renderModels(view) {
    const dashboard = await api('/api/dashboard');
    const leaderboard = dashboard.leaderboard || [];
    const actions = `<a class="btn btn-primary" href="#/new-run">${icon('plus', 14)} Compare models</a>`;
    view.innerHTML = `${heading('MODEL CATALOG', 'Model explorer', 'See which provider adapters are available, inspect historical evidence, and start a consistent side-by-side benchmark.', actions)}
      <div class="info-banner" style="margin-bottom:18px">${icon('info')}<div><strong>Configured does not mean benchmarked.</strong><p>A model becomes part of the historical leaderboard only after successful real provider calls. Provider aliases and supported model IDs can be changed with environment variables.</p></div></div>
      <div class="grid grid-3">${state.models.map(model => {
        const hist = leaderboard.find(m => m.model_id === model.id);
        const price = model.pricing ? `${model.pricing.input_per_1m} / ${model.pricing.output_per_1m}` : 'Not configured';
        return `<article class="card model-card"><div class="model-card-top"><div class="provider-logo ${providerClass(model.provider)}">${esc(providerInitial(model.provider))}</div><div style="min-width:0"><div class="model-card-name">${esc(model.id)}</div><div class="model-card-provider">${esc(model.provider_label)}</div></div></div>
          <div class="model-card-metrics"><div class="model-card-metric"><span>Historical accuracy · best workflow</span><strong>${hist?.accuracy == null ? '—' : `${fmtNum(hist.accuracy, 1)}%`}</strong></div><div class="model-card-metric"><span>Latest listed rate · USD / 1M</span><strong style="font-size:11px">${esc(price)}</strong></div></div>
          <div class="model-card-bottom"><span class="tag ${model.configured ? 'mint' : ''}">${model.configured ? 'Configured' : 'Credentials needed'}</span><a class="inline-link" href="#/new-run?model=${encodeURIComponent(model.id)}">Benchmark ${icon('arrow', 12)}</a></div></article>`;
      }).join('')}</div>
      <section class="card table-card"><div class="card-head"><div><h2>Historical task accuracy</h2><p class="subtle">Aggregated from completed cases in this local database.</p></div><span class="tag">LIVE RESULTS</span></div>${leaderboard.length ? `<div class="chart-wrap">${leaderboardBars(leaderboard, 8)}</div>` : `<div style="padding:18px 22px 22px">${emptyState('No scored models to rank yet', 'Run the same dataset against two or more configured models to compare them on the same workload.')}</div>`}</section>`;
  }

  function renderDatasets(view) {
    const actions = `<button class="btn btn-primary" data-action="new-dataset">${icon('plus', 14)} Create dataset</button>`;
    view.innerHTML = `${heading('TEST DATA MANAGEMENT', 'Benchmark datasets', 'Build reusable evaluation suites around real tasks, reference answers, evidence anchors, forbidden content, and expected tool calls.', actions)}
      <div class="info-banner" style="margin-bottom:18px">${icon('book')}<div><strong>Rubrics are part of the benchmark.</strong><p>Each case can define <code>must_include</code>, <code>must_not_include</code>, <code>grounding_facts</code>, and <code>expected_tools</code>. Run history stores a snapshot, so editing a dataset will not rewrite past results.</p></div></div>
      <div class="grid grid-3">${state.datasets.map(ds => `<article class="card dataset-card"><div class="dataset-card-head"><div class="dataset-icon">${icon('database', 20)}</div><span class="tag">v${fmtNum(ds.version)}</span></div><div class="dataset-title">${esc(ds.name)}</div><p class="dataset-description">${esc(ds.description || 'No description added.')}</p><div class="dataset-meta"><span class="tag accent">${esc(ds.category)}</span><span class="tag">${fmtNum(ds.case_count)} test cases</span></div><div class="dataset-actions"><a href="#/new-run?dataset=${encodeURIComponent(ds.id)}" class="btn btn-primary btn-sm">Run dataset ${icon('arrow', 12)}</a><button class="btn btn-secondary btn-sm" data-action="edit-dataset" data-id="${esc(ds.id)}" aria-label="Edit ${esc(ds.name)}">${icon('edit', 13)}</button><button class="icon-button" data-action="delete-dataset" data-id="${esc(ds.id)}" aria-label="Delete ${esc(ds.name)}" title="Delete dataset">${icon('trash', 13)}</button></div></article>`).join('')}
      ${state.datasets.length ? '' : `<div class="card card-pad">${emptyState('No datasets found', 'Create a dataset with at least one benchmark case.', 'Create dataset', '/datasets')}</div>`}</div>
      <p class="footer-note">Included order and policy tools are deterministic local fixtures—not a connection to a real commerce system. Replace them before evaluating live business operations.</p>`;
  }

  function openDatasetEditor(dataset = null) {
    const isEdit = !!dataset;
    const cases = dataset?.cases || [{
      id: 'case_01', title: 'Example grounded answer', category: 'Knowledge QA',
      prompt: 'Answer the question using only the supplied source.', context: 'The service is available Monday through Friday.',
      reference_answer: 'The service is available Monday through Friday.', must_include: ['Monday through Friday'],
      must_not_include: [], grounding_facts: ['Monday through Friday'], expected_tools: [], tags: ['grounding'],
    }];
    const modalRoot = document.createElement('div'); modalRoot.id = 'modal-root';
    modalRoot.innerHTML = `<div class="modal-backdrop" data-action="modal-backdrop"><section class="modal" role="dialog" aria-modal="true" aria-labelledby="dataset-modal-title"><form id="dataset-editor-form" data-id="${esc(dataset?.id || '')}">
      <div class="modal-header"><div><h2 id="dataset-modal-title">${isEdit ? 'Edit dataset' : 'Create a dataset'}</h2><p class="subtle">Versioned test cases with transparent, deterministic scoring rubrics.</p></div><button type="button" class="icon-button" data-action="close-modal" aria-label="Close dialog">${icon('close', 15)}</button></div>
      <div class="modal-body"><div class="form-field"><label for="dataset-name">Dataset name</label><input id="dataset-name" name="name" required minlength="2" maxlength="120" value="${esc(dataset?.name || '')}" placeholder="e.g. Claims intake accuracy" /></div>
      <div class="form-field"><label for="dataset-description">Description</label><input id="dataset-description" name="description" maxlength="1000" value="${esc(dataset?.description || '')}" placeholder="What business workflow does this dataset cover?" /></div>
      <div class="form-field"><label for="dataset-category">Category</label><input id="dataset-category" name="category" maxlength="80" value="${esc(dataset?.category || 'custom')}" placeholder="e.g. operations, sales, support" /></div>
      <div class="form-field"><label for="dataset-cases">Cases JSON</label><textarea class="json-editor" id="dataset-cases" name="cases" required spellcheck="false">${esc(JSON.stringify(cases, null, 2))}</textarea><span class="field-hint">Required per case: <code>id</code>, <code>title</code>, <code>prompt</code>. Optional: <code>context</code>, <code>reference_answer</code>, <code>must_include</code>, <code>must_not_include</code>, <code>grounding_facts</code>, <code>expected_tools</code>, <code>tags</code>. Expected tools: lookup_order, get_policy, calculate_refund.</span></div>
      </div><div class="modal-footer"><span class="mini">${isEdit ? `Current version: v${fmtNum(dataset.version)} · saving creates a new version` : 'The first saved version will be v1.'}</span><div class="modal-footer-right"><button type="button" class="btn btn-secondary" data-action="close-modal">Cancel</button><button type="submit" class="btn btn-primary">${isEdit ? 'Save new version' : 'Create dataset'}</button></div></div>
    </form></section></div>`;
    document.body.appendChild(modalRoot);
    document.getElementById('dataset-name')?.focus();
  }

  async function submitDatasetForm(form) {
    const name = document.getElementById('dataset-name').value.trim();
    const description = document.getElementById('dataset-description').value.trim();
    const category = document.getElementById('dataset-category').value.trim() || 'custom';
    let cases;
    try { cases = JSON.parse(document.getElementById('dataset-cases').value); }
    catch (_) { toast('Invalid case JSON', 'Check commas, quotes, brackets, and that the JSON is an array.', 'error'); return; }
    if (!Array.isArray(cases) || !cases.length) { toast('Dataset needs cases', 'Provide a JSON array with at least one case object.', 'error'); return; }
    const submit = form.querySelector('button[type="submit"]');
    submit.disabled = true; submit.textContent = 'Saving…';
    try {
      const id = form.dataset.id;
      const result = await api(id ? `/api/datasets/${encodeURIComponent(id)}` : '/api/datasets', {
        method: id ? 'PUT' : 'POST', body: JSON.stringify({ name, description, category, cases }),
      });
      document.getElementById('modal-root')?.remove();
      toast(id ? 'Dataset updated' : 'Dataset created', `${result.name} · version ${result.version}`);
      await route();
    } catch (error) {
      toast('Could not save dataset', error.message, 'error');
      submit.disabled = false; submit.textContent = form.dataset.id ? 'Save new version' : 'Create dataset';
    }
  }

  async function renderRuns(view) {
    const data = await api('/api/runs?limit=100');
    const runs = data.runs || [];
    const actions = `<a class="btn btn-primary" href="#/new-run">${icon('plus', 14)} New benchmark</a>`;
    view.innerHTML = `${heading('AUDITABLE HISTORY', 'Run history', 'Every benchmark attempt is persisted. Open a run to inspect comparisons, case responses, tool traces, scoring evidence, and errors.', actions)}
      <div class="grid grid-4" style="margin-bottom:18px"><div class="card stat-card"><div class="stat-top">Total runs <span class="stat-icon">${icon('history', 15)}</span></div><div class="stat-value">${fmtNum(runs.length)}</div><div class="stat-caption">Persisted in your local database</div></div><div class="card stat-card"><div class="stat-top">Completed <span class="stat-icon mint">${icon('check', 15)}</span></div><div class="stat-value">${fmtNum(runs.filter(r => ['completed','completed_with_errors'].includes(r.status)).length)}</div><div class="stat-caption">Finished or finished with errors</div></div><div class="card stat-card"><div class="stat-top">In progress <span class="stat-icon blue">${icon('clock', 15)}</span></div><div class="stat-value">${fmtNum(runs.filter(r => ['queued','running'].includes(r.status)).length)}</div><div class="stat-caption">Queued or running now</div></div><div class="card stat-card"><div class="stat-top">Case evaluations <span class="stat-icon amber">${icon('list', 15)}</span></div><div class="stat-value">${fmtNum(runs.reduce((sum,r) => sum + (r.result_count || 0), 0))}</div><div class="stat-caption">Successful and failed provider attempts</div></div></div>
      <section class="card table-card" style="margin-top:0"><div class="card-head"><div><h2>All benchmark runs</h2><p class="subtle">Sorted newest first · click a row to open the report</p></div><span class="tag">${fmtNum(runs.length)} RUNS</span></div>
      ${runs.length ? `<div class="table-scroll"><table><thead><tr><th>Benchmark</th><th>Status</th><th>Candidates</th><th>Case results</th><th>Top composite</th><th>Created</th><th></th></tr></thead><tbody>${runs.map(run => { const best = (run.model_summaries || []).find(s => s.composite_score != null); return `<tr class="clickable" data-action="open-run" data-id="${esc(run.id)}"><td><span class="td-title">${esc(run.name)}</span><span class="td-sub">${esc(run.dataset_name)} · v${run.dataset_version ?? '—'}</span></td><td>${statusTag(run.status)}</td><td>${fmtNum(run.candidate_count || run.model_count)}</td><td>${fmtNum(run.completed_result_count)}/${fmtNum(run.case_count * (run.candidate_count || run.model_count))}</td><td>${best ? scorePill(best.composite_score) : '—'}</td><td>${esc(dateFmt(run.created_at))}</td><td>${icon('chevron', 14)}</td></tr>`; }).join('')}</tbody></table></div>` : `<div style="padding:18px 22px 22px">${emptyState('Your run history starts here', 'Run a dataset against a configured model API. ProofBench will save case-level scores and raw responses for inspection.')}</div>`}
      </section>`;
  }

  function resultStats(run) {
    const summaries = run.model_summaries || [];
    const completed = run.completed_result_count || 0;
    const total = run.case_count * (run.candidate_count || run.model_count);
    const scores = run.results.filter(r => r.accuracy_score != null && r.status === 'completed').map(r => r.accuracy_score);
    const avg = scores.length ? scores.reduce((a,b) => a+b,0)/scores.length : null;
    const costs = run.results.filter(r => r.cost_usd != null).reduce((sum,r) => sum + r.cost_usd, 0);
    const anyCost = run.results.some(r => r.cost_usd != null);
    const latencies = run.results.filter(r => r.latency_ms != null && r.status === 'completed').map(r => r.latency_ms);
    const avgLatency = latencies.length ? latencies.reduce((a,b)=>a+b,0)/latencies.length : null;
    return `<div class="result-stat-row"><div class="result-stat"><div class="result-stat-label">Case evaluations</div><div class="result-stat-value">${fmtNum(completed)}<span style="font-size:12px;color:#9aa4b2;font-weight:600"> / ${fmtNum(total)}</span></div></div><div class="result-stat"><div class="result-stat-label">Mean task accuracy</div><div class="result-stat-value">${avg == null ? '—' : `${fmtNum(avg,1)}%`}</div></div><div class="result-stat"><div class="result-stat-label">Mean response latency</div><div class="result-stat-value">${avgLatency == null ? '—' : `${fmtNum(avgLatency,0)}<span style="font-size:11px;color:#8893a3;font-weight:600"> ms</span>`}</div></div><div class="result-stat"><div class="result-stat-label">Total estimated cost</div><div class="result-stat-value">${anyCost ? fmtUsd(costs) : '—'}</div></div></div>`;
  }

  function modelComparisonTable(summaries) {
    if (!summaries.length) return `<div class="empty-table"><strong>Waiting for model results</strong><span class="mini">The comparison table will populate as benchmark cases finish.</span></div>`;
    return `<div class="table-scroll"><table><thead><tr><th>Model</th><th>Composite</th><th>Task accuracy</th><th>Grounding</th><th>Tool reliability</th><th>Mean latency</th><th>Est. total cost</th><th>Failures</th></tr></thead><tbody>${summaries.map((m, idx) => `<tr><td><span class="td-title">${esc(m.model_id)}</span><span class="td-sub">${esc(m.provider || '')} · ${esc(workflowLabel(m.workflow_id))}${idx === 0 &&
m.composite_score != null &&
Number(m.case_count) >= 3 &&
Number(m.completed_cases) >= Math.max(
    3,
    Math.ceil(Number(m.case_count) * 0.8)
)? ' · Highest composite' : ''}</span></td><td>${(
    Number(m.case_count) >= 3 &&
    Number(m.completed_cases) >= Math.max(
        3,
        Math.ceil(Number(m.case_count) * 0.8)
    ) &&
    m.composite_score != null
)
    ? scorePill(m.composite_score)
    : '<span class="mini">Insufficient evidence</span>'}</td><td>${scorePill(m.accuracy)}</td><td>${scorePill(m.grounding)}</td><td>${scorePill(m.tool_reliability)}</td><td>${m.mean_latency_ms == null ? '—' : `${fmtNum(m.mean_latency_ms,0)} ms`}</td><td>${fmtUsd(m.total_cost_usd)}</td><td>${m.failure_rate == null ? '—' : `${fmtNum(m.failure_rate,0)}%`}</td></tr>`).join('')}</tbody></table></div>`;
  }

  function groupedCaseResults(results, modelIds) {
    const grouped = new Map();
    results.forEach(r => {
      const key = r.case_id;
      if (!grouped.has(key)) grouped.set(key, []);
      grouped.get(key).push(r);
    });
    if (!grouped.size) return `<div class="empty-table"><strong>No case results yet</strong><span class="mini">Responses and scoring evidence appear as calls complete.</span></div>`;
    return [...grouped.entries()].map(([caseId, rows]) => {
      rows.sort((a,b) => modelIds.indexOf(a.model_id) - modelIds.indexOf(b.model_id));
      const first = rows[0];
      return `<div class="case-result"><div class="case-result-title"><div><h3>${esc(first.case_title)}</h3><div class="mini">${esc(first.case_category)} · <code>${esc(caseId)}</code></div></div><span class="tag">${rows.filter(r => r.status === 'completed').length}/${rows.length} completed</span></div>
        <div class="response-grid">${rows.map(r => `<div class="response-panel"><div class="response-panel-head"><span class="response-panel-name">${esc(r.model_id)} · ${esc(workflowLabel(r.workflow_id))}</span>${r.status === 'completed' ? scorePill(r.accuracy_score) : statusTag(r.status)}</div>
          ${r.status === 'completed' ? `<div class="response-copy">${esc(r.response || '(Empty response)')}</div><div class="mini" style="display:flex;flex-wrap:wrap;gap:9px;margin-top:10px"><span>Grounding ${r.grounding_score == null ? 'N/A' : `${fmtNum(r.grounding_score,0)}%`}</span><span>Tools ${r.tool_reliability_score == null ? 'N/A' : `${fmtNum(r.tool_reliability_score,0)}%`}</span><span>${fmtNum(r.latency_ms,0)} ms</span><span>Usage ${r.usage_reported ? 'reported' : 'unreported'}</span><span>Cost ${esc(r.cost_source || 'unknown')}</span></div>` : `<div class="failure-item">${esc(r.error || 'Provider call failed. See run error details.')}</div>`}
          ${(r.failure_analysis || []).length ? `<div class="failure-list">${r.failure_analysis.map(f => `<div class="failure-item"><strong>${esc(f.type)}:</strong> ${esc(f.message)}</div>`).join('')}</div>` : ''}
          ${(r.tool_calls || []).length ? `<details class="tool-log"><summary>${fmtNum(r.tool_calls.length)} tool call${r.tool_calls.length===1?'':'s'} · inspect trace</summary><pre>${esc(JSON.stringify(r.tool_calls, null, 2))}</pre></details>` : ''}
        </div>`).join('')}</div></div>`;
    }).join('');
  }

  async function renderRunDetail(view, runId) {
    const run = await api(`/api/runs/${encodeURIComponent(runId)}`);
    const finished = ['completed', 'completed_with_errors', 'failed'].includes(run.status);
    const total = run.case_count * (run.candidate_count || run.model_count);
    const progress = total ? Math.round(100 * Math.min(run.result_count, total) / total) : 0;
    const top = run.recommendation;
    const actions = `<button class="btn btn-secondary" data-action="refresh">${icon('refresh', 14)} Refresh</button><a class="btn btn-primary" href="#/new-run?dataset=${encodeURIComponent(run.dataset_id)}">${icon('plus', 14)} Rerun benchmark</a>`;
    view.innerHTML = `<div class="run-detail-header">${heading('BENCHMARK REPORT', run.name, `${run.dataset_name} · dataset v${run.dataset_version ?? '—'} · created ${dateFmt(run.created_at)}`, actions)}</div>
      ${finished && top ? `<div class="recommendation-card"><div class="recommendation-icon">${icon('spark', 21)}</div><div class="recommendation-content"><div class="recommendation-label">Evidence-based recommendation</div><h2>${esc(top.model_id)} · ${esc(workflowLabel(top.workflow_id))} leads on this benchmark</h2><p>${esc(top.reason)} ${esc(top.caveat)}</p></div><div class="recommendation-score"><strong>${fmtNum(top.composite_score,1)}</strong><span>Composite / 100</span></div></div>` : ''}
      ${!finished ? `<div class="run-progress" style="margin-bottom:18px"><div style="display:flex;justify-content:space-between;gap:10px;align-items:center"><div><strong style="font-size:12px">Benchmark in progress</strong><div class="mini" style="margin-top:3px">${run.status === 'queued' ? 'Waiting for execution slot…' : 'Real provider calls are running; completed cases are persisted as they finish.'}</div></div>${statusTag(run.status)}</div><div class="progress-track"><div class="progress-bar" style="width:${Math.max(5,progress)}%"></div></div><div class="mini">${fmtNum(run.result_count)} of ${fmtNum(total)} case evaluations recorded · this page refreshes automatically</div></div>` : ''}
      ${run.status === 'failed' && run.error ? `<div class="info-banner warning" style="margin-bottom:18px">${icon('info')}<div><strong>Run failed</strong><p>${esc(run.error)}</p></div></div>` : ''}
      ${resultStats(run)}
      <section class="card table-card" style="margin-top:0"><div class="card-head"><div><h2>Model comparison</h2><p class="subtle">Same dataset snapshot · temperature 0 · scores are rubric-based</p></div><span class="tag">${esc(run.config?.evaluator_version || 'proofbench-rubric-v1')}</span></div>${modelComparisonTable(run.model_summaries || [])}</section>
      <section class="card table-card"><div class="card-head"><div><h2>Case-by-case evidence</h2><p class="subtle">Read each answer, inspect failed checks, and expand raw tool traces.</p></div><span class="tag">${fmtNum(run.dataset_snapshot?.cases?.length || 0)} CASES</span></div>${groupedCaseResults(run.results || [], run.model_ids || [])}</section>
      <div class="info-banner" style="margin-top:18px">${icon('info')}<div><strong>How to interpret this report</strong><p>The composite score renormalizes the stated weights when a metric is not applicable and discounts for failed case calls. Grounding is configured evidence-anchor coverage, not a semantic entailment judge. Latency and cost efficiency are normalized within this run. Use the recommendation to select a pilot, then validate on broader production-representative tasks.</p></div></div>
      <div class="footer-note">Run ID: <code>${esc(run.id)}</code> · dataset version ${run.dataset_version ?? '—'} is snapshotted in this report.</div>`;
    if (!finished) schedulePoll(runId);
  }

  function schedulePoll(runId) {
    if (state.pollingRun === runId && state.pollingTimer) return;
    state.pollingRun = runId;
    state.pollingTimer = window.setTimeout(async () => {
      state.pollingTimer = null;
      if (getHash().path !== `/runs/${runId}`) return stopPolling();
      try { await renderRunDetail(document.getElementById('view'), runId); }
      catch (error) { toast('Unable to refresh run', error.message, 'error'); schedulePoll(runId); }
    }, 2200);
  }

  async function renderSettings(view) {
    const [settingsData, methodology] = await Promise.all([api('/api/settings'), api('/api/methodology')]);
    view.innerHTML = `${heading('WORKSPACE CONFIGURATION', 'Settings & methodology', 'Configure live providers on the server, understand the bundled rate card, and review exactly how every metric is computed.', `<a class="btn btn-secondary" href="/docs" target="_blank" rel="noreferrer">${icon('file', 14)} API docs ${icon('arrow', 11)}</a>`)}
      <div class="grid grid-2" style="align-items:start">
        <section class="card card-pad"><div style="display:flex;align-items:center;gap:10px;margin-bottom:4px"><span class="stat-icon">${icon('shield', 17)}</span><div><h2>Provider connections</h2><p class="subtle">Keys are read from server environment variables.</p></div></div>
          <div style="margin-top:19px">${settingsData.providers.map(p => `<div class="settings-provider-row"><div class="provider-logo ${providerClass(p.id)}">${esc(providerInitial(p.id))}</div><div class="settings-provider-copy"><strong>${esc(p.label)}</strong><span>${esc(p.description)}</span><span style="margin-top:5px">Environment: <code class="code-chip">${esc(p.env_key)}${p.id==='gemini'?' or GEMINI_API_KEY':''}</code></span></div><div class="settings-provider-action"><span class="tag ${p.configured?'mint':'amber'}">${p.configured?'Configured':'Not configured'}</span></div></div>`).join('')}</div>
          <div class="info-banner warning" style="margin-top:18px">${icon('info')}<div><strong>Do not paste secrets into the UI.</strong><p>Add credentials to your server-side <code>.env</code> file using <code>.env.example</code> as a guide, restart the app, and refresh. Secrets are not stored in SQLite or returned by the API.</p></div></div>
          <div style="margin-top:16px"><div class="field-label" style="margin-bottom:7px">Configure model IDs</div><p class="subtle" style="line-height:1.7">Set <code class="code-chip">PROOFBENCH_OPENAI_MODELS</code>, <code class="code-chip">PROOFBENCH_GEMINI_MODELS</code>, <code class="code-chip">PROOFBENCH_ANTHROPIC_MODELS</code>, or <code class="code-chip">PROOFBENCH_COMPATIBLE_MODELS</code> to match the model IDs enabled on your account or local endpoint.</p></div>
        </section>
        <section class="card card-pad"><div style="display:flex;align-items:center;gap:10px;margin-bottom:4px"><span class="stat-icon amber">${icon('zap', 17)}</span><div><h2>Rate card</h2><p class="subtle">USD per one million input / output tokens.</p></div></div>
          <div class="info-banner warning" style="margin:15px 0">${icon('info')}<div><strong>Bundled prices are illustrative estimates.</strong><p>Provider prices and model aliases change. Set a current, verified rate card using <code>PROOFBENCH_MODEL_PRICING_JSON</code> before using cost comparisons for budget approvals.</p></div></div>
          <div class="table-scroll"><table style="min-width:350px"><thead><tr><th>Model</th><th>Input</th><th>Output</th><th>Source</th></tr></thead><tbody>${settingsData.pricing.map(p => `<tr><td><span class="td-title">${esc(p.model_id)}</span></td><td>${p.pricing ? `$${fmtNum(p.pricing.input_per_1m,3)}` : '—'}</td><td>${p.pricing ? `$${fmtNum(p.pricing.output_per_1m,3)}` : '—'}</td><td><span class="tag ${p.source==='environment_override'?'mint':'amber'}">${p.source==='environment_override'?'Override':p.source==='bundled_estimate'?'Estimate':'Unpriced'}</span></td></tr>`).join('')}</tbody></table></div>
          <p class="mini" style="margin-top:14px">Example override: <code class="code-chip">{"gpt-4o-mini":{"input_per_1m":0.15,"output_per_1m":0.6}}</code> as JSON in the environment value. Restart after changing it.</p>
        </section>
      </div>
      <section class="card card-pad" style="margin-top:18px"><div style="display:flex;align-items:center;gap:10px;margin-bottom:5px"><span class="stat-icon mint">${icon('book', 17)}</span><div><h2>Metric definitions</h2><p class="subtle">Evaluator version ${esc(methodology.evaluator_version)} · methodology is exposed at <code>/api/methodology</code>.</p></div></div>
        <div class="methodology-list" style="margin-top:19px">${methodology.metrics.map(m => `<div class="methodology-item"><strong>${esc(m.label)}</strong><p>${esc(m.definition)}</p><p><em>Limit:</em> ${esc(m.caveat)}</p></div>`).join('')}</div>
        <div class="info-banner" style="margin-top:18px">${icon('target')}<div><strong>Composite score — 40 / 30 / 20 / 5 / 5</strong><p>Task accuracy 40%, grounding 30%, tool reliability 20%, latency efficiency 5%, and cost efficiency 5%. Weights renormalize if a metric is not applicable. Latency and cost efficiency are compared within the same run. Keep the individual metrics visible when making decisions.</p></div></div>
      </section>
      <div class="footer-note">ProofBench is designed for trusted internal evaluation. Before exposing it beyond localhost, add authentication, rate limits, and a deployment-specific secret manager.</div>`;
  }

  document.addEventListener('click', async (event) => {
    const button = event.target.closest('[data-action]');
    if (!button) return;
    const action = button.dataset.action;
    if (action === 'refresh') { event.preventDefault(); try { await route(); toast('View refreshed', 'Latest database state loaded.'); } catch (error) { toast('Refresh failed', error.message, 'error'); } }
    if (action === 'new-dataset') openDatasetEditor();
    if (action === 'edit-dataset') {
      try { const ds = await api(`/api/datasets/${encodeURIComponent(button.dataset.id)}`); openDatasetEditor(ds); }
      catch (error) { toast('Could not open dataset', error.message, 'error'); }
    }
    if (action === 'delete-dataset') {
      const ds = state.datasets.find(d => d.id === button.dataset.id);
      if (!ds || !window.confirm(`Delete dataset “${ds.name}”? Existing run reports will remain available because they store dataset snapshots.`)) return;
      try { await api(`/api/datasets/${encodeURIComponent(ds.id)}`, { method: 'DELETE' }); toast('Dataset deleted', ds.name); await route(); }
      catch (error) { toast('Delete failed', error.message, 'error'); }
    }
    if (action === 'open-run') { const id = button.dataset.id; if (id) location.hash = `#/runs/${id}`; }
    if (action === 'close-modal') document.getElementById('modal-root')?.remove();
    if (action === 'modal-backdrop' && event.target === button) document.getElementById('modal-root')?.remove();
  });

  document.addEventListener('change', (event) => {
    if (event.target.matches('input[name="model_ids"]') || event.target.matches('input[name="workflow_ids"]')) updateRunPreview();
    if (event.target.matches('#dataset-id')) updateRunPreview();
  });

  document.addEventListener('submit', async (event) => {
    if (event.target.id === 'start-run-form') { event.preventDefault(); await handleStartRun(event.target); }
    if (event.target.id === 'dataset-editor-form') { event.preventDefault(); await submitDatasetForm(event.target); }
  });

  window.addEventListener('hashchange', route);
  window.addEventListener('keydown', (event) => { if (event.key === 'Escape') document.getElementById('modal-root')?.remove(); });

  async function init() {
    try {
      await loadCommon();
      if (!location.hash) location.hash = '#/dashboard';
      else await route();
    } catch (error) {
      root.className = 'app-loading';
      root.innerHTML = `<div class="loading-mark"><span class="mark-dot"></span>ProofBench</div><p>Could not connect to the local API: ${esc(error.message)}</p><button class="btn btn-primary" id="retry-init">Try again</button>`;
      document.getElementById('retry-init')?.addEventListener('click', init);
    }
  }
  init();
})();
