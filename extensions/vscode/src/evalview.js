'use strict';
// From the engine's job snapshot to what the Eval run tray draws, and the rules for transcripts and answers.
// No `vscode` import.

const path = require('path');

// The same rule as tools/skill_manager.py transcript_path: a .md or .jsonl one folder below results/.
const TRANSCRIPT_PATH = /^plugins\/[a-z0-9-]+\/evals\/results\/[^/]+\/[^/]+\.(md|jsonl)$/;
const TRANSCRIPT_LINE = /^transcript file: (.+)$/;
const CASE_FLAG = /--case\s+([a-z0-9][a-z0-9-]*)/;
const PASS_FROM = 0.6;
const CHOICE_LABEL = { y: 'Yes', n: 'No', s: 'Skip' };
const TRUST_NOTE = 'If it says the folder is not trusted, run it once in a terminal and answer the prompt. ' +
  'The extension never passes --trust-plugin.';

// The relative path a transcript line names, or null when it is not one the engine would serve.
function transcriptPath(rel) {
  const clean = String(rel || '').replace(/\\/g, '/');
  if (!TRANSCRIPT_PATH.test(clean) || clean.indexOf('..') >= 0) return null;
  return clean;
}

// The absolute file to open: the repository folder plus the checked path, and only if it stays under plugins/.
function resolveTranscript(repo, rel) {
  const clean = transcriptPath(rel);
  if (!clean) return null;
  const file = path.resolve(repo, clean);
  const root = path.resolve(repo, 'plugins') + path.sep;
  return file.indexOf(root) === 0 ? file : null;
}

// Every transcript the log names, tied to a case: by the case name in the file name, else by the `--case` of the
// last command line, else null.
function transcripts(log, caseNames) {
  const found = [];
  let current = null;
  (log || []).forEach((line) => {
    const flag = CASE_FLAG.exec(line);
    if (flag && line.indexOf('$ ') === 0) current = flag[1];
    const hit = TRANSCRIPT_LINE.exec(line);
    if (!hit) return;
    const rel = transcriptPath(hit[1]);
    if (!rel) return;
    const base = rel.split('/').pop();
    const byName = caseNames.filter((n) => base.indexOf(n) >= 0).sort((a, b) => b.length - a.length)[0];
    found.push({ path: rel, caseName: byName || (caseNames.indexOf(current) >= 0 ? current : null) });
  });
  return found;
}

// Scores of the cases that finished after the run began: a case counts only when its newest run on the host is
// not the one that was newest before the run.
function freshScores(before, after, host, cases) {
  const scores = {};
  const pick = (catalog, name) => {
    if (!catalog) return null;
    for (const plugin of catalog.plugins) {
      const found = plugin.cases.find((c) => c.name === name);
      if (found) return found.latest[host] || null;
    }
    return null;
  };
  cases.forEach((name) => {
    const was = pick(before, name);
    const now = pick(after, name);
    if (now && (!was || was.stamp !== now.stamp) && now.score !== null) scores[name] = now.score;
  });
  return scores;
}

function lineKind(line) {
  if (line.indexOf('$ ') === 0) return 'cmd';
  if (line.indexOf('? ') === 0) return 'ask';
  if (/exited \d|could not start|unexpected error|Traceback|error:/i.test(line)) return 'err';
  if (/^\s+answered:/.test(line)) return 'dim';
  return 'plain';
}

// The first line that says why a run failed, or the last line of the log.
function exitMessage(log) {
  const lines = (log || []).filter((l) => l.trim());
  const hit = lines.slice().reverse().find((l) => /exited \d|could not start|unexpected error|failed/i.test(l));
  return (hit || lines[lines.length - 1] || 'The run failed').slice(0, 200);
}

// The view model of the tray. `snapshot` is /api/job, `plan` is {plugin, host, hostLabel, cases, label}, `fresh` is
// freshScores(). `engineGone` is set when the engine exited while the run was open.
function jobView(snapshot, plan, fresh, engineGone) {
  const snap = snapshot || { status: 'idle' };
  const total = plan.cases.length;
  const running = snap.status === 'running';
  const ended = !running;
  const index = snap.progress && snap.progress.index ? snap.progress.index : 0;
  const files = transcripts(snap.log, plan.cases);
  const items = plan.cases.map((name, at) => {
    const position = at + 1;
    const have = Object.prototype.hasOwnProperty.call(fresh || {}, name);
    const score = have ? fresh[name] : null;
    let status;
    if (running) status = position < index ? 'finished' : position === index ? 'running' : 'queued';
    else if (snap.status === 'done') status = 'finished';
    else if (position < index) status = 'finished';
    else if (snap.status === 'failed' && position === index) status = 'failed-run';
    else status = 'stopped';
    // While the run goes on, a finished case whose score has not been read yet still shows as running.
    if (status === 'finished') status = have ? (score >= PASS_FROM ? 'passed' : 'failed') : running ? 'running' : 'failed';
    if (status === 'failed-run') status = 'failed';
    const file = files.find((f) => f.caseName === name);
    return { name, status, score, scoreText: have && score !== null ? Math.round(score * 100) + '%' : '',
      transcript: file ? file.path : null };
  });
  // A job that has not reported its first case yet shows the first case as running.
  if (running && index === 0 && items.length) items[0].status = 'running';
  const finished = items.filter((i) => i.status === 'passed' || i.status === 'failed').length;
  const stateText = (i) => i.scoreText || (i.status === 'failed' && ended ? 'no result' : i.status === 'passed' ? '' : i.status);
  const question = running && snap.question && !engineGone
    ? { id: snap.question.id, text: String(snap.question.text), choices: snap.question.choices.slice(),
        buttons: snap.question.choices.map((c) => ({ reply: c, label: CHOICE_LABEL[c] || c.toUpperCase() })) }
    : null;
  let error = null;
  if (engineGone) {
    error = { title: 'The eval engine stopped', body: 'It exited while the run was open. Finished cases keep their results.', tone: 'bad',
      buttons: [{ label: 'Show output', act: 'show-output' }, { label: 'Run the rest', act: 'run-rest', quiet: true }] };
  } else if (snap.status === 'failed') {
    error = { title: exitMessage(snap.log), body: TRUST_NOTE, tone: 'bad',
      buttons: [{ label: 'Show output', act: 'show-output' }, { label: 'Run the rest', act: 'run-rest', quiet: true }] };
  } else if (snap.status === 'stopped') {
    error = { title: 'Stopped', body: 'Finished cases keep their results.', tone: 'plain',
      buttons: [{ label: 'Run the rest', act: 'run-rest' }] };
  }
  const pct = ended ? Math.round(finished / Math.max(1, total) * 100) : Math.max(3, Math.round(finished / Math.max(1, total) * 100));
  return {
    title: plan.label || plan.cases[0] || snap.title || '', host: plan.host, hostLabel: plan.hostLabel || plan.host,
    meta: (plan.hostLabel || plan.host) + ' · ' + finished + ' of ' + total +
      (snap.status === 'done' ? ' · finished' : snap.status === 'stopped' ? ' · stopped' : snap.status === 'failed' ? ' · failed' : ''),
    running: running && !engineGone, stopping: !!snap.stopping, status: engineGone ? 'failed' : snap.status, pct,
    items: items.map((i) => Object.assign({}, i, { state: stateText(i) })),
    lines: (snap.log || []).map((text) => ({ text, kind: lineKind(text) })),
    question, error,
    remaining: items.filter((i) => i.status !== 'passed').map((i) => i.name)
  };
}

// The /api/answer body for a button, only when the reply is one the displayed question offers.
function answerBody(question, reply) {
  if (!question || typeof reply !== 'string' || question.choices.indexOf(reply) < 0) return null;
  return { id: question.id, reply };
}

// The command the engine will run for a request, shown in the confirmation dialog (mirrors skill_manager.py).
function runCommands(host, plugin, cases, kinds, maxCost) {
  if (host === 'claude') {
    return cases.map((name) => {
      const parts = ['claude', 'plugin', 'eval', 'plugins/' + plugin, '--case', name, '--no-publish', '--scaffold',
        '--max-cost-usd', String(maxCost)];
      if (kinds[name] === 'behavior') parts.push('--allow-tools', 'Bash', 'Write', 'Edit');
      return parts.join(' ');
    });
  }
  return cases.map((name) => ['python3', 'tools/copilot_eval.py', 'plugins/' + plugin, '--case', name, '--arms', 'with,without', '--run'].join(' '));
}

// The wording of the dialog before a run. N is the cost ceiling (over 0, at most 50).
function runDialog(host, hostLabel, cases, maxCost) {
  const billing = host === 'claude' ? 'Billed to your Claude key, with a $' + maxCost + ' ceiling.' : 'Billed to your Copilot plan.';
  return {
    title: 'Run ' + (cases.length === 1 ? cases[0] : cases.length + ' eval cases') + ' on ' + hostLabel + '?',
    body: billing + ' The agent runs commands in a scratch workspace as you. You may be asked to grade some runs.'
  };
}

// The cost ceiling from the setting, or null when it is not a number over 0 and at most 50.
function costCeiling(value) {
  const n = typeof value === 'number' ? value : Number(value);
  return isFinite(n) && n > 0 && n <= 50 ? n : null;
}

module.exports = { TRANSCRIPT_PATH, TRUST_NOTE, PASS_FROM, transcriptPath, resolveTranscript, transcripts, freshScores, lineKind,
  exitMessage, jobView, answerBody, runCommands, runDialog, costCeiling };
