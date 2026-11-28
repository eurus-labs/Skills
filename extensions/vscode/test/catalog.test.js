'use strict';
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const { EventEmitter } = require('events');

const cat = require('../src/catalog');
const { sample, installed } = require('./fixture');

const entry = (plugins) => ({ state: 'ready', marketplace: 'eurus-labs/Skills', plugins, error: null });
const have = (version, enabled) => ({ version, enabled: enabled !== false });

function state(overrides) {
  return Object.assign({
    catalog: sample(), installed: installed(), inRepo: false, source: { kind: 'github', date: '2026-11-26T10:00:00Z' }, problem: null, job: null, engineError: null,
    ui: { host: 'claude', filter: 'all', q: '', selected: 'planning', evalHost: 'claude', section: 'skills', menuOpen: false, help: false, expanded: {} }
  }, overrides);
}

// --- validation ---

test('the committed catalog.json passes validation', () => {
  const text = fs.readFileSync(path.join(__dirname, '..', '..', '..', 'catalog.json'), 'utf8');
  const result = cat.parseCatalog(text);
  assert.strictEqual(result.ok, true, result.error);
  assert.strictEqual(result.catalog.plugins.length, 9);
  assert.strictEqual(result.catalog.plugins.reduce((n, p) => n + p.skills.length, 0), 18);
});

test('a catalog over 1 MB is rejected before it is parsed', () => {
  const big = JSON.stringify(Object.assign(sample(), { padding: 'x'.repeat(cat.MAX_BYTES) }));
  const result = cat.parseCatalog(big);
  assert.strictEqual(result.ok, false);
  assert.match(result.error, /over 1 MB/);
});

test('another schemaVersion is rejected', () => {
  for (const version of [2, 0, '1', undefined]) {
    const result = cat.parseCatalog(JSON.stringify(Object.assign(sample(), { schemaVersion: version })));
    assert.strictEqual(result.ok, false, String(version));
    assert.match(result.error, /schemaVersion/);
  }
});

test('a plugin named a;rm -rf or ../x is rejected, with the name in the reason', () => {
  for (const name of ['a;rm -rf', '../x', 'Upper', 'a b', '$(x)', '']) {
    const doc = sample();
    doc.plugins[1].name = name;
    const result = cat.parseCatalog(JSON.stringify(doc));
    assert.strictEqual(result.ok, false, name);
    assert.strictEqual(result.error, 'Plugin name `' + name + '` is not allowed');
  }
});

test('a case name or a host id that is not a name is rejected too', () => {
  const badCase = sample();
  badCase.plugins[0].cases[0].name = '../../etc/passwd';
  assert.match(cat.parseCatalog(JSON.stringify(badCase)).error, /Case name `\.\.\/\.\.\/etc\/passwd` is not allowed/);
  const badHost = sample();
  badHost.hosts[0].id = 'x;y';
  assert.match(cat.parseCatalog(JSON.stringify(badHost)).error, /Host id `x;y` is not allowed/);
});

test('text that is not a catalog is rejected', () => {
  for (const text of ['not json', '[]', 'null', '{}', JSON.stringify(Object.assign(sample(), { plugins: 'x' }))]) {
    assert.strictEqual(cat.parseCatalog(text).ok, false, text);
  }
});

test('validation keeps only known fields, so nothing else in a file reaches a view', () => {
  const doc = sample();
  doc.extra = '<script>';
  doc.plugins[0].onclick = 'x';
  const result = cat.parseCatalog(JSON.stringify(doc).replace('"schemaVersion"', '"__proto__": {"polluted": true}, "schemaVersion"'));
  assert.strictEqual(result.ok, true);
  assert.strictEqual(result.catalog.extra, undefined);
  assert.strictEqual(result.catalog.plugins[0].onclick, undefined);
  assert.strictEqual({}.polluted, undefined);
});

test('a featured plugin with an unsafe name is dropped', () => {
  const doc = sample();
  doc.featured.plugin = 'a;b';
  assert.strictEqual(cat.parseCatalog(JSON.stringify(doc)).catalog.featured, null);
});

// --- fetching ---

function fakeGet(status, chunks, error) {
  return (url, options, callback) => {
    const req = new EventEmitter();
    req.setTimeout = () => {};
    req.destroy = () => {};
    process.nextTick(() => {
      if (error) { req.emit('error', new Error(error)); return; }
      const res = new EventEmitter();
      res.statusCode = status;
      res.resume = () => {};
      res.destroy = () => {};
      callback(res);
      chunks.forEach((c) => res.emit('data', Buffer.from(c)));
      res.emit('end');
    });
    return req;
  };
}

test('only an https:// URL is fetched', async () => {
  for (const url of ['http://example.com/catalog.json', 'file:///etc/passwd', 'ftp://x', '', undefined]) {
    await assert.rejects(cat.fetchCatalogText(url, fakeGet(200, ['{}'])), (e) => e.kind === 'rejected' && /https/.test(e.message), String(url));
  }
});

test('a 200 answer gives the text; an error status or a network error is offline', async () => {
  assert.strictEqual(await cat.fetchCatalogText('https://x.test/c.json', fakeGet(200, ['{"a":', '1}'])), '{"a":1}');
  await assert.rejects(cat.fetchCatalogText('https://x.test/c.json', fakeGet(404, [])), (e) => e.kind === 'offline');
  await assert.rejects(cat.fetchCatalogText('https://x.test/c.json', fakeGet(0, [], 'getaddrinfo ENOTFOUND')), (e) => e.kind === 'offline' && /ENOTFOUND/.test(e.message));
});

test('a body past 1 MB is cut off and rejected', async () => {
  await assert.rejects(cat.fetchCatalogText('https://x.test/c.json', fakeGet(200, ['x'.repeat(cat.MAX_BYTES), 'y'])), (e) => e.kind === 'rejected' && /1 MB/.test(e.message));
});

// --- statuses, rows, order ---

test('a row shows Get, Update, Enable or the score for not installed, older, disabled and up to date', () => {
  const s = state({ installed: installed(entry({ planning: have('0.1.0'), docs: have('1.8.0'), review: have('0.3.0', false) })) });
  const { rows } = cat.listRows(s.catalog, s.installed, 'claude', 'all', '');
  const by = Object.fromEntries(rows.map((r) => [r.name, r]));
  assert.strictEqual(by.testing.pill.label, 'Get');
  assert.strictEqual(by.testing.pill.action, 'install');
  assert.strictEqual(by.docs.pill.label, 'Update');
  assert.strictEqual(by.docs.pill.primary, true);
  assert.strictEqual(by.docs.sub, 'v1.8.0 → v1.9.0');
  assert.strictEqual(by.review.pill.label, 'Enable');
  assert.strictEqual(by.review.sub, 'Disabled');
  assert.strictEqual(by.planning.pill, null);
  assert.strictEqual(by.planning.score.text, '82%', 'the mean over 6 cases: (0.98 x 4 + 0.5 x 2) / 6');
  assert.strictEqual(by.planning.score.role, 'warn');
  assert.strictEqual(by.planning.sub, '2 skills · v0.1.0');
});

test('rows are ordered updates, then disabled, then installed, then not installed', () => {
  const s = state({ installed: installed(entry({ planning: have('0.1.0'), docs: have('1.8.0'), review: have('0.3.0', false), 'skill-authoring': have('0.1.2') })) });
  const { rows } = cat.listRows(s.catalog, s.installed, 'claude', 'all', '');
  assert.deepStrictEqual(rows.map((r) => r.name), ['docs', 'review', 'planning', 'skill-authoring', 'testing']);
});

test('a newer installed version is not an update, and an unreadable one is not either', () => {
  assert.strictEqual(cat.compareVersions('0.1.0', '0.2.0'), -1);
  assert.strictEqual(cat.compareVersions('1.10.0', '1.9.0'), 1);
  assert.strictEqual(cat.compareVersions('1.9.0', '1.9.0'), 0);
  assert.ok(Number.isNaN(cat.compareVersions('weird', '1.0.0')));
  const s = state({ installed: installed(entry({ docs: have('2.0.0'), testing: have(null) })) });
  const keys = Object.fromEntries(cat.listRows(s.catalog, s.installed, 'claude', 'all', '').rows.map((r) => [r.name, r.status]));
  assert.strictEqual(keys.docs, 'ok');
  assert.strictEqual(keys.testing, 'ok');
});

test('the host switch decides the install state shown', () => {
  const s = state({ installed: installed(entry({}), entry({ docs: have('1.9.0') })) });
  const claude = cat.listRows(s.catalog, s.installed, 'claude', 'installed', '');
  const copilot = cat.listRows(s.catalog, s.installed, 'copilot', 'installed', '');
  assert.strictEqual(claude.rows.length, 0);
  assert.deepStrictEqual(copilot.rows.map((r) => r.name), ['docs']);
  assert.deepStrictEqual(copilot.counts, { all: 5, installed: 1, updates: 0 });
});

test('filters and counts: Installed and Updates, with search over names, descriptions and skill names', () => {
  const s = state({ installed: installed(entry({ planning: have('0.1.0'), docs: have('1.8.0') })) });
  assert.deepStrictEqual(cat.listRows(s.catalog, s.installed, 'claude', 'all', '').counts, { all: 5, installed: 2, updates: 1 });
  assert.deepStrictEqual(cat.listRows(s.catalog, s.installed, 'claude', 'updates', '').rows.map((r) => r.name), ['docs']);
  assert.deepStrictEqual(cat.listRows(s.catalog, s.installed, 'claude', 'all', 'group-epics').rows.map((r) => r.name), ['planning']);
  assert.deepStrictEqual(cat.listRows(s.catalog, s.installed, 'claude', 'all', 'REQUIREMENT').rows.map((r) => r.name), ['planning']);
  assert.deepStrictEqual(cat.listRows(s.catalog, s.installed, 'claude', 'all', 'zzz').rows, []);
  assert.deepStrictEqual(cat.listRows(s.catalog, s.installed, 'claude', 'all', 'document-codebase').rows.map((r) => r.name), ['docs']);
});

test('a host that is not on PATH reads "Install state unknown" and offers no install', () => {
  const s = state({ installed: installed({ state: 'missing-exe', plugins: {} }) });
  const { rows } = cat.listRows(s.catalog, s.installed, 'claude', 'all', '');
  assert.ok(rows.every((r) => r.pill === null));
  assert.strictEqual(rows.find((r) => r.name === 'testing').sub, 'Install state unknown');
  assert.strictEqual(rows.find((r) => r.name === 'planning').score.text, '82%');
});

test('with the marketplace not registered, Get is disabled and says to register first', () => {
  const s = state({ installed: installed({ state: 'no-marketplace', plugins: {} }) });
  const row = cat.listRows(s.catalog, s.installed, 'claude', 'all', '').rows.find((r) => r.name === 'docs');
  assert.strictEqual(row.pill.label, 'Get');
  assert.strictEqual(row.pill.disabled, true);
  assert.strictEqual(row.sub, 'Register first to install');
});

// --- the split button ---

function split(claude, copilot, chosen, plugin) {
  const catalog = sample();
  const p = catalog.plugins.find((x) => x.name === (plugin || 'planning'));
  const statuses = {
    claude: cat.pluginStatus(p, cat.hostInfo({ claude: entry(claude), copilot: entry(copilot) }, 'claude')),
    copilot: cat.pluginStatus(p, cat.hostInfo({ claude: entry(claude), copilot: entry(copilot) }, 'copilot'))
  };
  return cat.splitAction(catalog, statuses, chosen);
}

test('the split button runs the pending action for the chosen host, else for the other one', () => {
  const cases = [
    // [claude has, copilot has, chosen, expected host, expected label]
    [{}, {}, 'claude', 'claude', 'Install in Claude Code'],
    [{}, {}, 'copilot', 'copilot', 'Install in Copilot CLI'],
    [{ planning: have('0.1.0') }, {}, 'claude', 'copilot', 'Install in Copilot CLI'],
    [{ planning: have('0.1.0') }, {}, 'copilot', 'copilot', 'Install in Copilot CLI'],
    [{}, { planning: have('0.1.0') }, 'copilot', 'claude', 'Install in Claude Code'],
    [{ planning: have('0.0.9') }, { planning: have('0.0.9') }, 'copilot', 'copilot', 'Update in Copilot CLI'],
    [{ planning: have('0.0.9') }, { planning: have('0.1.0') }, 'copilot', 'claude', 'Update in Claude Code'],
    [{ planning: have('0.1.0', false) }, { planning: have('0.1.0') }, 'claude', 'claude', 'Enable in Claude Code'],
    [{ planning: have('0.1.0', false) }, { planning: have('0.0.1') }, 'claude', 'claude', 'Enable in Claude Code'],
    [{ planning: have('0.1.0') }, { planning: have('0.1.0') }, 'claude', null, 'Up to date everywhere']
  ];
  for (const [claude, copilot, chosen, host, label] of cases) {
    const result = split(claude, copilot, chosen);
    assert.strictEqual(result.host, host, label + ' / ' + chosen);
    assert.strictEqual(result.label, label, label + ' / ' + chosen);
    assert.strictEqual(result.action === null, host === null);
  }
});

test('the split menu lists every action for both hosts, Uninstall included', () => {
  const result = split({ planning: have('0.0.9') }, {});
  assert.deepStrictEqual(result.menu.map((m) => m.label + '|' + m.host), ['Install|copilot', 'Update|claude', 'Uninstall|claude']);
  assert.strictEqual(split({ planning: have('0.1.0') }, { planning: have('0.1.0') }).menu.length, 2);
  assert.strictEqual(split({ planning: have('0.1.0') }, { planning: have('0.1.0') }).note, 'Nothing is pending');
  assert.strictEqual(split({}, {}).note, 'Runs in a terminal · you confirm first');
});

// --- the sidebar ---

test('the featured card is hidden while searching or filtering, and the Update all strip counts updates', () => {
  const base = state({ installed: installed(entry({ docs: have('1.8.0'), testing: have('0.3.0') })) });
  const plain = cat.sidebarModel(base);
  assert.strictEqual(plain.featured.plugin, 'planning');
  assert.strictEqual(plain.featured.note, 'New in 0.6.0');
  assert.strictEqual(plain.updateAll.count, 2);
  assert.strictEqual(plain.filters.find((f) => f.id === 'updates').hot, true);
  assert.strictEqual(cat.sidebarModel(Object.assign({}, base, { ui: Object.assign({}, base.ui, { q: 'plan' }) })).featured, null);
  assert.strictEqual(cat.sidebarModel(Object.assign({}, base, { ui: Object.assign({}, base.ui, { filter: 'installed' }) })).featured, null);
  const none = cat.sidebarModel(Object.assign({}, base, { installed: installed() }));
  assert.strictEqual(none.updateAll, null);
  assert.strictEqual(none.filters.find((f) => f.id === 'updates').hot, false);
});

test('the footer names the source and the marketplace version', () => {
  assert.strictEqual(cat.sidebarModel(state()).footer.source, 'Catalog from GitHub · 26 Nov');
  assert.strictEqual(cat.sidebarModel(state({ source: { kind: 'checkout', date: null } })).footer.source, 'Catalog from this checkout');
  assert.strictEqual(cat.sidebarModel(state()).footer.version, '0.7.0');
});

test('the setup and failure notices say what happened and give one next step', () => {
  const none = cat.sidebarModel(state({ installed: installed({ state: 'no-marketplace', plugins: {} }) }));
  const register = none.notices.find((n) => n.kind === 'register');
  assert.strictEqual(register.title, 'Connect Claude Code to eurus-labs');
  assert.strictEqual(register.command, 'claude plugin marketplace add eurus-labs/Skills');
  assert.deepStrictEqual(register.buttons.map((b) => b.label), ['Register from GitHub']);
  const inRepo = cat.sidebarModel(state({ inRepo: true, installed: installed({ state: 'no-marketplace', plugins: {} }) }));
  assert.deepStrictEqual(inRepo.notices[0].buttons.map((b) => b.label), ['Register from GitHub', 'Use this checkout']);

  const missing = cat.sidebarModel(state({ installed: installed({ state: 'missing-exe', plugins: {} }) })).notices[0];
  assert.strictEqual(missing.code, 'claude');
  assert.match(missing.body, /Install Claude Code, then refresh\. The catalog and Copilot CLI keep working\./);

  const offline = cat.sidebarModel(state({ problem: { kind: 'offline', message: 'x', date: '2026-11-26T00:00:00Z' } })).notices[0];
  assert.strictEqual(offline.title, 'Showing the catalog from 26 Nov');
  assert.match(offline.body, /GitHub could not be reached\. Install state is live; versions may be behind\./);
  assert.strictEqual(offline.buttons[0].label, 'Try again');

  const rejected = cat.sidebarModel(state({ problem: { kind: 'rejected', message: 'Plugin name `a;rm -rf` is not allowed', date: '2026-11-26T00:00:00Z' } })).notices[0];
  assert.match(rejected.body, /Plugin name `a;rm -rf` is not allowed\. Still showing the catalog from 26 Nov\./);
  assert.deepStrictEqual(rejected.buttons.map((b) => b.label), ['Try again', 'Settings']);
});

test('with no catalog the sidebar is an empty model that carries the problem', () => {
  const model = cat.sidebarModel(state({ catalog: null, source: null, problem: { kind: 'offline', message: 'offline' } }));
  assert.strictEqual(model.empty, true);
  assert.strictEqual(model.problem.message, 'offline');
});

// --- the plugin page ---

test('the page shows the status pills and the eval stats of the chosen host', () => {
  const s = state({ installed: installed(entry({ planning: have('0.1.0') }), entry({ planning: have('0.0.1') })) });
  const m = cat.pluginModel(s);
  assert.deepStrictEqual(m.pills.map((p) => p.text), ['Update available in Copilot CLI', 'Installed in Claude Code']);
  assert.strictEqual(m.eval.has, true);
  assert.strictEqual(m.eval.kpis[0].value, '1');
  assert.strictEqual(m.eval.kpis[0].unit, ' / 4');
  assert.strictEqual(m.eval.low, true, 'one trusted case is low confidence');
  assert.strictEqual(m.eval.kpis[1].value, '26');
  assert.strictEqual(m.eval.kpis[1].unit, ' Nov');
  assert.strictEqual(m.skills[0].low, false);
  assert.strictEqual(m.skills[0].meta, '4/4 · 26 Nov');
});

test('a skill with fewer than 3 cases on the host is marked low confidence', () => {
  const m = cat.pluginModel(state());
  const group = m.skills.find((x) => x.name === 'group-epics');
  assert.strictEqual(group.low, true);
  assert.match(group.meta, /low confidence/);
  assert.strictEqual(group.role, 'bad');
});

test('with no run on the host one panel replaces the four cards and says so', () => {
  const s = state();
  s.ui = Object.assign({}, s.ui, { evalHost: 'copilot' });
  const m = cat.pluginModel(s);
  assert.strictEqual(m.eval.has, false);
  assert.strictEqual(m.eval.title, 'No Copilot CLI run in the archive yet');
  assert.strictEqual(m.skills[0].pct, '—');
  assert.strictEqual(m.skills[0].meta, 'Not run on Copilot CLI');
});

test('the contributor surface is absent outside the repository and present inside it', () => {
  const outside = cat.pluginModel(state());
  assert.strictEqual(outside.contributor, null);
  assert.ok(outside.skills.every((x) => !x.canExpand));
  const s = state({ inRepo: true });
  s.ui = Object.assign({}, s.ui, { expanded: { 'analyze-requirements': true } });
  const inside = cat.pluginModel(s);
  assert.strictEqual(inside.contributor.summary, '2 must fire · 1 must stay quiet · 1 behavior');
  assert.strictEqual(inside.contributor.runAllLabel, 'Run all 4 cases');
  const first = inside.skills[0];
  assert.strictEqual(first.open, true);
  assert.strictEqual(first.runLabel, 'Run 3 cases');
  assert.deepStrictEqual(first.cases.map((c) => c.kindLabel), ['Must fire', 'Must stay quiet', 'Behavior']);
  assert.strictEqual(inside.skills[1].open, false);
});

test('a case result is the percentage, "partial" or "error" when it is not trusted, or "Not run"', () => {
  const m = cat.pluginModel(Object.assign(state({ inRepo: true }), {}));
  const catalog = sample();
  const [fires, quiet, works, none] = catalog.plugins[0].cases;
  assert.deepStrictEqual([cat.caseResult(fires, 'claude').text, cat.caseResult(fires, 'claude').role, cat.caseResult(fires, 'claude').meta], ['100%', 'ok', '3 runs · 26 Nov']);
  assert.strictEqual(cat.caseResult(quiet, 'claude').text, 'partial');
  assert.strictEqual(cat.caseResult(works, 'claude').text, 'error');
  assert.strictEqual(cat.caseResult(none, 'claude').text, 'Not run');
  assert.ok(m);
});

test('a running job overlays its cases, and a fresh score replaces the old one', () => {
  const [fires, quiet] = sample().plugins[0].cases;
  assert.strictEqual(cat.caseResult(fires, 'claude', { status: 'running' }).text, 'Running');
  assert.strictEqual(cat.caseResult(fires, 'claude', { status: 'running' }).pulse, true);
  assert.strictEqual(cat.caseResult(fires, 'claude', { status: 'queued' }).text, 'Queued');
  assert.strictEqual(cat.caseResult(fires, 'claude', { status: 'stopped' }).text, 'Stopped');
  assert.deepStrictEqual([cat.caseResult(quiet, 'claude', { status: 'failed', score: 0.4 }).text, cat.caseResult(quiet, 'claude', { status: 'failed', score: 0.4 }).meta], ['40%', 'just now']);
});

test('Run buttons are disabled while a run is in progress', () => {
  const s = state({ inRepo: true, job: { plan: { plugin: 'planning', host: 'claude', cases: [] }, view: { running: true, items: [] } } });
  assert.strictEqual(cat.pluginModel(s).contributor.disabled, true);
  assert.strictEqual(cat.pluginModel(s).jobRunning, true);
  assert.strictEqual(cat.pluginModel(state({ inRepo: true })).contributor.disabled, false);
});

test('runs are listed oldest first with the date, its number and the case count', () => {
  const m = cat.pluginModel(state());
  assert.deepStrictEqual(m.runs.map((r) => [r.pct, r.when, r.cases]), [['100%', '26 Nov #1', '9 cases'], ['69%', '26 Nov #2', '4 cases']]);
  assert.strictEqual(m.runs[1].role, 'warn');
});

test('the Install tab has one row per host with its status, the command, and two fixed slots', () => {
  const s = state({ installed: installed(entry({ planning: have('0.0.9') }), entry({ planning: have('0.1.0') })) });
  const m = cat.pluginModel(s);
  const [copilot, claude] = m.install;
  assert.strictEqual(copilot.upToDate, true);
  assert.strictEqual(copilot.primary, null);
  assert.strictEqual(copilot.canUninstall, true);
  assert.strictEqual(claude.primary.label, 'Update');
  assert.strictEqual(claude.command, 'claude plugin update planning@eurus-labs');
  assert.strictEqual(claude.status, 'v0.0.9 installed · v0.1.0 available');
  const fresh = cat.pluginModel(state()).install[0];
  assert.strictEqual(fresh.canUninstall, false);
  assert.strictEqual(fresh.primary.label, 'Install');
  const missing = cat.pluginModel(state({ installed: installed({ state: 'missing-exe', plugins: {} }) })).install[1];
  assert.strictEqual(missing.primary.disabled, true);
  assert.strictEqual(missing.status, 'claude is not on PATH');
});

test('dates come from a run stamp or an ISO time', () => {
  assert.strictEqual(cat.day('2026-11-26T06-55-42-435Z'), '26 Nov');
  assert.strictEqual(cat.day('2026-01-02T10:00:00.000Z'), '2 Jan');
  assert.strictEqual(cat.day('nonsense'), '');
  assert.strictEqual(cat.day(undefined), '');
});
