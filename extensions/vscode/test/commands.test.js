'use strict';
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');

const commands = require('../src/commands');
const { sample } = require('./fixture');

const table = JSON.parse(fs.readFileSync(path.join(__dirname, 'commands.json'), 'utf8'));
const REPO = '/work/Skills';

test('every row of commands.json is what build() makes (tools/test_skill_manager.py checks the Python side)', () => {
  assert.ok(table.cases.length >= 14);
  assert.deepStrictEqual(commands.EXE, table.exe);
  assert.strictEqual(commands.MARKETPLACE, table.marketplace);
  for (const row of table.cases) {
    const command = commands.build(row.host, row.action, { plugin: table.plugin, source: row.source, repo: REPO });
    const expected = row.args.map((a) => (a === '<repo>' ? REPO : a));
    assert.deepStrictEqual(command, { exe: table.exe[row.host], args: expected }, JSON.stringify(row));
  }
});

test('the table covers every host with every action', () => {
  for (const host of Object.keys(table.exe)) {
    for (const action of commands.ACTIONS) {
      assert.ok(table.cases.some((r) => r.host === host && r.action === action), host + ' ' + action);
    }
  }
});

test('display() joins the program and its arguments', () => {
  assert.strictEqual(commands.display(commands.build('claude', 'install', { plugin: 'planning' })), 'claude plugin install planning@eurus-labs');
  assert.strictEqual(commands.display(commands.build('copilot', 'enable', { plugin: 'docs' })), 'copilot plugin enable docs');
});

const catalog = sample();
const listed = { claude: { planning: { version: '0.1.0', enabled: true }, gone: { version: '0.1.0', enabled: true } }, copilot: {} };

test('a plugin that is not in the catalog is refused for install and update', () => {
  for (const action of ['install', 'update']) {
    const result = commands.validate({ host: 'claude', action, plugin: 'nope' }, catalog, listed);
    assert.strictEqual(result.ok, false);
    assert.match(result.error, /Unknown plugin: nope/);
  }
});

test('enable and uninstall are checked against what the host lists, so a renamed plugin can still be removed', () => {
  assert.strictEqual(commands.validate({ host: 'claude', action: 'uninstall', plugin: 'gone' }, catalog, listed).ok, true);
  assert.strictEqual(commands.validate({ host: 'claude', action: 'enable', plugin: 'planning' }, catalog, listed).ok, true);
  assert.strictEqual(commands.validate({ host: 'claude', action: 'uninstall', plugin: 'docs' }, catalog, listed).ok, false);
  assert.strictEqual(commands.validate({ host: 'copilot', action: 'enable', plugin: 'planning' }, catalog, listed).ok, false);
});

test('an unknown host is refused, and so is a host the catalog does not list', () => {
  assert.match(commands.validate({ host: 'bash', action: 'install', plugin: 'planning' }, catalog, listed).error, /Unknown host/);
  const narrow = Object.assign({}, catalog, { hosts: [{ id: 'claude', label: 'Claude Code' }] });
  assert.strictEqual(commands.validate({ host: 'copilot', action: 'install', plugin: 'planning' }, narrow, listed).ok, false);
  assert.strictEqual(commands.validate({ action: 'install', plugin: 'planning' }, catalog, listed).ok, false);
});

test('an unknown action is refused', () => {
  for (const action of ['rm', 'install; rm -rf /', '', undefined, 'marketplace-remove']) {
    const result = commands.validate({ host: 'claude', action, plugin: 'planning' }, catalog, listed);
    assert.strictEqual(result.ok, false, String(action));
    assert.match(result.error, /Unknown action/);
  }
});

test('a plugin name that is not a plugin name never reaches a command', () => {
  for (const name of ['a;rm -rf', '../x', 'Planning', '', 'planning@evil', '-rf']) {
    assert.strictEqual(commands.validate({ host: 'claude', action: 'uninstall', plugin: name }, catalog, { claude: { [name]: {} } }).ok, false, name);
    assert.throws(() => commands.build('claude', 'install', { plugin: name }));
  }
});

test('marketplace-add needs a known source, and a checkout needs its folder', () => {
  assert.strictEqual(commands.validate({ host: 'claude', action: 'marketplace-add', source: 'github' }, catalog, listed).ok, true);
  assert.strictEqual(commands.validate({ host: 'claude', action: 'marketplace-add', source: 'ftp://x' }, catalog, listed).ok, false);
  assert.strictEqual(commands.validate({ host: 'claude', action: 'marketplace-add', source: 'checkout' }, catalog, listed).ok, false);
  const ok = commands.validate({ host: 'claude', action: 'marketplace-add', source: 'checkout', repo: REPO }, catalog, listed);
  assert.deepStrictEqual(ok.command.args, ['plugin', 'marketplace', 'add', REPO]);
});

test('parseInstalled reads Copilot by name and marketplace, and Claude by id', () => {
  const copilot = commands.parseInstalled('copilot',
    [{ name: 'docs', marketplace: 'eurus-labs', version: '1.9.0' }, { name: 'x', marketplace: 'other', version: '1' }, { name: 'off', marketplace: 'eurus-labs', version: '2', enabled: false }],
    [{ name: 'eurus-labs', source: 'eurus-labs/Skills' }]);
  assert.strictEqual(copilot.marketplace, 'eurus-labs/Skills');
  assert.deepStrictEqual(copilot.plugins, { docs: { version: '1.9.0', enabled: true }, off: { version: '2', enabled: false } });
  const claude = commands.parseInstalled('claude',
    [{ id: 'planning@eurus-labs', version: '0.1.0' }, { id: 'y@other', version: '1' }, { id: 'bad;name@eurus-labs', version: '1' }, null, 'text'], []);
  assert.strictEqual(claude.marketplace, null);
  assert.deepStrictEqual(Object.keys(claude.plugins), ['planning']);
});

test('readInstalled reports ready, no marketplace, a missing program and a failing command', async () => {
  const ok = (plugins, markets) => async (exe, args) => ({ stdout: JSON.stringify(args[1] === 'list' ? plugins : markets) });
  const ready = await commands.readInstalled('claude', ok([{ id: 'planning@eurus-labs', version: '0.1.0' }], [{ name: 'eurus-labs', source: 'x' }]));
  assert.strictEqual(ready.state, 'ready');
  assert.strictEqual(ready.plugins.planning.version, '0.1.0');
  const none = await commands.readInstalled('copilot', ok([], []));
  assert.strictEqual(none.state, 'no-marketplace');
  const missing = await commands.readInstalled('claude', async () => { const e = new Error('spawn claude ENOENT'); e.code = 'ENOENT'; throw e; });
  assert.strictEqual(missing.state, 'missing-exe');
  const failing = await commands.readInstalled('claude', async () => { throw new Error('boom'); });
  assert.strictEqual(failing.state, 'error');
  assert.match(failing.error, /boom/);
  const garbled = await commands.readInstalled('claude', async () => ({ stdout: 'not json' }));
  assert.strictEqual(garbled.state, 'error');
});

test('readInstalled calls the program with an argument list, never a shell string', async () => {
  const seen = [];
  await commands.readInstalled('copilot', async (exe, args) => { seen.push([exe, args]); return { stdout: '[]' }; });
  assert.deepStrictEqual(seen, [['copilot', ['plugin', 'list', '--json']], ['copilot', ['plugin', 'marketplace', 'list', '--json']]]);
});
