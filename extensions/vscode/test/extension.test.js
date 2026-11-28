'use strict';
// Drives src/extension.js against a fake `vscode` module, a fake `claude` and `copilot` on PATH, and the real
// eval engine (tools/skill_manager.py) when Python is installed. It checks the wiring that the pure modules cannot:
// what a webview message does on the extension host, and what reaches a terminal or the engine.

const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const Module = require('module');
const { spawnSync } = require('child_process');

const REPO = path.join(__dirname, '..', '..', '..');
const python = spawnSync('python3', ['--version']);
const skip = process.platform === 'win32' ? 'the fake executables are shell scripts' : false;

const sent = { sidebar: [], page: [] };
const terminals = [];
const warnings = [];
const settings = { theme: 'stone', catalogUrl: 'https://example.invalid/catalog.json', confirmInstalls: true, python: 'python3', evalMaxCostUsd: 2 };
const handlers = { sidebar: null, page: null, close: null };
let provider = null;
let panel = null;
let sidebarHtml = '';

function webview(kind) {
  return {
    cspSource: 'vscode-webview://test',
    options: null,
    set html(value) { if (kind === 'sidebar') sidebarHtml = value; else panel.htmlText = value; },
    postMessage(message) { sent[kind].push(message); return Promise.resolve(true); },
    onDidReceiveMessage(fn) { handlers[kind] = fn; return { dispose() {} }; }
  };
}

const fakeVscode = {
  ColorThemeKind: { Light: 1, Dark: 2, HighContrast: 3, HighContrastLight: 4 },
  ConfigurationTarget: { Global: 1 },
  ViewColumn: { Active: -1 },
  Uri: { file: (p) => ({ fsPath: p, scheme: 'file' }), parse: (u) => ({ url: u }) },
  env: { openExternal: async () => true },
  commands: { registerCommand: () => ({ dispose() {} }), executeCommand: async () => undefined },
  window: {
    activeColorTheme: { kind: 2 },
    createOutputChannel: () => ({ appendLine() {}, show() {}, dispose() {} }),
    registerWebviewViewProvider: (id, p) => { provider = p; return { dispose() {} }; },
    createWebviewPanel: (id, title) => {
      panel = { title, visible: true, htmlText: '', webview: webview('page'), reveal() {}, onDidDispose() {}, onDidChangeViewState() {} };
      return panel;
    },
    createTerminal: (options) => { const t = Object.assign({ shown: false, show() { this.shown = true; }, exitStatus: undefined }, { options }); terminals.push(t); return t; },
    onDidCloseTerminal: (fn) => { handlers.close = fn; return { dispose() {} }; },
    onDidChangeActiveColorTheme: () => ({ dispose() {} }),
    showWarningMessage: (message) => { warnings.push(message); return Promise.resolve(undefined); },
    showErrorMessage: (message) => { warnings.push(message); return Promise.resolve(undefined); },
    showInformationMessage: () => Promise.resolve(undefined),
    showTextDocument: async () => undefined
  },
  workspace: {
    isTrusted: true,
    workspaceFolders: [{ uri: { scheme: 'file', fsPath: REPO } }],
    getConfiguration: () => ({ get: (key) => settings[key], update: async (key, value) => { settings[key] = value; } }),
    onDidChangeConfiguration: () => ({ dispose() {} }),
    onDidChangeWorkspaceFolders: () => ({ dispose() {} })
  }
};

const realLoad = Module._load;
Module._load = function load(request, ...rest) {
  return request === 'vscode' ? fakeVscode : realLoad.call(this, request, ...rest);
};

// Fake claude and copilot: list commands answer with JSON; `plugin eval` prints a transcript line and exits.
const bin = fs.mkdtempSync(path.join(os.tmpdir(), 'eurus-bin-'));
for (const exe of ['claude', 'copilot']) {
  fs.writeFileSync(path.join(bin, exe), [
    '#!/bin/sh',
    'case "$2 $3" in',
    '  "list --json") cat "$(dirname "$0")/$(basename "$0").list.json" 2>/dev/null || echo "[]";;',
    '  "marketplace list") echo \'[{"name":"eurus-labs","source":"eurus-labs/Skills"}]\';;',
    '  "eval plugins/planning") echo "transcript file: plugins/planning/evals/results/2099-01-01T00-00-00Z/fake.md";;',
    '  *) echo "unexpected: $*";;',
    'esac',
    'exit 0', ''
  ].join('\n'), { mode: 0o755 });
}
process.env.PATH = bin + path.delimiter + process.env.PATH;

let extension;
const later = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function until(check, what, timeoutMs) {
  const end = Date.now() + (timeoutMs || 15000);
  while (Date.now() < end) {
    if (check()) return;
    await later(50);
  }
  assert.fail('timed out waiting for ' + what);
}

function lastRegions(kind) {
  const renders = sent[kind].filter((m) => m.type === 'render');
  return renders.length ? renders[renders.length - 1].regions : {};
}

test.before(async () => {
  extension = require('../src/extension');
  const subscriptions = [];
  const store = {};
  await extension.activate({ subscriptions, globalState: { get: (k) => store[k], update: async (k, v) => { store[k] = v; } } });
  provider.resolveWebviewView({ webview: webview('sidebar'), onDidDispose() {} });
  await until(() => lastRegions('sidebar').main && lastRegions('sidebar').main.includes('planning'), 'the sidebar to list plugins');
});

test.after(() => {
  extension.deactivate();
  fs.rmSync(bin, { recursive: true, force: true });
});

test('in this repository the sidebar lists the nine plugins from catalog.json and says where it got them', { skip }, () => {
  const main = lastRegions('sidebar').main;
  assert.match(main, /Catalog from this checkout/);
  assert.strictEqual((main.match(/data-act="select"/g) || []).length, 9 + 1, 'nine rows and the featured card');
  assert.ok(sidebarHtml.includes('Content-Security-Policy'));
});

test('a request for an unknown plugin or an unsafe name opens no dialog and runs nothing', { skip }, async () => {
  const before = terminals.length;
  for (const plugin of ['nope', 'a;rm -rf', '../x']) {
    handlers.sidebar({ type: 'ask', action: 'install', plugin });
    await later(20);
  }
  handlers.sidebar({ type: 'ask', action: 'rm', plugin: 'planning' });
  handlers.sidebar({ type: 'confirm', id: 'made-up', dontAsk: false });
  await later(50);
  assert.strictEqual(terminals.length, before);
  assert.ok(warnings.length >= 3, warnings.join(' | '));
  assert.ok(!lastRegions('sidebar').dialog);
});

test('Get asks first with the exact command, and confirming runs it in a terminal with no shell', { skip }, async () => {
  await until(() => lastRegions('sidebar').main.includes('Get'), 'install state');
  handlers.sidebar({ type: 'ask', action: 'install', plugin: 'planning' });
  await until(() => (lastRegions('sidebar').dialog || '').includes('dlg'), 'the dialog');
  const dialog = lastRegions('sidebar').dialog;
  assert.match(dialog, /Install planning in Claude Code\?/);
  assert.ok(dialog.includes('claude plugin install planning@eurus-labs'));
  assert.ok(dialog.includes('Don’t ask again'));
  assert.strictEqual(terminals.length, 0, 'nothing runs before the person confirms');
  const id = /data-act="confirm" data-id="([a-f0-9]+)"/.exec(dialog)[1];
  handlers.sidebar({ type: 'confirm', id, dontAsk: false });
  await until(() => terminals.length === 1, 'the terminal');
  assert.deepStrictEqual(terminals[0].options.shellPath, 'claude');
  assert.deepStrictEqual(terminals[0].options.shellArgs, ['plugin', 'install', 'planning@eurus-labs']);
  assert.strictEqual(terminals[0].shown, true);
  assert.ok(!(lastRegions('sidebar').dialog || '').includes('dlg'), 'the dialog closes');
  assert.strictEqual(settings.confirmInstalls, true);
  handlers.sidebar({ type: 'confirm', id, dontAsk: false });
  await later(30);
  assert.strictEqual(terminals.length, 1, 'a dialog confirms once');
});

test('Don’t ask again turns the setting off, and the next install runs at once', { skip }, async () => {
  handlers.sidebar({ type: 'ask', action: 'install', plugin: 'docs' });
  await until(() => (lastRegions('sidebar').dialog || '').includes('dlg'), 'the dialog');
  const id = /data-act="confirm" data-id="([a-f0-9]+)"/.exec(lastRegions('sidebar').dialog)[1];
  handlers.sidebar({ type: 'confirm', id, dontAsk: true });
  await until(() => terminals.length === 2, 'the second terminal');
  assert.strictEqual(settings.confirmInstalls, false);
  handlers.sidebar({ type: 'ask', action: 'install', plugin: 'testing' });
  await until(() => terminals.length === 3, 'the third terminal, with no dialog');
  assert.deepStrictEqual(terminals[2].options.shellArgs, ['plugin', 'install', 'testing@eurus-labs']);
});

test('Uninstall always asks, even with the setting off, and its button is the danger one', { skip }, async () => {
  fs.writeFileSync(path.join(bin, 'claude.list.json'), JSON.stringify([{ id: 'planning@eurus-labs', version: '0.1.0' }]));
  handlers.sidebar({ type: 'select', plugin: 'planning' });
  await until(() => panel, 'the plugin page panel');
  assert.ok(panel.htmlText.includes('<h1>planning</h1>'), 'the first paint already holds the page');
  handlers.page({ type: 'ready' }); // what the page script posts once it has loaded
  await until(() => lastRegions('page').main, 'the first render');
  assert.strictEqual(panel.title, 'planning');
  handlers.page({ type: 'refresh' });
  await until(() => lastRegions('page').main.includes('Installed in Claude Code'), 'the install state to refresh');
  const before = terminals.length;
  handlers.page({ type: 'ask', action: 'uninstall', host: 'claude' });
  await until(() => (lastRegions('page').dialog || '').includes('dlg'), 'the uninstall dialog');
  const dialog = lastRegions('page').dialog;
  assert.match(dialog, /Uninstall planning in Claude Code\?/);
  assert.ok(dialog.includes('btn lg danger'));
  assert.ok(!dialog.includes('Don\u2019t ask again'));
  assert.strictEqual(terminals.length, before);
  const id = /data-act="confirm" data-id="([a-f0-9]+)"/.exec(dialog)[1];
  handlers.page({ type: 'confirm', id, dontAsk: true });
  await until(() => terminals.length === before + 1, 'the uninstall terminal');
  assert.deepStrictEqual(terminals[before].options.shellArgs, ['plugin', 'uninstall', 'planning@eurus-labs']);
});

test('a plugin the host does not list cannot be uninstalled or enabled', { skip }, async () => {
  const before = terminals.length;
  warnings.length = 0;
  handlers.page({ type: 'ask', action: 'enable', host: 'copilot' });
  handlers.page({ type: 'ask', action: 'uninstall', host: 'copilot' });
  handlers.page({ type: 'ask', action: 'install', host: 'bash' });
  await later(100);
  assert.strictEqual(terminals.length, before);
  assert.ok(!(lastRegions('page').dialog || '').includes('dlg'));
  assert.strictEqual(warnings.filter((w) => /Unknown (plugin|host)/.test(w)).length, 3, warnings.join(' | '));
});

test('the plugin page shows the contributor surface in this repository', { skip }, async () => {
  handlers.page({ type: 'toggle-skill', skill: 'analyze-requirements' });
  await until(() => lastRegions('page').main.includes('data-act="run-case"'), 'the cases');
  const main = lastRegions('page').main;
  assert.ok(main.includes('Contributor'));
  assert.ok(main.includes('Run all 13 cases'));
  handlers.page({ type: 'help' });
  await until(() => lastRegions('page').main.includes('An eval runs a skill on fixed test prompts'), 'the help text');
});

test('Run asks first, names the billing, and starts nothing before the person confirms', { skip: skip || (python.status === 0 ? false : 'python3 is not installed') }, async () => {
  handlers.page({ type: 'run-case', case: 'no-such-case' });
  await later(50);
  assert.ok(!(lastRegions('page').dialog || '').includes('dlg'), 'an unknown case opens no dialog');
  handlers.page({ type: 'run-case', case: 'analyze-requirements-compare-versions' });
  await until(() => (lastRegions('page').dialog || '').includes('dlg'), 'the run dialog');
  const dialog = lastRegions('page').dialog;
  assert.match(dialog, /Run analyze-requirements-compare-versions on Claude Code\?/);
  assert.ok(dialog.includes('Billed to your Claude key, with a $2 ceiling.'));
  assert.ok(dialog.includes('claude plugin eval plugins/planning --case analyze-requirements-compare-versions --no-publish --scaffold --max-cost-usd 2'));
  assert.ok(!dialog.includes('Don’t ask again'));
  assert.ok(!lastRegions('page').tray, 'no tray before the run starts');
});

test('confirming a run starts the real engine, runs the case, and fills the tray', { skip: skip || (python.status === 0 ? false : 'python3 is not installed') }, async () => {
  const id = /data-act="confirm" data-id="([a-f0-9]+)"/.exec(lastRegions('page').dialog)[1];
  handlers.page({ type: 'confirm', id, dontAsk: false });
  await until(() => (lastRegions('page').tray || '').includes('EVAL RUN'), 'the tray');
  await until(() => /finished|failed|stopped/.test(lastRegions('page').tray), 'the run to end', 30000);
  const tray = lastRegions('page').tray;
  assert.ok(tray.includes('analyze-requirements-compare-versions'));
  assert.ok(tray.includes('$ claude plugin eval plugins/planning --case analyze-requirements-compare-versions'));
  assert.ok(!/token=[A-Za-z0-9_-]{8,}/.test(tray), 'no token in the tray');
  assert.ok(!tray.includes('--trust-plugin'));
  assert.ok(tray.includes('data-act="transcript"'), 'the transcript line the engine logged becomes a link');
  assert.ok(tray.includes('data-act="close-tray"'));
  assert.ok(!tray.includes('data-act="stop"'), 'no Stop once it ended');
  const everything = JSON.stringify(sent) + sidebarHtml + panel.htmlText;
  assert.ok(!/127\.0\.0\.1:\d+\/\?token/.test(everything), 'the engine address never reaches a webview');
});

test('closing the tray clears it', { skip: skip || (python.status === 0 ? false : 'python3 is not installed') }, async () => {
  handlers.page({ type: 'close-tray' });
  await until(() => lastRegions('page').tray === '', 'the tray to close');
});
