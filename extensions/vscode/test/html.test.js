'use strict';
const test = require('node:test');
const assert = require('node:assert');

const html = require('../src/html');
const cat = require('../src/catalog');
const ev = require('../src/evalview');
const { sample, installed } = require('./fixture');

const EVIL = '<script>alert(1)</script>';
const OPTIONS = { nonce: 'NONCE123', cspSource: 'vscode-webview://x', theme: 'stone', highContrast: false };

function state(catalog) {
  return {
    catalog, installed: installed(), inRepo: true, source: { kind: 'checkout', date: null }, problem: null, job: null, engineError: null,
    ui: { host: 'claude', filter: 'all', q: '', selected: 'planning', evalHost: 'claude', section: 'skills', menuOpen: true, help: true, expanded: { 'analyze-requirements': true } }
  };
}

// A catalog whose every text field holds a script tag.
function hostile() {
  const doc = sample();
  doc.marketplace.version = EVIL;
  doc.featured = { plugin: 'planning', note: EVIL, text: EVIL };
  doc.plugins[0].description = EVIL;
  doc.plugins[0].version = EVIL;
  doc.plugins[0].skills.forEach((s) => { s.description = EVIL; });
  doc.plugins[0].cases.forEach((c) => { c.description = EVIL; });
  return cat.validateCatalog(doc).catalog;
}

// Everything the page script would parse as markup: whole <script>...</script> elements other than ours.
function foreignScripts(text) {
  return (text.match(/<script\b[^>]*>/g) || []).filter((tag) => tag !== '<script nonce="NONCE123">');
}

test('esc() escapes the five characters that matter', () => {
  assert.strictEqual(html.esc('<a href="x" onclick=\'y\'>&</a>'), '&lt;a href=&quot;x&quot; onclick=&#39;y&#39;&gt;&amp;&lt;/a&gt;');
  assert.strictEqual(html.esc(undefined), '');
  assert.strictEqual(html.esc(0), '0');
});

test('catalog text holding <script> renders as text in the sidebar and the page', () => {
  const s = state(hostile());
  const side = html.sidebarDocument(cat.sidebarModel(s), null, OPTIONS);
  const pageText = html.pluginDocument(cat.pluginModel(s), null, null, OPTIONS);
  for (const doc of [side, pageText]) {
    assert.deepStrictEqual(foreignScripts(doc), []);
    assert.ok(!doc.includes(EVIL));
    assert.ok(doc.includes('&lt;script&gt;alert(1)&lt;/script&gt;'));
  }
});

test('case, log and question text holding <script> renders as text in the tray and the dialog', () => {
  const plan = { plugin: 'planning', host: 'claude', hostLabel: 'Claude Code', cases: ['case-one'], label: 'case-one' };
  const view = ev.jobView({ status: 'running', log: ['$ x', EVIL, 'transcript file: plugins/p/evals/results/s/case-one.md'], progress: { index: 1, total: 1, item: 'case-one' },
    question: { id: 1, text: EVIL, choices: ['y', 'n', 's'] } }, plan, {});
  const dialog = { id: 'd', title: EVIL, body: EVIL, commands: [EVIL], canSkip: true, confirmLabel: EVIL, danger: false };
  const doc = html.pluginDocument(cat.pluginModel(state(sample())), view, dialog, OPTIONS);
  assert.deepStrictEqual(foreignScripts(doc), []);
  assert.ok(!doc.includes(EVIL));
  assert.ok((doc.match(/&lt;script&gt;alert\(1\)&lt;\/script&gt;/g) || []).length >= 5);
  const tray = html.trayHtml(view);
  assert.match(tray, /WAITING FOR YOU/);
  assert.strictEqual((tray.match(/data-act="answer"/g) || []).length, 3);
});

test('an attribute value cannot be broken out of', () => {
  const doc = sample();
  doc.plugins[3].name = 'review';
  const s = state(cat.validateCatalog(doc).catalog);
  s.ui.q = '"><img src=x onerror=alert(1)>';
  const out = html.sidebarDocument(cat.sidebarModel(s), null, OPTIONS);
  assert.ok(!out.includes('<img'));
  assert.ok(out.includes('value="&quot;&gt;&lt;img src=x onerror=alert(1)&gt;"'));
});

test('both pages carry a CSP with default-src none, the nonce, and no inline style attribute', () => {
  const s = state(sample());
  for (const doc of [html.sidebarDocument(cat.sidebarModel(s), null, OPTIONS), html.pluginDocument(cat.pluginModel(s), null, null, OPTIONS)]) {
    const csp = /Content-Security-Policy" content="([^"]+)"/.exec(doc)[1];
    assert.match(csp, /default-src 'none'/);
    assert.match(csp, /script-src 'nonce-NONCE123'/);
    assert.match(csp, /style-src vscode-webview:\/\/x 'nonce-NONCE123'/);
    assert.doesNotMatch(csp, /unsafe-inline|unsafe-eval|\*/);
    assert.strictEqual((doc.match(/<script\b/g) || []).length, 1);
    assert.strictEqual((doc.match(/<style\b/g) || []).length, 1);
    assert.doesNotMatch(doc, /<[a-z][^>]*\sstyle=/i, 'an inline style attribute would be blocked by the CSP');
    assert.doesNotMatch(doc, /\son[a-z]+=/i, 'no inline event handler');
    assert.doesNotMatch(doc, /<(iframe|object|embed|link|img)\b/i);
  }
});

test('a fresh nonce is made for every load', () => {
  const a = html.nonce();
  assert.notStrictEqual(a, html.nonce());
  assert.ok(a.length >= 16);
});

test('the page holds the layout the plan fixes: hero, split button, eval row, four stat cards, three tabs', () => {
  const doc = html.pluginDocument(cat.pluginModel(state(sample())), null, null, OPTIONS);
  for (const needle of ['class="hero"', 'More install options', 'Eval on', 'How scores work', 'EVAL SCORE', 'CASES RUN', 'LAST RUN', 'SKILLS', 'role="tablist" aria-label="Plugin sections"',
    'Install in Claude Code', 'Runs in a terminal', 'Contributor', 'Run all 4 cases', 'Must fire', 'Must stay quiet', 'Behavior', 'Run 3 cases']) {
    assert.ok(doc.includes(needle), needle);
  }
  assert.match(doc, /<h1>planning<\/h1>/);
});

test('outside the repository the page has no contributor parts', () => {
  const s = state(sample());
  s.inRepo = false;
  const doc = html.pluginDocument(cat.pluginModel(s), null, null, OPTIONS);
  for (const needle of ['Contributor', 'Run all', 'data-act="run-case"', 'data-act="toggle-skill"', 'EVAL RUN']) assert.ok(!doc.includes(needle), needle);
});

test('the sidebar holds its rows from top to bottom', () => {
  const s = state(sample());
  s.installed = installed({ state: 'ready', marketplace: 'x', plugins: { docs: { version: '1.8.0', enabled: true } }, error: null });
  const doc = html.sidebarDocument(cat.sidebarModel(s), null, OPTIONS);
  const order = ['EURUS SKILLS', 'id="q"', 'aria-label="Host"', 'class="featured"', 'role="tablist" aria-label="Filter"', 'role="list"', 'class="updateall"', 'Catalog from this checkout'];
  let at = -1;
  for (const needle of order) {
    const next = doc.indexOf(needle);
    assert.ok(next > at, needle + ' is out of order');
    at = next;
  }
  assert.ok(doc.includes('<kbd aria-hidden="true">/</kbd>'));
});

test('the tray shows each state icon, the stop button only while running, and a transcript link', () => {
  const plan = { plugin: 'planning', host: 'claude', hostLabel: 'Claude Code', cases: ['case-one', 'case-two', 'case-three'], label: 'x' };
  const running = ev.jobView({ status: 'running', log: ['$ claude plugin eval --case case-one', 'transcript file: plugins/p/evals/results/s/case-one.md'], progress: { index: 2, total: 3 } }, plan, { 'case-one': 1 });
  const tray = html.trayHtml(running);
  for (const needle of ['✓', '●', '○', 'data-act="stop"', 'Transcript', 'EVAL RUN', 'Claude Code · 1 of 3']) assert.ok(tray.includes(needle), needle);
  const stopped = html.trayHtml(ev.jobView({ status: 'stopped', log: [], progress: { index: 2, total: 3 } }, plan, { 'case-one': 1 }));
  assert.ok(!stopped.includes('data-act="stop"'));
  assert.ok(stopped.includes('–'));
  assert.ok(stopped.includes('data-act="close-tray"'));
});

test('the dialog shows the commands, the verb, and Don’t ask again only when allowed', () => {
  const base = { id: 'abc', title: 'Install planning in Claude Code?', body: 'b', commands: ['claude plugin install planning@eurus-labs'], canSkip: true, confirmLabel: 'Install', danger: false };
  const out = html.dialogHtml(base);
  assert.ok(out.includes('claude plugin install planning@eurus-labs'));
  assert.ok(out.includes('Don’t ask again'));
  assert.ok(out.includes('data-act="confirm" data-id="abc"'));
  assert.ok(!html.dialogHtml(Object.assign({}, base, { canSkip: false })).includes('Don’t ask again'));
  assert.ok(html.dialogHtml(Object.assign({}, base, { danger: true, confirmLabel: 'Uninstall' })).includes('btn lg danger'));
  assert.strictEqual(html.dialogHtml(null), '');
});

test('no token or engine address appears in either page', () => {
  const s = state(sample());
  const docs = html.sidebarDocument(cat.sidebarModel(s), null, OPTIONS) + html.pluginDocument(cat.pluginModel(s), null, null, OPTIONS);
  assert.doesNotMatch(docs, /token/i);
  assert.doesNotMatch(docs, /127\.0\.0\.1/);
  assert.doesNotMatch(docs, /X-Board/);
});

test('the theme setting selects the palette in the page, and high contrast uses the --vscode variables', () => {
  const s = state(sample());
  const black = html.sidebarDocument(cat.sidebarModel(s), null, Object.assign({}, OPTIONS, { theme: 'black' }));
  assert.ok(black.includes('--bg: #0a0a0a;'));
  const hc = html.sidebarDocument(cat.sidebarModel(s), null, Object.assign({}, OPTIONS, { theme: 'black', highContrast: true }));
  assert.ok(hc.includes('--text: var(--vscode-foreground);'));
  assert.ok(!hc.includes('#0a0a0a'));
  assert.ok(html.sidebarDocument(cat.sidebarModel(s), null, OPTIONS).includes('--bg: #f1eee8;'));
});

test('with no catalog the sidebar says it is loading, or why it could not load', () => {
  const loading = html.sidebarDocument(cat.sidebarModel(Object.assign(state(null), { catalog: null, source: null })), null, OPTIONS);
  assert.ok(loading.includes('Loading the catalog'));
  const failed = html.sidebarDocument(cat.sidebarModel(Object.assign(state(null), { catalog: null, source: null, problem: { kind: 'offline', message: 'HTTP 404' } })), null, OPTIONS);
  assert.ok(failed.includes('The catalog could not be loaded'));
  assert.ok(failed.includes('HTTP 404'));
});
