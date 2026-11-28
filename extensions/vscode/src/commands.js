'use strict';
// Install commands and their validation, and how the hosts' install state is read. No `vscode` import.
// The argument lists mirror tools/skill_manager.py plugin_command; test/commands.json pins both.

const NAME = /^[a-z0-9][a-z0-9-]*$/;
const MARKETPLACE = 'eurus-labs';
const GITHUB_SOURCE = 'eurus-labs/Skills';
const EXE = { copilot: 'copilot', claude: 'claude' };
const PLUGIN_ACTIONS = ['install', 'update', 'enable', 'uninstall'];
const ACTIONS = PLUGIN_ACTIONS.concat(['marketplace-add', 'marketplace-update']);
const VERB = { install: 'Install', update: 'Update', enable: 'Enable', uninstall: 'Uninstall' };
const LIST_TIMEOUT_MS = 60000;

// {exe, args} for one action. The host and the action are checked here too, so a caller cannot skip it.
// `plugin` is needed for the four plugin actions; `source` ('github' or 'checkout') and `repo` for marketplace-add.
function build(host, action, options) {
  const opts = options || {};
  if (!Object.prototype.hasOwnProperty.call(EXE, host)) throw new Error('unknown host: ' + host);
  if (ACTIONS.indexOf(action) < 0) throw new Error('unknown action: ' + action);
  const exe = EXE[host];
  if (PLUGIN_ACTIONS.indexOf(action) >= 0) {
    if (typeof opts.plugin !== 'string' || !NAME.test(opts.plugin)) throw new Error('unknown plugin: ' + opts.plugin);
    // Copilot enables by name; every other plugin action, and Claude's enable, takes name@marketplace.
    const ref = action === 'enable' && host === 'copilot' ? opts.plugin : opts.plugin + '@' + MARKETPLACE;
    return { exe, args: ['plugin', action, ref] };
  }
  if (action === 'marketplace-update') return { exe, args: ['plugin', 'marketplace', 'update', MARKETPLACE] };
  if (opts.source === 'checkout') {
    if (typeof opts.repo !== 'string' || !opts.repo) throw new Error('the checkout folder is unknown');
    return { exe, args: ['plugin', 'marketplace', 'add', opts.repo] };
  }
  if (opts.source !== 'github') throw new Error('source must be github or checkout');
  return { exe, args: ['plugin', 'marketplace', 'add', GITHUB_SOURCE] };
}

// The command as a person reads it: `claude plugin install planning@eurus-labs`.
function display(command) {
  return [command.exe].concat(command.args).join(' ');
}

// Check a request from a webview against what the extension host knows, then build its command.
// `catalog` is the loaded catalog; `listed` is {host: {plugin: {version, enabled}}} from the hosts' own listing,
// the only list Enable and Uninstall are checked against (a renamed plugin is no longer in the catalog).
function validate(request, catalog, listed) {
  const req = request || {};
  const hosts = ((catalog && catalog.hosts) || []).map((h) => h.id);
  if (typeof req.host !== 'string' || hosts.indexOf(req.host) < 0 || !Object.prototype.hasOwnProperty.call(EXE, req.host)) {
    return { ok: false, error: 'Unknown host: ' + String(req.host) };
  }
  if (ACTIONS.indexOf(req.action) < 0) return { ok: false, error: 'Unknown action: ' + String(req.action) };
  if (PLUGIN_ACTIONS.indexOf(req.action) >= 0) {
    const name = req.plugin;
    if (typeof name !== 'string' || !NAME.test(name)) return { ok: false, error: 'Unknown plugin: ' + String(name) };
    let known;
    if (req.action === 'enable' || req.action === 'uninstall') {
      known = Object.prototype.hasOwnProperty.call((listed && listed[req.host]) || {}, name);
    } else {
      known = ((catalog && catalog.plugins) || []).some((p) => p.name === name);
    }
    if (!known) return { ok: false, error: 'Unknown plugin: ' + name };
  } else if (req.action === 'marketplace-add' && req.source !== 'github' && req.source !== 'checkout') {
    return { ok: false, error: 'Source must be github or checkout' };
  }
  try {
    return { ok: true, command: build(req.host, req.action, { plugin: req.plugin, source: req.source, repo: req.repo }) };
  } catch (error) {
    return { ok: false, error: error.message };
  }
}

// What one host has, read as tools/skill_manager.py installed() reads it.
function parseInstalled(host, pluginList, marketList) {
  const entry = { marketplace: null, plugins: {} };
  (Array.isArray(marketList) ? marketList : []).forEach((market) => {
    if (market && typeof market === 'object' && market.name === MARKETPLACE) {
      entry.marketplace = typeof market.source === 'string' ? market.source : 'registered';
      if (market.path) entry.marketplace = market.source + ' ' + market.path;
    }
  });
  (Array.isArray(pluginList) ? pluginList : []).forEach((item) => {
    if (!item || typeof item !== 'object') return;
    let name;
    let market;
    if (host === 'copilot') {
      name = item.name;
      market = item.marketplace;
    } else {
      const id = typeof item.id === 'string' ? item.id : '';
      const at = id.indexOf('@');
      name = at < 0 ? id : id.slice(0, at);
      market = at < 0 ? '' : id.slice(at + 1);
    }
    if (market === MARKETPLACE && typeof name === 'string' && NAME.test(name)) {
      entry.plugins[name] = { version: item.version == null ? null : String(item.version), enabled: item.enabled !== false };
    }
  });
  return entry;
}

// Read one host's state. `run(exe, args)` resolves {stdout} or rejects with an error that may have code 'ENOENT'.
// Result: {state: 'ready' | 'no-marketplace' | 'missing-exe' | 'error', ...parsed, error}.
async function readInstalled(host, run) {
  const exe = EXE[host];
  let plugins;
  let markets;
  try {
    plugins = JSON.parse((await run(exe, ['plugin', 'list', '--json'])).stdout);
    markets = JSON.parse((await run(exe, ['plugin', 'marketplace', 'list', '--json'])).stdout);
  } catch (error) {
    if (error && error.code === 'ENOENT') return { state: 'missing-exe', marketplace: null, plugins: {}, error: null };
    return { state: 'error', marketplace: null, plugins: {}, error: String((error && error.message) || error).slice(-300) };
  }
  const parsed = parseInstalled(host, plugins, markets);
  return Object.assign({ state: parsed.marketplace ? 'ready' : 'no-marketplace', error: null }, parsed);
}

module.exports = { NAME, MARKETPLACE, GITHUB_SOURCE, EXE, ACTIONS, PLUGIN_ACTIONS, VERB, LIST_TIMEOUT_MS,
  build, display, validate, parseInstalled, readInstalled };
