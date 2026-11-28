'use strict';
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const pkg = JSON.parse(fs.readFileSync(path.join(ROOT, 'package.json'), 'utf8'));

function walk(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) => (e.isDirectory() ? walk(path.join(dir, e.name)) : [path.join(dir, e.name)]));
}

test('the package has no dependencies, no lockfile, and the identity the plan fixes', () => {
  assert.strictEqual(pkg.dependencies, undefined);
  assert.strictEqual(pkg.devDependencies, undefined);
  assert.strictEqual(pkg.name, 'eurus-skills');
  assert.strictEqual(pkg.displayName, 'Eurus Skills');
  assert.strictEqual(pkg.publisher, 'eurus-labs');
  assert.strictEqual(pkg.version, '0.1.0');
  for (const lock of ['package-lock.json', 'yarn.lock', 'pnpm-lock.yaml', 'node_modules']) {
    assert.ok(!fs.existsSync(path.join(ROOT, lock)), lock);
  }
});

test('it targets VS Code 1.85 and runs next to the files', () => {
  assert.strictEqual(pkg.engines.vscode, '^1.85.0');
  assert.deepStrictEqual(pkg.extensionKind, ['workspace']);
  assert.strictEqual(pkg.main, './src/extension.js');
  assert.ok(fs.existsSync(path.join(ROOT, pkg.main)));
});

test('it declares the sidebar container, the view, and the five settings', () => {
  assert.strictEqual(pkg.contributes.viewsContainers.activitybar[0].title, 'Eurus Skills');
  assert.ok(fs.existsSync(path.join(ROOT, pkg.contributes.viewsContainers.activitybar[0].icon)));
  assert.strictEqual(pkg.contributes.views.eurusSkills[0].type, 'webview');
  const settings = pkg.contributes.configuration.properties;
  assert.deepStrictEqual(Object.keys(settings).sort(), ['eurusSkills.catalogUrl', 'eurusSkills.confirmInstalls', 'eurusSkills.evalMaxCostUsd', 'eurusSkills.python', 'eurusSkills.theme']);
  assert.deepStrictEqual(settings['eurusSkills.theme'].enum, ['stone', 'charcoal', 'black']);
  assert.strictEqual(settings['eurusSkills.theme'].default, 'stone');
  assert.strictEqual(settings['eurusSkills.python'].default, 'python3');
  assert.strictEqual(settings['eurusSkills.evalMaxCostUsd'].default, 2);
  assert.strictEqual(settings['eurusSkills.evalMaxCostUsd'].maximum, 50);
  assert.ok(settings['eurusSkills.evalMaxCostUsd'].minimum > 0);
  assert.strictEqual(settings['eurusSkills.confirmInstalls'].default, true);
  assert.match(settings['eurusSkills.catalogUrl'].default, /^https:\/\//);
  assert.strictEqual(settings['eurusSkills.catalogUrl'].pattern, '^https://');
});

test('the packaged files exclude the tests', () => {
  const ignore = fs.readFileSync(path.join(ROOT, '.vscodeignore'), 'utf8').split('\n');
  assert.ok(ignore.includes('test/**'));
});

test('only src/extension.js imports vscode', () => {
  for (const file of walk(path.join(ROOT, 'src')).filter((f) => f.endsWith('.js'))) {
    const text = fs.readFileSync(file, 'utf8');
    assert.strictEqual(/require\(['"]vscode['"]\)/.test(text), path.basename(file) === 'extension.js', file);
  }
});

test('the source uses only modules Node 18 has, and nothing from the network but the catalog fetch', () => {
  const allowed = new Set(['vscode', 'fs', 'path', 'http', 'https', 'child_process', 'crypto', './catalog', './commands', './engine', './evalview', './html', './theme']);
  for (const file of walk(path.join(ROOT, 'src')).filter((f) => f.endsWith('.js'))) {
    const text = fs.readFileSync(file, 'utf8');
    for (const match of text.matchAll(/require\(['"]([^'"]+)['"]\)/g)) assert.ok(allowed.has(match[1]), file + ' requires ' + match[1]);
    assert.doesNotMatch(text, /\bfetch\(|XMLHttpRequest|WebSocket|node:/, file + ' uses a newer or networking API');
    assert.doesNotMatch(text, /\.(at|findLast|findLastIndex|toSorted|toReversed|structuredClone|replaceAll)\(/, file + ' uses an API newer than Node 18');
  }
  const https = fs.readFileSync(path.join(ROOT, 'src', 'extension.js'), 'utf8');
  assert.strictEqual((https.match(/https\.get/g) || []).length, 1, 'one catalog fetch');
});

test('the extension never passes --trust-plugin to anything', () => {
  for (const file of walk(path.join(ROOT, 'src')).filter((f) => f.endsWith('.js'))) {
    const text = fs.readFileSync(file, 'utf8').split('\n').filter((l) => !/never passes/.test(l) && !/trust-plugin\.\x27/.test(l)).join('\n');
    assert.doesNotMatch(text, /--trust-plugin/, file);
  }
});
