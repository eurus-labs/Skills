'use strict';
const test = require('node:test');
const assert = require('node:assert');

const theme = require('../src/theme');

test('marks: the first letter and the next consonant, or the initials of a hyphenated name', () => {
  assert.strictEqual(theme.mark('planning'), 'Pl');
  assert.strictEqual(theme.mark('testing'), 'Ts');
  assert.strictEqual(theme.mark('review'), 'Rv');
  assert.strictEqual(theme.mark('skill-authoring'), 'SA');
  assert.strictEqual(theme.mark('docs'), 'Dc');
  assert.strictEqual(theme.mark('a'), 'A');
  assert.strictEqual(theme.mark(''), '');
});

test('the theme is stone by default and follows the setting', () => {
  assert.strictEqual(theme.themeName(undefined), 'stone');
  assert.strictEqual(theme.themeName('nonsense'), 'stone');
  assert.strictEqual(theme.themeName('charcoal'), 'charcoal');
  assert.strictEqual(theme.themeName('black'), 'black');
  assert.strictEqual(theme.resolve(undefined, false).bg, '#f1eee8');
  assert.strictEqual(theme.resolve('charcoal', false).bg, '#1b1916');
  assert.strictEqual(theme.resolve('black', false).bg, '#0a0a0a');
  assert.match(theme.cssVariables('black', false), /--bg: #0a0a0a;/);
});

test('the palettes hold the approved values', () => {
  const stone = theme.PALETTES.stone;
  assert.deepStrictEqual([stone.bg, stone.chrome, stone.side, stone.surface, stone.raised], ['#f1eee8', '#e6e2da', '#ebe7df', '#f8f6f1', '#fdfcfa']);
  assert.deepStrictEqual([stone.text, stone['text-2'], stone.accent, stone['on-accent']], ['#1f1d1a', '#5f5a52', '#1f1d1a', '#fbfaf7']);
  assert.deepStrictEqual([stone.ok, stone.warn, stone.bad, stone.danger, stone['on-danger']], ['#2f7d4f', '#a35c0a', '#c0392b', '#b93a2c', '#ffffff']);
  const charcoal = theme.PALETTES.charcoal;
  assert.deepStrictEqual([charcoal.bg, charcoal.text, charcoal.ok, charcoal.warn, charcoal.bad], ['#1b1916', '#f2ede4', '#5cc28a', '#e0a64a', '#ef6a5a']);
  const black = theme.PALETTES.black;
  assert.deepStrictEqual([black.bg, black.chrome, black.text, black.accent, black['on-accent']], ['#0a0a0a', '#000000', '#f5f5f5', '#f5f5f5', '#0a0a0a']);
  assert.strictEqual(stone['input-border'], 'rgba(60, 50, 35, .50)');
});

test('every palette defines every role the stylesheet reads', () => {
  const roles = Object.keys(theme.PALETTES.stone);
  for (const name of theme.THEMES) assert.deepStrictEqual(Object.keys(theme.PALETTES[name]).sort(), roles.slice().sort(), name);
  assert.deepStrictEqual(Object.keys(theme.HIGH_CONTRAST).sort(), roles.slice().sort());
});

test('in high contrast the setting is ignored and every role reads a --vscode-* variable', () => {
  for (const setting of ['stone', 'charcoal', 'black', undefined]) {
    const table = theme.resolve(setting, true);
    assert.strictEqual(table, theme.HIGH_CONTRAST);
  }
  const css = theme.cssVariables('black', true);
  assert.match(css, /--text: var\(--vscode-foreground\);/);
  assert.match(css, /--accent: var\(--vscode-button-background\);/);
  assert.doesNotMatch(css, /#0a0a0a/);
  for (const role of ['bg', 'side', 'text', 'accent', 'on-accent', 'focus', 'ok', 'warn', 'bad']) {
    assert.match(theme.HIGH_CONTRAST[role], /var\(--vscode-/, role);
  }
});

test('score colors: 90 and up green, 60 to 89 amber, under 60 red, on the percentage shown', () => {
  assert.strictEqual(theme.scoreRole(1), 'ok');
  assert.strictEqual(theme.scoreRole(0.9), 'ok');
  assert.strictEqual(theme.scoreRole(0.895), 'ok');
  assert.strictEqual(theme.scoreRole(0.89), 'warn');
  assert.strictEqual(theme.scoreRole(0.6), 'warn');
  assert.strictEqual(theme.scoreRole(0.59), 'bad');
  assert.strictEqual(theme.scoreRole(0), 'bad');
  assert.strictEqual(theme.percent(0.985), 99);
});
