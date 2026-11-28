'use strict';
// The three palettes, the high-contrast mapping, plugin marks and score colors. No `vscode` import, so
// `node --test` loads it. Colors mean something or are not used: the accent marks the primary action; green,
// amber and red are scores and states only; plugins have no color of their own.

const THEMES = ['stone', 'charcoal', 'black'];
const DEFAULT_THEME = 'stone';

// Each key is the CSS custom property the webviews read (without the leading dashes).
const PALETTES = {
  stone: {
    bg: '#f1eee8', chrome: '#e6e2da', side: '#ebe7df', surface: '#f8f6f1', raised: '#fdfcfa',
    line: 'rgba(60, 50, 35, .10)', 'line-strong': 'rgba(60, 50, 35, .18)', 'input-border': 'rgba(60, 50, 35, .50)',
    dot: 'rgba(60, 50, 35, .13)', text: '#1f1d1a', 'text-2': '#5f5a52', 'text-3': '#6d675e',
    accent: '#1f1d1a', 'on-accent': '#fbfaf7', split: 'rgba(251, 250, 247, .22)',
    ok: '#2f7d4f', warn: '#a35c0a', bad: '#c0392b', danger: '#b93a2c', 'on-danger': '#ffffff',
    track: 'rgba(60, 50, 35, .09)', selected: '#f8f6f1', focus: '#1f1d1a', scrim: 'rgba(31, 29, 26, .35)',
    shadow: 'rgba(60, 50, 35, .2)', 'shadow-soft': 'rgba(60, 50, 35, .08)',
    'warn-bg': '#f6ead6', 'warn-line': 'rgba(163, 92, 10, .3)', 'bad-bg': '#f6e1dc', 'bad-line': 'rgba(192, 57, 43, .28)'
  },
  charcoal: {
    bg: '#1b1916', chrome: '#141210', side: '#181613', surface: '#221f1b', raised: '#2a2722',
    line: 'rgba(255, 240, 220, .08)', 'line-strong': 'rgba(255, 240, 220, .15)', 'input-border': 'rgba(255, 240, 220, .38)',
    dot: 'rgba(255, 240, 220, .09)', text: '#f2ede4', 'text-2': '#b0a898', 'text-3': '#a39b8c',
    accent: '#f2ede4', 'on-accent': '#1b1916', split: 'rgba(27, 25, 22, .2)',
    ok: '#5cc28a', warn: '#e0a64a', bad: '#ef6a5a', danger: '#b93a2c', 'on-danger': '#ffffff',
    track: 'rgba(255, 240, 220, .08)', selected: '#24211d', focus: '#f2ede4', scrim: 'rgba(0, 0, 0, .55)',
    shadow: 'rgba(0, 0, 0, .55)', 'shadow-soft': 'rgba(0, 0, 0, .3)',
    'warn-bg': 'rgba(224, 166, 74, .1)', 'warn-line': 'rgba(224, 166, 74, .32)',
    'bad-bg': 'rgba(239, 106, 90, .1)', 'bad-line': 'rgba(239, 106, 90, .32)'
  },
  black: {
    bg: '#0a0a0a', chrome: '#000000', side: '#0f0f0f', surface: '#141414', raised: '#1c1c1c',
    line: 'rgba(255, 255, 255, .08)', 'line-strong': 'rgba(255, 255, 255, .15)', 'input-border': 'rgba(255, 255, 255, .36)',
    dot: 'rgba(255, 255, 255, .08)', text: '#f5f5f5', 'text-2': '#a3a3a3', 'text-3': '#8f8f8f',
    accent: '#f5f5f5', 'on-accent': '#0a0a0a', split: 'rgba(10, 10, 10, .18)',
    ok: '#52c98a', warn: '#e8a838', bad: '#f26b5b', danger: '#b93a2c', 'on-danger': '#ffffff',
    track: 'rgba(255, 255, 255, .08)', selected: '#171717', focus: '#f5f5f5', scrim: 'rgba(0, 0, 0, .65)',
    shadow: 'rgba(0, 0, 0, .7)', 'shadow-soft': 'rgba(0, 0, 0, .4)',
    'warn-bg': 'rgba(232, 168, 56, .09)', 'warn-line': 'rgba(232, 168, 56, .32)',
    'bad-bg': 'rgba(242, 107, 91, .09)', 'bad-line': 'rgba(242, 107, 91, .32)'
  }
};

// In a high-contrast VS Code theme the setting is ignored and every role reads the matching variable.
const HIGH_CONTRAST = {
  bg: 'var(--vscode-editor-background)', chrome: 'var(--vscode-editor-background)',
  side: 'var(--vscode-sideBar-background, var(--vscode-editor-background))',
  surface: 'var(--vscode-editor-background)', raised: 'var(--vscode-editor-background)',
  line: 'var(--vscode-contrastBorder, var(--vscode-panel-border, currentColor))',
  'line-strong': 'var(--vscode-contrastActiveBorder, var(--vscode-contrastBorder, currentColor))',
  'input-border': 'var(--vscode-input-border, var(--vscode-contrastBorder, currentColor))',
  dot: 'transparent', text: 'var(--vscode-foreground)', 'text-2': 'var(--vscode-foreground)',
  'text-3': 'var(--vscode-foreground)', accent: 'var(--vscode-button-background)',
  'on-accent': 'var(--vscode-button-foreground)', split: 'var(--vscode-contrastBorder, currentColor)',
  ok: 'var(--vscode-charts-green, var(--vscode-foreground))',
  warn: 'var(--vscode-editorWarning-foreground, var(--vscode-charts-yellow, var(--vscode-foreground)))',
  bad: 'var(--vscode-errorForeground)', danger: 'var(--vscode-errorForeground)',
  'on-danger': 'var(--vscode-editor-background)', track: 'var(--vscode-contrastBorder, transparent)',
  selected: 'var(--vscode-list-activeSelectionBackground, var(--vscode-editor-background))',
  focus: 'var(--vscode-focusBorder)', scrim: 'rgba(0, 0, 0, .6)', shadow: 'transparent',
  'shadow-soft': 'transparent', 'warn-bg': 'var(--vscode-editor-background)',
  'warn-line': 'var(--vscode-editorWarning-foreground, currentColor)', 'bad-bg': 'var(--vscode-editor-background)',
  'bad-line': 'var(--vscode-errorForeground)'
};

// The setting's value as a theme name; anything else is the default.
function themeName(value) {
  return THEMES.indexOf(value) >= 0 ? value : DEFAULT_THEME;
}

// The role table to use: the matching --vscode-* variables in high contrast, else the chosen palette.
function resolve(setting, highContrast) {
  return highContrast ? HIGH_CONTRAST : PALETTES[themeName(setting)];
}

// The custom properties as CSS text for :root.
function cssVariables(setting, highContrast) {
  const table = resolve(setting, highContrast);
  return Object.keys(table).map((key) => '--' + key + ': ' + table[key] + ';').join(' ');
}

// A plugin's mark: its first letter in upper case and the next consonant (planning -> Pl, testing -> Ts,
// review -> Rv), or the initials of the first two words of a hyphenated name (skill-authoring -> SA).
function mark(name) {
  const text = String(name || '');
  if (!text) return '';
  const words = text.split('-').filter(Boolean);
  if (words.length > 1) return (words[0][0] + words[1][0]).toUpperCase();
  const next = text.slice(1).match(/[bcdfghjklmnpqrstvwxz]/i);
  return text[0].toUpperCase() + (next ? next[0].toLowerCase() : (text[1] || '').toLowerCase());
}

// Score colors on the percentage shown: 90 % and up is green, 60-89 % amber, under 60 % red.
function percent(score) {
  return Math.round(score * 100);
}

function scoreRole(score) {
  const pct = percent(score);
  return pct >= 90 ? 'ok' : pct >= 60 ? 'warn' : 'bad';
}

module.exports = { THEMES, DEFAULT_THEME, PALETTES, HIGH_CONTRAST, themeName, resolve, cssVariables, mark, percent, scoreRole };
