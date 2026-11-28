'use strict';
const test = require('node:test');
const assert = require('node:assert');
const path = require('path');

const ev = require('../src/evalview');
const { sample } = require('./fixture');

const CASES = ['case-one', 'case-two', 'case-three', 'case-four'];
const plan = { plugin: 'planning', host: 'claude', hostLabel: 'Claude Code', cases: CASES, label: 'analyze-requirements \u00b7 4 cases' };

function snapshot(extra) {
  return Object.assign({ status: 'running', kind: 'eval', title: 'x', host: 'claude', question: null, log: [], progress: { index: 1, total: 4, item: 'case-one' }, tally: {}, stopping: false }, extra);
}

function statuses(view) {
  return view.items.map((i) => i.status);
}

test('a question with choices y, n and s gives three buttons and one /api/answer body', () => {
  const view = ev.jobView(snapshot({ question: { id: 7, text: 'Did it work?', choices: ['y', 'n', 's'] } }), plan, {});
  assert.deepStrictEqual(view.question.buttons, [{ reply: 'y', label: 'Yes' }, { reply: 'n', label: 'No' }, { reply: 's', label: 'Skip' }]);
  assert.strictEqual(view.question.text, 'Did it work?');
  assert.deepStrictEqual(ev.answerBody(view.question, 'y'), { id: 7, reply: 'y' });
  assert.deepStrictEqual(ev.answerBody(view.question, 's'), { id: 7, reply: 's' });
});

test('an answer the question does not offer is refused', () => {
  const view = ev.jobView(snapshot({ question: { id: 7, text: 'q', choices: ['y', 'n'] } }), plan, {});
  assert.strictEqual(ev.answerBody(view.question, 's'), null);
  assert.strictEqual(ev.answerBody(view.question, 'yes'), null);
  assert.strictEqual(ev.answerBody(view.question, undefined), null);
  assert.strictEqual(ev.answerBody(null, 'y'), null);
});

test('no question is shown once the job is no longer running', () => {
  const view = ev.jobView(snapshot({ status: 'stopped', question: { id: 7, text: 'q', choices: ['y', 'n'] } }), plan, {});
  assert.strictEqual(view.question, null);
});

test('running: finished cases, the one running, and the queued ones', () => {
  const view = ev.jobView(snapshot({ progress: { index: 3, total: 4, item: 'case-three' } }), plan, { 'case-one': 1, 'case-two': 0.5 });
  assert.deepStrictEqual(statuses(view), ['passed', 'failed', 'running', 'queued']);
  assert.deepStrictEqual(view.items.map((i) => i.state), ['100%', '50%', 'running', 'queued']);
  assert.strictEqual(view.meta, 'Claude Code \u00b7 2 of 4');
  assert.strictEqual(view.running, true);
  assert.strictEqual(view.pct, 50);
});

test('a finished case whose score is not read yet still shows as running', () => {
  const view = ev.jobView(snapshot({ progress: { index: 2, total: 4, item: 'case-two' } }), plan, {});
  assert.deepStrictEqual(statuses(view), ['running', 'running', 'queued', 'queued']);
});

test('a stopped job marks its queued cases stopped and keeps the finished ones', () => {
  const view = ev.jobView(snapshot({ status: 'stopped', progress: { index: 3, total: 4, item: 'case-three' } }), plan, { 'case-one': 1, 'case-two': 0.95 });
  assert.deepStrictEqual(statuses(view), ['passed', 'passed', 'stopped', 'stopped']);
  assert.strictEqual(view.running, false);
  assert.strictEqual(view.error.title, 'Stopped');
  assert.deepStrictEqual(view.error.buttons.map((b) => b.label), ['Run the rest']);
  assert.deepStrictEqual(view.remaining, ['case-three', 'case-four']);
  assert.match(view.meta, /stopped/);
});

test('a failed job keeps the finished cases and shows the engine message with the trust note', () => {
  const log = ['$ claude plugin eval plugins/planning --case case-three', 'claude plugin eval exited 1. If it says the directory is not trusted, run it once in a terminal.'];
  const view = ev.jobView(snapshot({ status: 'failed', progress: { index: 3, total: 4, item: 'case-three' }, log }), plan, { 'case-one': 1, 'case-two': 1 });
  assert.deepStrictEqual(statuses(view), ['passed', 'passed', 'failed', 'stopped']);
  assert.match(view.error.title, /^claude plugin eval exited 1/);
  assert.strictEqual(view.error.body, 'If it says the folder is not trusted, run it once in a terminal and answer the prompt. The extension never passes --trust-plugin.');
  assert.deepStrictEqual(view.error.buttons.map((b) => b.label), ['Show output', 'Run the rest']);
});

test('an engine that exited while the run was open is an error with the finished cases kept', () => {
  const view = ev.jobView(snapshot({ progress: { index: 2, total: 4, item: 'case-two' } }), plan, { 'case-one': 1 }, true);
  assert.strictEqual(view.running, false);
  assert.strictEqual(view.question, null);
  assert.strictEqual(view.error.title, 'The eval engine stopped');
  assert.strictEqual(view.items[0].status, 'passed');
});

test('a done job with no score for a case says "no result" instead of passing it', () => {
  const view = ev.jobView(snapshot({ status: 'done', progress: { index: 4, total: 4, item: 'case-four' } }), plan, { 'case-one': 1, 'case-two': 1, 'case-three': 1 });
  assert.deepStrictEqual(statuses(view), ['passed', 'passed', 'passed', 'failed']);
  assert.strictEqual(view.items[3].state, 'no result');
  assert.strictEqual(view.error, null);
  assert.strictEqual(view.pct, 100, 'the case with no result still counts as finished');
});

test('a job that has not reported its first case yet shows the first case as running', () => {
  const view = ev.jobView(snapshot({ progress: null }), plan, {});
  assert.deepStrictEqual(statuses(view), ['running', 'queued', 'queued', 'queued']);
});

test('log lines get a kind, so errors and commands can be styled', () => {
  assert.strictEqual(ev.lineKind('$ claude plugin eval'), 'cmd');
  assert.strictEqual(ev.lineKind('? Did it work?'), 'ask');
  assert.strictEqual(ev.lineKind('claude plugin eval exited 1.'), 'err');
  assert.strictEqual(ev.lineKind('  answered: y'), 'dim');
  assert.strictEqual(ev.lineKind('plain'), 'plain');
});

// --- transcripts ---

test('transcript lines are parsed and tied to a case', () => {
  const log = [
    '$ claude plugin eval plugins/planning --case case-one --no-publish',
    'transcript file: plugins/planning/evals/results/2026-11-28T00-00-00Z/case-one-with-1.md',
    '$ claude plugin eval plugins/planning --case case-two --no-publish',
    'transcript file: plugins/planning/evals/results/2026-11-28T00-00-00Z/run-7.jsonl',
    'transcript file: plugins/planning/evals/results/2026-11-28T00-00-00Z/case-four-without-1.md'
  ];
  assert.deepStrictEqual(ev.transcripts(log, CASES), [
    { path: 'plugins/planning/evals/results/2026-11-28T00-00-00Z/case-one-with-1.md', caseName: 'case-one' },
    { path: 'plugins/planning/evals/results/2026-11-28T00-00-00Z/run-7.jsonl', caseName: 'case-two' },
    { path: 'plugins/planning/evals/results/2026-11-28T00-00-00Z/case-four-without-1.md', caseName: 'case-four' }
  ]);
  const view = ev.jobView(snapshot({ log, progress: { index: 3, total: 4, item: 'case-three' } }), plan, { 'case-one': 1 });
  assert.strictEqual(view.items[0].transcript, 'plugins/planning/evals/results/2026-11-28T00-00-00Z/case-one-with-1.md');
  assert.strictEqual(view.items[2].transcript, null);
});

test('../x.md and a path outside plugins/*/evals/results/ are refused', () => {
  const bad = [
    '../x.md',
    'plugins/planning/evals/results/../../../../etc/passwd.md',
    'plugins/planning/evals/results/2026/../x.md',
    '/etc/passwd',
    'plugins/planning/evals/archive/2026-11-28T00-00-00Z/report.md',
    'plugins/planning/skills/x/SKILL.md',
    'plugins/Planning/evals/results/stamp/x.md',
    'plugins/planning/evals/results/stamp/x.html',
    'plugins/planning/evals/results/stamp/sub/x.md',
    'plugins/planning/evals/results/stamp/',
    'C:\\Windows\\win.ini',
    ''
  ];
  for (const rel of bad) {
    assert.strictEqual(ev.transcriptPath(rel), null, rel);
    assert.strictEqual(ev.resolveTranscript('/work/Skills', rel), null, rel);
  }
  const log = ['transcript file: ../x.md', 'transcript file: plugins/planning/evals/archive/s/x.md'];
  assert.deepStrictEqual(ev.transcripts(log, CASES), []);
});

test('a good transcript path resolves under plugins/ of the repository', () => {
  const rel = 'plugins/planning/evals/results/2026-11-28T00-00-00Z/case-one.md';
  assert.strictEqual(ev.transcriptPath(rel), rel);
  assert.strictEqual(ev.transcriptPath('plugins\\planning\\evals\\results\\s\\x.md'), 'plugins/planning/evals/results/s/x.md');
  assert.strictEqual(ev.resolveTranscript('/work/Skills', rel), path.resolve('/work/Skills', rel));
});

// --- scores, commands, dialog ---

test('a case counts as finished by this run only when its newest run is a new one', () => {
  const before = sample();
  const after = sample();
  const fires = after.plugins[0].cases[0];
  fires.latest.claude = { stamp: '2026-11-28T10-00-00-000Z', score: 0.8, runs: 3, trusted: true };
  const quiet = after.plugins[0].cases[1];
  quiet.latest.claude = { stamp: '2026-11-28T10-00-00-000Z', score: null, runs: 3, trusted: false };
  const names = ['analyze-requirements-fires', 'analyze-requirements-quiet', 'analyze-requirements-works', 'nope'];
  assert.deepStrictEqual(ev.freshScores(before, after, 'claude', names), { 'analyze-requirements-fires': 0.8 });
  assert.deepStrictEqual(ev.freshScores(before, before, 'claude', names), {});
  assert.deepStrictEqual(ev.freshScores(null, after, 'claude', names), { 'analyze-requirements-fires': 0.8 });
});

test('the cost ceiling must be over 0 and at most 50', () => {
  assert.strictEqual(ev.costCeiling(2), 2);
  assert.strictEqual(ev.costCeiling('7.5'), 7.5);
  assert.strictEqual(ev.costCeiling(50), 50);
  for (const bad of [0, -1, 50.01, 500, 'x', null, undefined, NaN, Infinity]) assert.strictEqual(ev.costCeiling(bad), null, String(bad));
});

test('the run dialog names the billing and the commands the engine will run', () => {
  const claude = ev.runDialog('claude', 'Claude Code', ['a', 'b'], 2);
  assert.strictEqual(claude.title, 'Run 2 eval cases on Claude Code?');
  assert.strictEqual(claude.body, 'Billed to your Claude key, with a $2 ceiling. The agent runs commands in a scratch workspace as you. You may be asked to grade some runs.');
  const copilot = ev.runDialog('copilot', 'Copilot CLI', ['only-case'], 2);
  assert.strictEqual(copilot.title, 'Run only-case on Copilot CLI?');
  assert.match(copilot.body, /^Billed to your Copilot plan\. The agent runs commands in a scratch workspace as you\./);
  const [first, second] = ev.runCommands('claude', 'planning', ['a', 'b'], { a: 'fires', b: 'behavior' }, 2);
  assert.strictEqual(first, 'claude plugin eval plugins/planning --case a --no-publish --scaffold --max-cost-usd 2');
  assert.match(second, /--allow-tools Bash Write Edit$/);
  assert.ok(ev.runCommands('copilot', 'planning', ['a'], {}, 2)[0].startsWith('python3 tools/copilot_eval.py plugins/planning --case a'));
  assert.ok(ev.runCommands('claude', 'planning', ['a'], {}, 2).every((c) => !c.includes('--trust-plugin')));
});

test('log, case and question text holding <script> stays text in the view model', () => {
  const evil = '<script>alert(1)</script>';
  const view = ev.jobView(snapshot({ log: [evil], question: { id: 1, text: evil, choices: ['y'] } }), plan, {});
  assert.strictEqual(view.lines[0].text, evil);
  assert.strictEqual(view.question.text, evil);
});
