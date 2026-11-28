'use strict';
// The catalog: validation before anything is drawn, the rows and filters of the sidebar, the status of a
// plugin in each host, the split button, and the view models of both webviews. No `vscode` import.

const { mark, percent, scoreRole } = require('./theme');
const { NAME, VERB, EXE, display, build } = require('./commands');

const MAX_BYTES = 1024 * 1024;
const LOW_CONFIDENCE = 3;
const KINDS = ['fires', 'quiet', 'behavior'];
const KIND_LABEL = { fires: 'Must fire', quiet: 'Must stay quiet', behavior: 'Behavior' };
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const GITHUB_TREE = 'https://github.com/eurus-labs/Skills/tree/main/plugins/';
const CHANGELOG = 'https://github.com/eurus-labs/Skills/blob/main/CHANGELOG.md';
const HELP_TEXT = 'An eval runs a skill on fixed test prompts and grades what the agent did. The score is the mean ' +
  'over the skill’s cases, each from its newest finished run on the chosen host. Fewer than 3 cases is marked ' +
  'low confidence. Runs that stopped early or errored are not counted.';

// --- validation ------------------------------------------------------------------------------------------

function shown(value) {
  const text = String(value);
  return text.length > 40 ? text.slice(0, 40) + '…' : text;
}

function text(value) {
  return typeof value === 'string' ? value : '';
}

function count(value) {
  return typeof value === 'number' && isFinite(value) && value >= 0 ? value : 0;
}

function score(value) {
  return typeof value === 'number' && isFinite(value) ? value : null;
}

// A new object holding only the known fields, with the types the views rely on, so nothing else a file holds
// reaches the webviews. Returns {ok: true, catalog} or {ok: false, error}.
function validateCatalog(raw) {
  const fail = (error) => ({ ok: false, error });
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return fail('The catalog is not a JSON object');
  if (raw.schemaVersion !== 1) return fail('The catalog has schemaVersion ' + shown(raw.schemaVersion) + ', and only 1 is supported');
  if (!Array.isArray(raw.hosts) || !raw.hosts.length) return fail('The catalog lists no hosts');
  if (!Array.isArray(raw.plugins)) return fail('The catalog lists no plugins');
  const market = raw.marketplace && typeof raw.marketplace === 'object' ? raw.marketplace : {};
  const hosts = [];
  for (const host of raw.hosts) {
    const id = host && host.id;
    if (typeof id !== 'string' || !NAME.test(id)) return fail('Host id `' + shown(id) + '` is not allowed');
    hosts.push({ id, label: text(host.label) || id });
  }
  const hostIds = hosts.map((h) => h.id);
  const plugins = [];
  for (const plugin of raw.plugins) {
    const name = plugin && plugin.name;
    if (typeof name !== 'string' || !NAME.test(name)) return fail('Plugin name `' + shown(name) + '` is not allowed');
    const skills = (Array.isArray(plugin.skills) ? plugin.skills : []).filter((s) => s && typeof s === 'object').map((s) => {
      const evals = s.evals && typeof s.evals === 'object' ? s.evals : {};
      const byHost = {};
      hostIds.forEach((id) => {
        const h = evals.hosts && evals.hosts[id];
        if (h && typeof h === 'object' && score(h.score) !== null) {
          byHost[id] = { cases: count(h.cases), score: score(h.score), latest: text(h.latest) };
        }
      });
      return { name: text(s.name), description: text(s.description), evals: { cases: count(evals.cases), hosts: byHost } };
    });
    const cases = [];
    for (const c of Array.isArray(plugin.cases) ? plugin.cases : []) {
      const caseName = c && c.name;
      if (typeof caseName !== 'string' || !NAME.test(caseName)) return fail('Case name `' + shown(caseName) + '` is not allowed');
      const latest = {};
      hostIds.forEach((id) => {
        const l = c.latest && c.latest[id];
        if (l && typeof l === 'object') {
          latest[id] = { stamp: text(l.stamp), score: score(l.score), runs: count(l.runs), trusted: l.trusted === true };
        }
      });
      cases.push({ name: caseName, kind: KINDS.indexOf(c.kind) >= 0 ? c.kind : 'fires',
        skills: (Array.isArray(c.skills) ? c.skills : []).filter((s) => typeof s === 'string'),
        description: text(c.description), latest });
    }
    const runs = (Array.isArray(plugin.runs) ? plugin.runs : []).filter((r) => r && typeof r === 'object').map((r) => ({
      stamp: text(r.stamp), host: text(r.host), score: score(r.score), cases: count(r.cases) }));
    plugins.push({ name, version: text(plugin.version), description: text(plugin.description), skills, cases, runs });
  }
  let featured = null;
  const f = raw.featured;
  if (f && typeof f === 'object' && typeof f.plugin === 'string' && NAME.test(f.plugin)) {
    featured = { plugin: f.plugin, note: text(f.note), text: text(f.text) };
  }
  return { ok: true, catalog: { schemaVersion: 1,
    marketplace: { name: text(market.name), version: text(market.version), source: text(market.source) },
    hosts, featured, plugins } };
}

// Text of a catalog file to a validated catalog; rejects over 1 MB, bad JSON, another schemaVersion, unsafe names.
function parseCatalog(body) {
  const textBody = String(body);
  if (Buffer.byteLength(textBody, 'utf8') > MAX_BYTES) return { ok: false, error: 'The catalog is over 1 MB' };
  let raw;
  try {
    raw = JSON.parse(textBody);
  } catch (error) {
    return { ok: false, error: 'The catalog is not valid JSON' };
  }
  return validateCatalog(raw);
}

// Fetch the catalog text. Only https:// URLs; the body is cut off past 1 MB; no redirect is followed.
// `get` is https.get, replaceable in tests. Resolves the text, or rejects with {kind: 'rejected' | 'offline', message}.
function fetchCatalogText(url, get, timeoutMs) {
  return new Promise((resolve, reject) => {
    if (typeof url !== 'string' || !/^https:\/\/[^\s]+$/.test(url)) {
      reject({ kind: 'rejected', message: 'The catalog URL must start with https://' });
      return;
    }
    let done = false;
    const finish = (fn, value) => {
      if (!done) {
        done = true;
        fn(value);
      }
    };
    const req = get(url, { headers: { Accept: 'application/json', 'User-Agent': 'eurus-skills-vscode' } }, (res) => {
      if (res.statusCode !== 200) {
        res.resume();
        finish(reject, { kind: 'offline', message: 'HTTP ' + res.statusCode });
        return;
      }
      const chunks = [];
      let size = 0;
      res.on('data', (chunk) => {
        size += chunk.length;
        if (size > MAX_BYTES) {
          res.destroy();
          finish(reject, { kind: 'rejected', message: 'The catalog is over 1 MB' });
          return;
        }
        chunks.push(chunk);
      });
      res.on('end', () => finish(resolve, Buffer.concat(chunks).toString('utf8')));
      res.on('error', (error) => finish(reject, { kind: 'offline', message: error.message }));
    });
    req.on('error', (error) => finish(reject, { kind: 'offline', message: error.message }));
    req.setTimeout(timeoutMs || 15000, () => {
      req.destroy();
      finish(reject, { kind: 'offline', message: 'timed out' });
    });
  });
}

// --- dates, versions -------------------------------------------------------------------------------------

// "26 Nov" from a run stamp (2026-11-26T06-55-42-435Z) or an ISO date.
function day(value) {
  const found = /^(\d{4})-(\d\d)-(\d\d)/.exec(String(value || ''));
  return found ? Number(found[3]) + ' ' + MONTHS[Number(found[2]) - 1] : '';
}

// -1, 0 or 1; NaN when either side is not a version.
function compareVersions(a, b) {
  const parse = (v) => {
    const found = /^(\d+)\.(\d+)\.(\d+)/.exec(String(v || ''));
    return found ? [Number(found[1]), Number(found[2]), Number(found[3])] : null;
  };
  const x = parse(a);
  const y = parse(b);
  if (!x || !y) return String(a) === String(b) ? 0 : NaN;
  for (let i = 0; i < 3; i += 1) {
    if (x[i] !== y[i]) return x[i] < y[i] ? -1 : 1;
  }
  return 0;
}

function plural(n, one, many) {
  return n + ' ' + (n === 1 ? one : many);
}

// --- hosts and statuses ----------------------------------------------------------------------------------

function hostLabel(catalog, id) {
  const found = catalog.hosts.find((h) => h.id === id);
  return found ? found.label : id;
}

// What a host's listing says: {kind: 'loading' | 'missing-exe' | 'no-marketplace' | 'error' | 'ready', plugins}.
function hostInfo(installed, host) {
  const entry = installed && installed[host];
  if (!entry) return { kind: 'loading', plugins: {} };
  return { kind: entry.state, plugins: entry.plugins || {}, error: entry.error || null };
}

// A plugin's status in one host. key: ok, update, off, none (not installed), unknown (state not known).
function pluginStatus(plugin, info) {
  if (info.kind === 'missing-exe' || info.kind === 'loading' || info.kind === 'error') {
    return { key: 'unknown', action: null, text: info.kind === 'loading' ? 'Checking…' : 'Install state unknown', installed: null };
  }
  if (info.kind === 'no-marketplace') {
    return { key: 'none', action: null, blocked: true, text: 'Register first to install', installed: null };
  }
  const have = info.plugins[plugin.name];
  if (!have) return { key: 'none', action: 'install', text: 'Not installed', installed: null };
  const version = have.version;
  if (!have.enabled) return { key: 'off', action: 'enable', text: 'Disabled · v' + version, installed: version };
  if (compareVersions(version, plugin.version) < 0) {
    return { key: 'update', action: 'update', text: 'v' + version + ' installed · v' + plugin.version + ' available', installed: version };
  }
  return { key: 'ok', action: null, text: 'Installed · v' + version, installed: version };
}

const RANK = { update: 0, off: 1, ok: 2, none: 3, unknown: 3 };

// The eval summary of a plugin on one host, or null when no trusted run exists there.
function summary(plugin, host) {
  const withScore = plugin.skills.filter((s) => s.evals.hosts[host]);
  if (!withScore.length) return null;
  let cases = 0;
  let sum = 0;
  let latest = '';
  withScore.forEach((s) => {
    const h = s.evals.hosts[host];
    cases += h.cases;
    sum += h.score * h.cases;
    if (h.latest > latest) latest = h.latest;
  });
  const total = plugin.cases.length || plugin.skills.reduce((n, s) => n + s.evals.cases, 0);
  const trustedCases = plugin.cases.filter((c) => c.latest[host] && c.latest[host].trusted).length;
  const run = trustedCases || cases;
  return { score: cases ? sum / cases : 0, cases: run, total, latest };
}

function skillCount(plugin) {
  return plural(plugin.skills.length, 'skill', 'skills');
}

// One sidebar row.
function rowFor(plugin, status, evalSummary, hostName) {
  let sub;
  if (status.key === 'update') sub = 'v' + status.installed + ' → v' + plugin.version;
  else if (status.key === 'off') sub = 'Disabled';
  else if (status.key === 'unknown' && status.text !== 'Checking…') sub = status.text;
  else if (status.blocked) sub = status.text;
  else sub = skillCount(plugin) + ' · v' + plugin.version;
  const showAction = status.action !== null || status.blocked === true;
  const action = status.blocked ? 'install' : status.action;
  return {
    name: plugin.name, mark: mark(plugin.name), sub, status: status.key,
    pill: showAction ? { label: status.key === 'none' ? 'Get' : VERB[action], action, primary: status.key === 'update', disabled: status.blocked === true } : null,
    score: !showAction && evalSummary ? { text: percent(evalSummary.score) + '%', role: scoreRole(evalSummary.score),
      title: 'Eval on ' + hostName + ': ' + percent(evalSummary.score) + '% over ' + plural(evalSummary.cases, 'case', 'cases') +
        (evalSummary.cases < LOW_CONFIDENCE ? ', low confidence' : '') } : null,
    noScore: !showAction && !evalSummary
  };
}

function matches(plugin, query) {
  const q = String(query || '').trim().toLowerCase();
  if (!q) return true;
  return plugin.name.toLowerCase().indexOf(q) >= 0 || plugin.description.toLowerCase().indexOf(q) >= 0 ||
    plugin.skills.some((s) => s.name.toLowerCase().indexOf(q) >= 0);
}

// Rows for a host: filtered by the tab and the query, ordered by updates, disabled, installed, not installed.
function listRows(catalog, installed, host, filter, query) {
  const info = hostInfo(installed, host);
  const name = hostLabel(catalog, host);
  const all = catalog.plugins.map((plugin) => {
    const status = pluginStatus(plugin, info);
    return { plugin, status, row: rowFor(plugin, status, summary(plugin, host), name) };
  });
  const counts = {
    all: all.length,
    installed: all.filter((x) => ['ok', 'off', 'update'].indexOf(x.status.key) >= 0).length,
    updates: all.filter((x) => x.status.key === 'update').length
  };
  const wanted = (x) => filter === 'installed' ? ['ok', 'off', 'update'].indexOf(x.status.key) >= 0
    : filter === 'updates' ? x.status.key === 'update' : true;
  const rows = all.filter((x) => matches(x.plugin, query) && wanted(x)).sort((a, b) => RANK[a.status.key] - RANK[b.status.key]);
  return { rows: rows.map((x) => x.row), counts, updatable: all.filter((x) => x.status.key === 'update').map((x) => x.plugin.name) };
}

// The split button of the plugin page. Its main part runs the pending action for the chosen host, else for the other.
function splitAction(catalog, statuses, chosenHost) {
  const pending = catalog.hosts.filter((h) => statuses[h.id] && statuses[h.id].action);
  const main = pending.find((h) => h.id === chosenHost) || pending[0] || null;
  const menu = [];
  catalog.hosts.forEach((h) => {
    const st = statuses[h.id];
    if (!st) return;
    if (st.action) menu.push({ label: VERB[st.action], action: st.action, host: h.id, hostLabel: h.label });
    if (st.key !== 'none' && st.key !== 'unknown') menu.push({ label: 'Uninstall', action: 'uninstall', host: h.id, hostLabel: h.label });
  });
  return {
    host: main ? main.id : null,
    action: main ? statuses[main.id].action : null,
    label: main ? VERB[statuses[main.id].action] + ' in ' + main.label : 'Up to date everywhere',
    note: main ? 'Runs in a terminal · you confirm first' : 'Nothing is pending',
    menu
  };
}

// --- the sidebar -----------------------------------------------------------------------------------------

function sourceLine(source) {
  if (!source) return 'No catalog yet';
  if (source.kind === 'checkout') return 'Catalog from this checkout';
  return 'Catalog from GitHub' + (source.date ? ' · ' + day(source.date) : '');
}

// The notices that sit above the list: marketplace not registered, host missing, offline, rejected.
function notices(state, catalog) {
  const found = [];
  const host = state.ui.host;
  const info = hostInfo(state.installed, host);
  const label = hostLabel(catalog, host);
  const other = catalog.hosts.find((h) => h.id !== host);
  if (state.problem && state.problem.kind === 'offline') {
    found.push({ kind: 'offline', title: 'Showing the catalog from ' + (day(state.problem.date) || 'an earlier visit'),
      body: 'GitHub could not be reached. Install state is live; versions may be behind.', buttons: [{ label: 'Try again', act: 'refresh' }] });
  }
  if (state.problem && state.problem.kind === 'rejected') {
    found.push({ kind: 'rejected', title: 'The downloaded catalog was rejected',
      body: state.problem.message + '.' + (state.problem.date ? ' Still showing the catalog from ' + day(state.problem.date) + '.' : ''),
      buttons: [{ label: 'Try again', act: 'refresh' }, { label: 'Settings', act: 'settings-catalog', quiet: true }] });
  }
  if (info.kind === 'missing-exe') {
    found.push({ kind: 'no-exe', code: EXE[host],
      title: ' is not on PATH',
      body: 'Install ' + label + ', then refresh. The catalog' + (other ? ' and ' + other.label : '') + ' keep working.', buttons: [] });
  }
  if (info.kind === 'no-marketplace') {
    const github = display(build(host, 'marketplace-add', { source: 'github' }));
    found.push({ kind: 'register', title: 'Connect ' + label + ' to eurus-labs',
      body: 'One-time setup. Afterwards every plugin installs with one click.', command: github,
      buttons: [{ label: 'Register from GitHub', act: 'register', source: 'github', primary: true }]
        .concat(state.inRepo ? [{ label: 'Use this checkout', act: 'register', source: 'checkout' }] : []) });
  }
  return found;
}

function sidebarModel(state) {
  const catalog = state.catalog;
  const ui = state.ui;
  if (!catalog) {
    return { empty: true, title: 'Eurus Skills', problem: state.problem || null, loading: !state.problem,
      q: ui.q, footer: { source: sourceLine(null), version: '' } };
  }
  const list = listRows(catalog, state.installed, ui.host, ui.filter, ui.q);
  const searching = ui.q.trim() !== '' || ui.filter !== 'all';
  const featuredPlugin = catalog.featured && catalog.plugins.find((p) => p.name === catalog.featured.plugin);
  return {
    empty: false, q: ui.q, selected: ui.selected,
    hosts: catalog.hosts.map((h) => ({ id: h.id, label: h.label, pressed: h.id === ui.host })),
    featured: !searching && featuredPlugin ? { plugin: featuredPlugin.name, note: catalog.featured.note, text: catalog.featured.text } : null,
    filters: [['all', 'All'], ['installed', 'Installed'], ['updates', 'Updates']].map((f) => ({
      id: f[0], label: f[1], count: list.counts[f[0]], selected: ui.filter === f[0], hot: f[0] === 'updates' && list.counts.updates > 0 })),
    updateAll: list.updatable.length ? { count: list.updatable.length, text: plural(list.updatable.length, 'update', 'updates') + ' available' } : null,
    notices: notices(state, catalog),
    rows: list.rows,
    noMatch: !list.rows.length && ui.q.trim() !== '' ? ui.q.trim() : '',
    footer: { source: sourceLine(state.source), version: catalog.marketplace.version }
  };
}

// --- the plugin page -------------------------------------------------------------------------------------

function caseCounts(cases) {
  const n = (kind) => cases.filter((c) => c.kind === kind).length;
  return n('fires') + ' must fire · ' + n('quiet') + ' must stay quiet · ' + n('behavior') + ' behavior';
}

// The result column of a case row on the eval host, with a running job's state laid over it.
function caseResult(c, evalHost, item) {
  if (item && (item.status === 'running' || item.status === 'queued' || item.status === 'stopped')) {
    return { text: item.status === 'running' ? 'Running' : item.status === 'queued' ? 'Queued' : 'Stopped',
      role: item.status === 'running' ? 'text' : 'dim', pulse: item.status === 'running', meta: '' };
  }
  if (item && (item.status === 'passed' || item.status === 'failed') && item.score !== null) {
    return { text: percent(item.score) + '%', role: scoreRole(item.score), pulse: false, meta: 'just now' };
  }
  const latest = c.latest[evalHost];
  if (!latest) return { text: 'Not run', role: 'dim', pulse: false, meta: '' };
  const when = day(latest.stamp);
  if (!latest.trusted) {
    return { text: latest.score === null ? 'error' : 'partial', role: 'dim', pulse: false,
      meta: plural(latest.runs, 'run', 'runs') + (when ? ' · ' + when : '') };
  }
  return { text: percent(latest.score) + '%', role: scoreRole(latest.score), pulse: false,
    meta: plural(latest.runs, 'run', 'runs') + (when ? ' · ' + when : '') };
}

function pluginModel(state) {
  const catalog = state.catalog;
  const ui = state.ui;
  const plugin = catalog.plugins.find((p) => p.name === ui.selected) || catalog.plugins[0];
  if (!plugin) return null;
  const evalHost = catalog.hosts.some((h) => h.id === ui.evalHost) ? ui.evalHost : catalog.hosts[0].id;
  const evalLabel = hostLabel(catalog, evalHost);
  const statuses = {};
  catalog.hosts.forEach((h) => { statuses[h.id] = pluginStatus(plugin, hostInfo(state.installed, h.id)); });
  const split = splitAction(catalog, statuses, ui.host);
  const sum = summary(plugin, evalHost);
  const job = state.job;
  const jobRunning = !!(job && job.view && job.view.running);
  const items = {};
  if (job && job.plan.plugin === plugin.name && job.plan.host === evalHost) {
    job.view.items.forEach((i) => { items[i.name] = i; });
  }
  const contributor = state.inRepo && plugin.cases.length > 0;
  const skills = plugin.skills.map((s) => {
    const r = s.evals.hosts[evalHost];
    const tied = plugin.cases.filter((c) => c.skills.indexOf(s.name) >= 0);
    const open = contributor && !!ui.expanded[s.name] && tied.length > 0;
    const low = !!r && r.cases < LOW_CONFIDENCE;
    return {
      name: s.name, description: s.description, canExpand: contributor && tied.length > 0, open,
      pct: r ? percent(r.score) + '%' : '—', barPct: r ? Math.max(2, percent(r.score)) : 0, role: r ? scoreRole(r.score) : 'dim',
      meta: r ? r.cases + '/' + s.evals.cases + ' · ' + day(r.latest) + (low ? ' · low confidence' : '') : 'Not run on ' + evalLabel,
      low, caseCount: tied.length, runLabel: 'Run ' + plural(tied.length, 'case', 'cases'), cases: tied.map((c) => {
        const res = caseResult(c, evalHost, items[c.name]);
        return { name: c.name, kind: c.kind, kindLabel: KIND_LABEL[c.kind], description: c.description, result: res };
      })
    };
  });
  const runs = plugin.runs.map((r, i) => ({
    pct: r.score === null ? '—' : percent(r.score) + '%', barPct: r.score === null ? 0 : Math.max(4, percent(r.score)),
    role: r.score === null ? 'dim' : scoreRole(r.score), when: day(r.stamp) + ' #' + (i + 1), cases: plural(r.cases, 'case', 'cases'),
    title: r.host + ' · ' + r.stamp }));
  const tabs = [['skills', 'Skills', plugin.skills.length], ['runs', 'Runs', plugin.runs.length], ['install', 'Install', catalog.hosts.length]]
    .map((t) => ({ id: t[0], label: t[1], count: t[2], selected: ui.section === t[0] }));
  return {
    name: plugin.name, mark: mark(plugin.name), version: plugin.version, description: plugin.description,
    marketplace: catalog.marketplace.name || 'eurus-labs',
    links: { readme: GITHUB_TREE + plugin.name, changelog: CHANGELOG },
    pills: catalog.hosts.filter((h) => ['ok', 'update', 'off'].indexOf(statuses[h.id].key) >= 0).map((h) => ({
      key: statuses[h.id].key, text: { ok: 'Installed in ', update: 'Update available in ', off: 'Disabled in ' }[statuses[h.id].key] + h.label })),
    split: Object.assign({ open: ui.menuOpen }, split),
    evalHosts: catalog.hosts.map((h) => ({ id: h.id, label: h.label, pressed: h.id === evalHost })),
    evalHostLabel: evalLabel, help: ui.help, helpText: HELP_TEXT,
    eval: sum ? {
      has: true, score: percent(sum.score) + '%', pct: percent(sum.score), role: scoreRole(sum.score),
      note: sum.cases < LOW_CONFIDENCE ? 'low confidence' : 'mean of ' + plural(sum.cases, 'case', 'cases'), low: sum.cases < LOW_CONFIDENCE,
      kpis: [
        { label: 'CASES RUN', value: String(sum.cases), unit: ' / ' + sum.total, note: 'trusted runs only' },
        { label: 'LAST RUN', value: day(sum.latest).split(' ')[0], unit: ' ' + day(sum.latest).split(' ')[1],
          note: plural(plugin.runs.length, 'run', 'runs') + ' in the archive' },
        { label: 'SKILLS', value: String(plugin.skills.length), unit: '', note: plugin.skills.map((s) => s.name.split('-')[0]).join(' · ') }
      ]
    } : { has: false, title: 'No ' + evalLabel + ' run in the archive yet',
      body: 'Switch to the other host to see its scores.' + (state.inRepo ? ' Run a case from the Skills tab to add one.' : '') },
    tabs, section: ui.section, skills, runs,
    contributor: contributor ? { summary: caseCounts(plugin.cases), runAll: plugin.cases.length,
      runAllLabel: 'Run all ' + plugin.cases.length + ' cases', disabled: jobRunning } : null,
    engineError: contributor ? state.engineError || null : null,
    jobRunning,
    install: catalog.hosts.map((h) => {
      const st = statuses[h.id];
      const info = hostInfo(state.installed, h.id);
      const canRun = st.key !== 'unknown' && !st.blocked;
      const primary = st.action ? { label: VERB[st.action], action: st.action, disabled: !canRun }
        : st.blocked || st.key === 'unknown' ? { label: 'Install', action: 'install', disabled: true } : null;
      return { id: h.id, label: h.label, status: info.kind === 'missing-exe' ? EXE[h.id] + ' is not on PATH' : st.text, dotRole: st.key,
        command: canRun ? display(build(h.id, st.action || 'uninstall', { plugin: plugin.name })) : display({ exe: EXE[h.id], args: ['plugin', 'install', plugin.name + '@eurus-labs'] }),
        canUninstall: st.key !== 'none' && st.key !== 'unknown', primary, upToDate: st.key === 'ok' };
    })
  };
}

module.exports = { MAX_BYTES, LOW_CONFIDENCE, KIND_LABEL, HELP_TEXT, validateCatalog, parseCatalog, fetchCatalogText, day, compareVersions,
  hostInfo, pluginStatus, summary, rowFor, matches, listRows, splitAction, sourceLine, notices, sidebarModel, caseResult,
  pluginModel, caseCounts, hostLabel, plural };
