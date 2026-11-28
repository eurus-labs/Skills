'use strict';
// The VS Code glue. Everything that can be tested without VS Code lives in the other modules; this file only
// connects them to the editor: the sidebar view, the plugin page, terminals, the output channel and the engine.
// It sends no telemetry. Its one network call is the catalog fetch (Decision 5), outside this repository only.

const vscode = require('vscode');
const fs = require('fs');
const https = require('https');
const childProcess = require('child_process');
const crypto = require('crypto');
const path = require('path');

const catalogs = require('./catalog');
const commands = require('./commands');
const engine = require('./engine');
const evalview = require('./evalview');
const html = require('./html');

const DEFAULT_CATALOG_URL = 'https://raw.githubusercontent.com/eurus-labs/Skills/main/catalog.json';
const CACHE_KEY = 'eurusSkills.catalogCache';
const JOB_POLL_MS = 1000;
const CATALOG_POLL_MS = 5000;

let output;
let context;
let sidebar = null; // the WebviewView, once resolved
let page = null; // the WebviewPanel, while open
let engineHandle = null; // {api, stop, exited, url}
let starting = null; // the engine start in progress
let jobTimer = null;
let catalogTimer = null;
const terminalQueue = new Map(); // terminal -> what to run when it closes

const S = {
  catalog: null,
  source: null,
  problem: null,
  installed: {},
  inRepo: false,
  repo: null,
  engineError: null,
  job: null,
  dialog: null,
  ui: { host: 'claude', filter: 'all', q: '', selected: null, evalHost: 'claude', section: 'skills', menuOpen: false, help: false, expanded: {} }
};

// --- settings and theme ----------------------------------------------------------------------------------

function config() {
  return vscode.workspace.getConfiguration('eurusSkills');
}

function htmlOptions(webview) {
  const kind = vscode.window.activeColorTheme.kind;
  const highContrast = kind === vscode.ColorThemeKind.HighContrast || kind === vscode.ColorThemeKind.HighContrastLight;
  return { nonce: html.nonce(), cspSource: webview.cspSource, theme: config().get('theme'), highContrast };
}

function log(line) {
  output.appendLine(engine.maskToken(line, engineHandle ? engineHandle.api.token : ''));
}

// --- the model each webview draws ------------------------------------------------------------------------

function trayView() {
  return S.job ? S.job.view : null;
}

function dialogFor(origin) {
  const d = S.dialog;
  return d && d.origin === origin ? d : null;
}

function renderSidebar(full) {
  if (!sidebar) return;
  if (full) {
    sidebar.webview.html = html.sidebarDocument(catalogs.sidebarModel(S), dialogFor('sidebar'), htmlOptions(sidebar.webview));
    return;
  }
  sidebar.webview.postMessage({ type: 'render', regions: html.sidebarRegions(catalogs.sidebarModel(S), dialogFor('sidebar')) });
}

function renderPage(full) {
  if (!page) return;
  const model = S.catalog ? catalogs.pluginModel(S) : null;
  if (full) {
    page.webview.html = html.pluginDocument(model, trayView(), dialogFor('page'), htmlOptions(page.webview));
    return;
  }
  page.webview.postMessage({ type: 'render', regions: html.pluginRegions(model, trayView(), dialogFor('page')) });
}

function renderAll(full) {
  renderSidebar(full);
  renderPage(full);
}

function rebuildJobView() {
  if (!S.job) return;
  S.job.view = evalview.jobView(S.job.snapshot, S.job.plan,
    evalview.freshScores(S.job.before, S.catalog, S.job.plan.host, S.job.plan.cases), S.job.engineGone);
}

// --- the catalog -----------------------------------------------------------------------------------------

function detectRepo() {
  const folders = vscode.workspace.workspaceFolders || [];
  for (const folder of folders) {
    if (folder.uri.scheme === 'file' && engine.isSkillsRepo(folder.uri.fsPath, fs)) return folder.uri.fsPath;
  }
  return null;
}

function adopt(catalog, source) {
  S.catalog = catalog;
  S.source = source;
  const ids = catalog.hosts.map((h) => h.id);
  if (ids.indexOf(S.ui.host) < 0) S.ui.host = ids[0];
  if (ids.indexOf(S.ui.evalHost) < 0) S.ui.evalHost = ids[0];
  if (!S.ui.selected || !catalog.plugins.some((p) => p.name === S.ui.selected)) {
    S.ui.selected = catalog.featured ? catalog.featured.plugin : (catalog.plugins[0] || {}).name || null;
  }
}

function readCache() {
  const cached = context.globalState.get(CACHE_KEY);
  if (!cached || typeof cached.text !== 'string') return null;
  const parsed = catalogs.parseCatalog(cached.text);
  return parsed.ok ? { catalog: parsed.catalog, fetchedAt: cached.fetchedAt } : null;
}

async function loadFromCheckout() {
  if (engineHandle) {
    try {
      const parsed = catalogs.validateCatalog(await engineHandle.api.catalog());
      if (parsed.ok) {
        adopt(parsed.catalog, { kind: 'checkout', date: null });
        S.problem = null;
        return;
      }
      S.problem = { kind: 'rejected', message: parsed.error, date: null };
      return;
    } catch (error) {
      log('The engine could not give its catalog: ' + error.message);
    }
  }
  try {
    const parsed = catalogs.parseCatalog(fs.readFileSync(path.join(S.repo, 'catalog.json'), 'utf8'));
    if (parsed.ok) {
      adopt(parsed.catalog, { kind: 'checkout', date: null });
      S.problem = null;
    } else {
      S.problem = { kind: 'rejected', message: parsed.error, date: null };
    }
  } catch (error) {
    S.problem = { kind: 'rejected', message: 'catalog.json could not be read: ' + error.message, date: null };
  }
}

async function loadFromGithub() {
  const url = config().get('catalogUrl') || DEFAULT_CATALOG_URL;
  const cache = readCache();
  const useCache = (problem) => {
    if (cache) {
      adopt(cache.catalog, { kind: 'github', date: cache.fetchedAt });
      S.problem = Object.assign({ date: cache.fetchedAt }, problem);
    } else {
      S.catalog = null;
      S.problem = problem;
    }
  };
  try {
    const body = await catalogs.fetchCatalogText(url, https.get, 15000);
    const parsed = catalogs.parseCatalog(body);
    if (!parsed.ok) {
      useCache({ kind: 'rejected', message: parsed.error });
      return;
    }
    const fetchedAt = new Date().toISOString();
    await context.globalState.update(CACHE_KEY, { text: body, fetchedAt });
    adopt(parsed.catalog, { kind: 'github', date: fetchedAt });
    S.problem = null;
  } catch (failure) {
    const message = failure && failure.message ? failure.message : 'unknown error';
    useCache(failure && failure.kind === 'rejected' ? { kind: 'rejected', message } : { kind: 'offline', message });
  }
}

async function loadCatalog() {
  S.repo = detectRepo();
  S.inRepo = !!S.repo;
  if (S.inRepo) await loadFromCheckout();
  else await loadFromGithub();
}

function execFileRun(exe, args) {
  return new Promise((resolve, reject) => {
    childProcess.execFile(exe, args, { cwd: S.repo || undefined, timeout: commands.LIST_TIMEOUT_MS, windowsHide: true, maxBuffer: 4 * 1024 * 1024 },
      (error, stdout, stderr) => {
        if (error) {
          error.message = (stderr || error.message || '').toString();
          reject(error);
          return;
        }
        resolve({ stdout: stdout.toString() });
      });
  });
}

async function refreshInstalled() {
  const ids = (S.catalog ? S.catalog.hosts.map((h) => h.id) : Object.keys(commands.EXE)).filter((id) => commands.EXE[id]);
  await Promise.all(ids.map(async (id) => {
    S.installed[id] = await commands.readInstalled(id, execFileRun);
  }));
  renderAll(false);
}

async function refreshAll() {
  await loadCatalog();
  renderAll(false);
  await refreshInstalled();
}

// --- the engine ------------------------------------------------------------------------------------------

async function ensureEngine() {
  if (engineHandle) return engineHandle;
  if (starting) return starting;
  if (!S.repo) throw new Error('Open this repository to run evals');
  const python = config().get('python') || 'python3';
  if (!vscode.workspace.isTrusted) {
    S.engineError = engine.describeFailure({ code: 'untrusted' }, python);
    renderPage(false);
    throw new Error(S.engineError.title);
  }
  starting = engine.startEngine({ python, cwd: S.repo, onLine: (line) => output.appendLine(line) }).then((handle) => {
    handle.url = 'http://127.0.0.1:' + handle.api.port + '/?token=' + handle.api.token;
    engineHandle = handle;
    S.engineError = null;
    handle.exited.then(() => {
      if (engineHandle === handle) engineHandle = null;
      if (S.job && S.job.snapshot && S.job.snapshot.status === 'running') {
        S.job.engineGone = true;
        stopJobPolling();
        rebuildJobView();
      }
      renderAll(false);
    });
    return handle;
  }, (failure) => {
    output.appendLine((failure.tail || []).join('\n'));
    S.engineError = engine.describeFailure(failure, python);
    renderPage(false);
    throw new Error(S.engineError.title);
  }).finally(() => { starting = null; });
  return starting;
}

function stopEngine() {
  if (engineHandle) engineHandle.stop();
  engineHandle = null;
}

function startCatalogPolling() {
  stopCatalogPolling();
  catalogTimer = setInterval(async () => {
    if (!engineHandle || !page || !page.visible) return;
    try {
      const parsed = catalogs.validateCatalog(await engineHandle.api.catalog());
      if (parsed.ok && JSON.stringify(parsed.catalog) !== JSON.stringify(S.catalog)) {
        adopt(parsed.catalog, { kind: 'checkout', date: null });
        rebuildJobView();
        renderAll(false);
      }
    } catch (error) {
      log('Catalog poll failed: ' + error.message);
    }
  }, CATALOG_POLL_MS);
}

function stopCatalogPolling() {
  if (catalogTimer) clearInterval(catalogTimer);
  catalogTimer = null;
}

function stopJobPolling() {
  if (jobTimer) clearInterval(jobTimer);
  jobTimer = null;
}

function startJobPolling() {
  stopJobPolling();
  const tick = async () => {
    if (!engineHandle || !S.job) return;
    try {
      const snapshot = await engineHandle.api.job();
      S.job.snapshot = snapshot;
      if (snapshot.status !== 'running') {
        stopJobPolling();
        const parsed = catalogs.validateCatalog(await engineHandle.api.catalog());
        if (parsed.ok) adopt(parsed.catalog, { kind: 'checkout', date: null });
      }
      rebuildJobView();
      renderPage(false);
    } catch (error) {
      log('Job poll failed: ' + error.message);
    }
  };
  jobTimer = setInterval(tick, JOB_POLL_MS);
}

// --- dialogs and actions ---------------------------------------------------------------------------------

function newId() {
  return crypto.randomBytes(8).toString('hex');
}

function describeRequests(requests) {
  const first = requests[0];
  const label = catalogs.hostLabel(S.catalog, first.host);
  const verb = first.action === 'marketplace-add' ? 'Register' : commands.VERB[first.action];
  const n = requests.length;
  const subject = first.action === 'marketplace-add' ? 'eurus-labs' : n === 1 ? first.plugin : n + ' plugins';
  return {
    title: verb + ' ' + subject + ' in ' + label + '?',
    body: 'This changes your ' + label + ' configuration. ' + (n === 1 ? 'The command runs' : 'The commands run') + ' in a VS Code terminal, where you can follow the output.',
    commands: requests.map((r) => commands.display(r.command)),
    canSkip: first.action !== 'uninstall' && first.action !== 'marketplace-add',
    confirmLabel: verb + (n > 1 ? ' all' : ''),
    danger: first.action === 'uninstall'
  };
}

function listedPlugins() {
  const listed = {};
  Object.keys(S.installed).forEach((id) => { listed[id] = S.installed[id].plugins || {}; });
  return listed;
}

// Validate requests from a webview, then confirm them (or run them at once when the person turned asking off).
function askInstall(origin, requests) {
  if (!S.catalog || !requests.length) return;
  const checked = [];
  for (const request of requests) {
    const result = commands.validate(Object.assign({ repo: S.repo }, request), S.catalog, listedPlugins());
    if (!result.ok) {
      vscode.window.showWarningMessage('Eurus Skills: ' + result.error);
      return;
    }
    const info = hostInfoFor(request.host);
    if (info.kind === 'missing-exe') {
      vscode.window.showWarningMessage('Eurus Skills: ' + commands.EXE[request.host] + ' is not on PATH.');
      return;
    }
    checked.push(Object.assign({}, request, { command: result.command }));
  }
  const first = checked[0];
  const skippable = first.action !== 'uninstall' && first.action !== 'marketplace-add';
  if (skippable && config().get('confirmInstalls') === false) {
    runInTerminals(checked);
    return;
  }
  S.dialog = Object.assign({ origin, id: newId(), kind: 'install', requests: checked }, describeRequests(checked));
  renderAll(false);
}

function hostInfoFor(host) {
  return catalogs.hostInfo(S.installed, host);
}

function runInTerminals(requests) {
  let next = 0;
  const step = () => {
    if (next >= requests.length) return;
    const request = requests[next++];
    const title = 'Eurus Skills · ' + (request.plugin || 'marketplace');
    const terminal = vscode.window.createTerminal({ name: title, shellPath: request.command.exe, shellArgs: request.command.args, cwd: S.repo || undefined });
    terminalQueue.set(terminal, step);
    terminal.show();
  };
  step();
}

function onTerminalClosed(terminal) {
  if (!terminalQueue.has(terminal)) return;
  const next = terminalQueue.get(terminal);
  terminalQueue.delete(terminal);
  refreshInstalled();
  if (terminal.exitStatus && terminal.exitStatus.code === 0) next();
}

async function confirmDialog(id, dontAsk) {
  const d = S.dialog;
  if (!d || d.id !== id) return;
  S.dialog = null;
  renderAll(false);
  if (d.kind === 'install') {
    if (dontAsk === true && d.canSkip) await config().update('confirmInstalls', false, vscode.ConfigurationTarget.Global);
    runInTerminals(d.requests);
  } else if (d.kind === 'run') {
    await startRun(d.plan);
  }
}

function askRun(caseNames, label) {
  if (!S.inRepo || !S.catalog || S.job && S.job.view && S.job.view.running) return;
  const plugin = S.catalog.plugins.find((p) => p.name === S.ui.selected);
  if (!plugin) return;
  const known = plugin.cases.map((c) => c.name);
  const cases = caseNames.filter((n) => known.indexOf(n) >= 0);
  if (!cases.length || cases.length > 100) return;
  const cost = evalview.costCeiling(config().get('evalMaxCostUsd'));
  if (cost === null) {
    vscode.window.showErrorMessage('Eurus Skills: eurusSkills.evalMaxCostUsd must be over 0 and at most 50.', 'Open setting').then((pick) => {
      if (pick) vscode.commands.executeCommand('workbench.action.openSettings', 'eurusSkills.evalMaxCostUsd');
    });
    return;
  }
  const host = S.ui.evalHost;
  const hostLabel = catalogs.hostLabel(S.catalog, host);
  const kinds = {};
  plugin.cases.forEach((c) => { kinds[c.name] = c.kind; });
  const words = evalview.runDialog(host, hostLabel, cases, cost);
  const plan = { plugin: plugin.name, host, hostLabel, cases, label: cases.length === 1 ? cases[0] : label + ' · ' + cases.length + ' cases', cost };
  S.dialog = Object.assign({ origin: 'page', id: newId(), kind: 'run', plan, canSkip: false, confirmLabel: 'Run', danger: false,
    commands: evalview.runCommands(host, plugin.name, cases, kinds, cost) }, words);
  renderPage(false);
}

async function startRun(plan) {
  let handle;
  try {
    handle = await ensureEngine();
  } catch (error) {
    return;
  }
  try {
    const snapshot = await handle.api.run({ plugin: plan.plugin, cases: plan.cases, host: plan.host, arms: 'both', max_cost_usd: plan.cost });
    S.job = { plan, snapshot, before: S.catalog, view: null, engineGone: false };
    rebuildJobView();
    startJobPolling();
    startCatalogPolling();
  } catch (error) {
    vscode.window.showWarningMessage('Eurus Skills: ' + error.message);
  }
  renderPage(false);
}

async function openTranscript(caseName) {
  const item = S.job && S.job.view && S.job.view.items.find((i) => i.name === caseName);
  if (!item || !item.transcript || !S.repo) return;
  const file = evalview.resolveTranscript(S.repo, item.transcript);
  if (!file || !fs.existsSync(file)) {
    vscode.window.showWarningMessage('Eurus Skills: that transcript is not on disk.');
    return;
  }
  const uri = vscode.Uri.file(file);
  if (file.endsWith('.md')) await vscode.commands.executeCommand('markdown.showPreview', uri);
  else await vscode.window.showTextDocument(uri);
}

// --- messages from the webviews (untrusted requests, re-validated here) -----------------------------------

function hostIds() {
  return S.catalog ? S.catalog.hosts.map((h) => h.id) : [];
}

function pluginNamed(name) {
  return S.catalog && S.catalog.plugins.find((p) => p.name === name) || null;
}

function str(value, max) {
  return typeof value === 'string' ? value.slice(0, max || 200) : '';
}

function common(origin, message) {
  switch (message.type) {
    case 'confirm': confirmDialog(str(message.id, 64), message.dontAsk === true || message.dontAsk === 'true'); return true;
    case 'cancel': S.dialog = null; renderAll(false); return true;
    case 'refresh': refreshAll(); return true;
    case 'settings-catalog': vscode.commands.executeCommand('workbench.action.openSettings', 'eurusSkills.catalogUrl'); return true;
    default: return false;
  }
}

function onSidebarMessage(message) {
  if (!message || typeof message.type !== 'string') return;
  if (message.type === 'ready') { renderSidebar(false); return; }
  if (common('sidebar', message)) return;
  switch (message.type) {
    case 'query': S.ui.q = str(message.q, 200); renderSidebar(false); break;
    case 'host': if (hostIds().indexOf(message.id) >= 0) { S.ui.host = message.id; renderAll(false); } break;
    case 'filter': if (['all', 'installed', 'updates'].indexOf(message.id) >= 0) { S.ui.filter = message.id; renderSidebar(false); } break;
    case 'select': openPlugin(str(message.plugin, 80)); break;
    case 'ask':
      if (['install', 'update', 'enable'].indexOf(message.action) >= 0) askInstall('sidebar', [{ host: S.ui.host, action: message.action, plugin: str(message.plugin, 80) }]);
      break;
    case 'update-all': {
      const list = catalogs.listRows(S.catalog, S.installed, S.ui.host, 'updates', '').rows;
      askInstall('sidebar', list.map((r) => ({ host: S.ui.host, action: 'update', plugin: r.name })));
      break;
    }
    case 'register':
      askInstall('sidebar', [{ host: S.ui.host, action: 'marketplace-add', source: message.source === 'checkout' && S.inRepo ? 'checkout' : 'github' }]);
      break;
    default: break;
  }
}

function onPageMessage(message) {
  if (!message || typeof message.type !== 'string') return;
  if (message.type === 'ready') { renderPage(false); return; }
  if (common('page', message)) return;
  const plugin = S.catalog ? pluginNamed(S.ui.selected) : null;
  switch (message.type) {
    case 'section': if (['skills', 'runs', 'install'].indexOf(message.id) >= 0) { S.ui.section = message.id; renderPage(false); } break;
    case 'eval-host': if (hostIds().indexOf(message.id) >= 0) { S.ui.evalHost = message.id; renderPage(false); } break;
    case 'help': S.ui.help = !S.ui.help; renderPage(false); break;
    case 'menu': S.ui.menuOpen = !S.ui.menuOpen; renderPage(false); break;
    case 'toggle-skill': {
      const name = str(message.skill, 80);
      if (plugin && plugin.skills.some((s) => s.name === name)) { S.ui.expanded[name] = !S.ui.expanded[name]; renderPage(false); }
      break;
    }
    case 'ask':
      if (plugin) {
        S.ui.menuOpen = false;
        askInstall('page', [{ host: str(message.host, 40), action: str(message.action, 40), plugin: plugin.name }]);
      }
      break;
    case 'run-case': askRun([str(message.case, 120)], str(message.case, 120)); break;
    case 'run-skill':
      if (plugin) askRun(plugin.cases.filter((c) => c.skills.indexOf(str(message.skill, 80)) >= 0).map((c) => c.name), str(message.skill, 80));
      break;
    case 'run-all': if (plugin) askRun(plugin.cases.map((c) => c.name), plugin.name); break;
    case 'run-rest': if (S.job) askRun(S.job.view.remaining, S.job.plan.label.split(' · ')[0]); break;
    case 'answer': answer(message); break;
    case 'stop': if (engineHandle && S.job) engineHandle.api.stop().catch((error) => vscode.window.showWarningMessage('Eurus Skills: ' + error.message)); break;
    case 'close-tray':
      if (engineHandle && S.job && S.job.view && S.job.view.running) engineHandle.api.stop().catch(() => {});
      stopJobPolling();
      S.job = null;
      renderPage(false);
      break;
    case 'transcript': openTranscript(str(message.case, 120)); break;
    case 'show-output': output.show(true); break;
    case 'retry-engine': S.engineError = null; ensureEngine().catch(() => {}).then(() => { refreshAll(); }); break;
    case 'open-setting': vscode.commands.executeCommand('workbench.action.openSettings', 'eurusSkills.python'); break;
    default: break;
  }
}

function answer(message) {
  const view = S.job && S.job.view;
  if (!engineHandle || !view || !view.question || String(view.question.id) !== str(message.qid, 20)) return;
  const body = evalview.answerBody(view.question, str(message.reply, 4));
  if (!body) return;
  engineHandle.api.answer(body.id, body.reply).catch((error) => vscode.window.showWarningMessage('Eurus Skills: ' + error.message));
}

// --- views -----------------------------------------------------------------------------------------------

function openPlugin(name) {
  const plugin = pluginNamed(name);
  if (!plugin) return;
  S.ui.selected = name;
  S.ui.menuOpen = false;
  if (page) {
    page.title = name;
    page.reveal(undefined, true);
    renderAll(false);
    return;
  }
  page = vscode.window.createWebviewPanel('eurusSkills.plugin', name, vscode.ViewColumn.Active, { enableScripts: true, localResourceRoots: [] });
  page.webview.onDidReceiveMessage(onPageMessage);
  page.onDidDispose(() => {
    page = null;
    stopCatalogPolling();
  });
  page.onDidChangeViewState(() => { if (page && page.visible) renderPage(false); });
  renderPage(true);
  if (engineHandle) startCatalogPolling();
  renderSidebar(false);
}

class StoreView {
  resolveWebviewView(view) {
    sidebar = view;
    view.webview.options = { enableScripts: true, localResourceRoots: [] };
    view.webview.onDidReceiveMessage(onSidebarMessage);
    view.onDidDispose(() => { sidebar = null; });
    renderSidebar(true);
  }
}

async function openSkillManager() {
  if (!S.inRepo) {
    vscode.window.showInformationMessage('Eurus Skills: open a checkout of this repository to use the skill manager.');
    return;
  }
  try {
    const handle = await ensureEngine();
    await vscode.env.openExternal(vscode.Uri.parse(handle.url));
  } catch (error) {
    vscode.window.showWarningMessage('Eurus Skills: ' + error.message);
  }
}

async function activate(extensionContext) {
  context = extensionContext;
  output = vscode.window.createOutputChannel('Eurus Skills');
  context.subscriptions.push(output);
  context.subscriptions.push(vscode.window.registerWebviewViewProvider('eurusSkills.store', new StoreView()));
  context.subscriptions.push(vscode.commands.registerCommand('eurusSkills.refresh', () => refreshAll()));
  context.subscriptions.push(vscode.commands.registerCommand('eurusSkills.openSkillManager', () => openSkillManager()));
  context.subscriptions.push(vscode.window.onDidCloseTerminal(onTerminalClosed));
  context.subscriptions.push(vscode.window.onDidChangeActiveColorTheme(() => renderAll(true)));
  context.subscriptions.push(vscode.workspace.onDidChangeConfiguration((event) => {
    if (event.affectsConfiguration('eurusSkills.catalogUrl')) refreshAll();
    else if (event.affectsConfiguration('eurusSkills')) renderAll(true);
  }));
  context.subscriptions.push(vscode.workspace.onDidChangeWorkspaceFolders(() => refreshAll()));
  await loadCatalog();
  renderAll(false);
  refreshInstalled();
}

function deactivate() {
  stopJobPolling();
  stopCatalogPolling();
  stopEngine();
}

module.exports = { activate, deactivate };
