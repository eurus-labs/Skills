'use strict';
const test = require('node:test');
const assert = require('node:assert');
const http = require('node:http');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { EventEmitter } = require('events');
const { spawnSync } = require('child_process');

const engine = require('../src/engine');
const catalogs = require('../src/catalog');

const REPO = path.join(__dirname, '..', '..', '..');
const TOKEN = 'abcDEF123_-xyz789TOKEN';

test('the URL line is parsed for 127.0.0.1 only, and a token is required', () => {
  assert.deepStrictEqual(engine.parseUrlLine('Skill manager: http://127.0.0.1:43211/?token=' + TOKEN), { host: '127.0.0.1', port: 43211, token: TOKEN });
  for (const line of [
    'Skill manager: http://example.com:1/?token=x12345678',
    'Skill manager: http://localhost:8080/?token=' + TOKEN,
    'Skill manager: http://127.0.0.1:8080/',
    'Skill manager: http://127.0.0.1:8080/?token=',
    'Skill manager: http://127.0.0.1:0/?token=' + TOKEN,
    'Skill manager: http://127.0.0.1:99999/?token=' + TOKEN,
    'Skill manager: http://127.0.0.1.evil.com:8080/?token=' + TOKEN,
    'Skill manager: https://127.0.0.1:8080/?token=' + TOKEN,
    'x Skill manager: http://127.0.0.1:8080/?token=' + TOKEN,
    'Only this machine can reach it. Press Ctrl+C to stop.',
    ''
  ]) {
    assert.strictEqual(engine.parseUrlLine(line), null, line);
  }
});

test('http://example.com:1/?token=x is rejected, and so is a line without a token', () => {
  assert.strictEqual(engine.parseUrlLine('Skill manager: http://example.com:1/?token=x'), null);
  assert.strictEqual(engine.parseUrlLine('Skill manager: http://127.0.0.1:1/'), null);
});

test('the masked log contains no token', () => {
  const line = 'Skill manager: http://127.0.0.1:43211/?token=' + TOKEN;
  const masked = engine.maskToken(line, TOKEN);
  assert.ok(!masked.includes(TOKEN));
  assert.strictEqual(masked, 'Skill manager: http://127.0.0.1:43211/?token=…');
  assert.ok(!engine.maskToken('leaked ' + TOKEN + ' and ' + TOKEN, TOKEN).includes(TOKEN));
  assert.ok(!engine.maskToken('GET /?token=someOtherValue123', '').includes('someOtherValue123'), 'any token= value is masked');
  assert.strictEqual(engine.maskToken('nothing to hide', TOKEN), 'nothing to hide');
});

// --- the API client, against a fake engine on node:http ---

function fakeEngine(handler) {
  const seen = [];
  const server = http.createServer((req, res) => {
    let body = '';
    req.on('data', (c) => { body += c; });
    req.on('end', () => {
      seen.push({ method: req.method, url: req.url, token: req.headers['x-board-token'], host: req.headers.host, body });
      handler(req, res, body);
    });
  });
  return new Promise((resolve) => server.listen(0, '127.0.0.1', () => resolve({ server, seen, port: server.address().port })));
}

function json(res, status, doc) {
  res.writeHead(status, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(doc));
}

test('the client sends X-Board-Token on every call and the body as JSON', async () => {
  const fake = await fakeEngine((req, res) => json(res, 200, { status: 'idle', ok: true }));
  try {
    const api = new engine.EngineApi({ port: fake.port, token: TOKEN });
    await api.catalog();
    await api.job();
    await api.run({ plugin: 'planning', cases: ['a'], host: 'claude', arms: 'both', max_cost_usd: 2 });
    await api.answer(3, 'y');
    await api.stop();
    assert.deepStrictEqual(fake.seen.map((s) => s.method + ' ' + s.url), ['GET /api/catalog', 'GET /api/job', 'POST /api/run', 'POST /api/answer', 'POST /api/stop']);
    assert.ok(fake.seen.every((s) => s.token === TOKEN));
    assert.ok(fake.seen.every((s) => s.host === '127.0.0.1:' + fake.port));
    assert.deepStrictEqual(JSON.parse(fake.seen[2].body), { plugin: 'planning', cases: ['a'], host: 'claude', arms: 'both', max_cost_usd: 2 });
    assert.deepStrictEqual(JSON.parse(fake.seen[3].body), { id: 3, reply: 'y' });
  } finally {
    fake.server.close();
  }
});

test('a 409 "another job is in progress" is reported as a message', async () => {
  const fake = await fakeEngine((req, res) => json(res, 409, { error: 'another job is in progress' }));
  try {
    const api = new engine.EngineApi({ port: fake.port, token: TOKEN });
    await assert.rejects(api.run({ plugin: 'planning' }), (error) => {
      assert.strictEqual(error.message, 'another job is in progress');
      assert.strictEqual(error.status, 409);
      return true;
    });
  } finally {
    fake.server.close();
  }
});

test('a refusal without a JSON body, and an engine that is gone, give a message too', async () => {
  const fake = await fakeEngine((req, res) => { res.writeHead(500); res.end('oops'); });
  const api = new engine.EngineApi({ port: fake.port, token: TOKEN });
  await assert.rejects(api.job(), /HTTP 500/);
  fake.server.close();
  await assert.rejects(api.job(), /not reachable/);
});

test('a hung engine times out', async () => {
  const fake = await fakeEngine(() => {});
  const api = new engine.EngineApi({ port: fake.port, token: TOKEN, timeoutMs: 100 });
  try {
    await assert.rejects(api.job(), /did not answer in time/);
  } finally {
    fake.server.closeAllConnections();
    fake.server.close();
  }
});

// --- starting the engine, with a fake process ---

function fakeSpawn(script) {
  return (command, args, options) => {
    const child = new EventEmitter();
    child.stdout = new EventEmitter();
    child.stdout.setEncoding = () => {};
    child.stderr = new EventEmitter();
    child.stderr.setEncoding = () => {};
    child.killed = false;
    child.kill = () => { child.killed = true; process.nextTick(() => child.emit('exit', null)); };
    child.command = command;
    child.args = args;
    child.options = options;
    process.nextTick(() => script(child));
    return child;
  };
}

test('the engine is started with -u and --no-open in the repository, and its URL line gives the API', async () => {
  let started;
  const lines = [];
  const spawn = (...a) => { started = fakeSpawn((child) => {
    child.stdout.emit('data', 'Skill manager: http://127.0.0.1:5555/?token=' + TOKEN + '\nOnly this machine can reach it.\n');
  })(...a); return started; };
  const handle = await engine.startEngine({ python: 'python3', cwd: '/repo', spawn, onLine: (l) => lines.push(l), timeoutMs: 1000 });
  assert.strictEqual(started.command, 'python3');
  assert.deepStrictEqual(started.args, ['-u', path.join('tools', 'skill_manager.py'), '--no-open']);
  assert.strictEqual(started.options.cwd, '/repo');
  assert.strictEqual(handle.api.port, 5555);
  assert.strictEqual(handle.api.token, TOKEN);
  assert.ok(lines.every((l) => !l.includes(TOKEN)), 'the log never holds the token: ' + lines.join('|'));
  handle.stop();
  assert.strictEqual(started.killed, true);
  assert.deepStrictEqual(await handle.exited, { code: null });
});

test('a URL line split across chunks still starts the engine', async () => {
  const spawn = fakeSpawn((child) => {
    child.stdout.emit('data', 'Skill manager: http://127.0.0.1:5');
    child.stdout.emit('data', '555/?token=' + TOKEN + '\n');
  });
  const handle = await engine.startEngine({ python: 'python3', cwd: '/repo', spawn, timeoutMs: 1000 });
  assert.strictEqual(handle.api.port, 5555);
});

test('a missing python is "python-not-found"', async () => {
  const spawn = fakeSpawn((child) => { const e = new Error('spawn python3 ENOENT'); e.code = 'ENOENT'; child.emit('error', e); });
  await assert.rejects(engine.startEngine({ python: 'python3', cwd: '/repo', spawn, timeoutMs: 1000 }), (f) => f.code === 'python-not-found');
  const throwing = () => { const e = new Error('spawn python3 ENOENT'); e.code = 'ENOENT'; throw e; };
  await assert.rejects(engine.startEngine({ python: 'python3', cwd: '/repo', spawn: throwing, timeoutMs: 1000 }), (f) => f.code === 'python-not-found');
});

test('no URL within the timeout is "no-url", and the process is stopped', async () => {
  let child;
  const spawn = (...a) => { child = fakeSpawn((c) => { c.stdout.emit('data', 'starting up\n'); })(...a); return child; };
  await assert.rejects(engine.startEngine({ python: 'python3', cwd: '/repo', spawn, timeoutMs: 50 }), (f) => {
    assert.strictEqual(f.code, 'no-url');
    assert.deepStrictEqual(f.tail, ['starting up']);
    return true;
  });
  assert.strictEqual(child.killed, true);
});

test('an engine that exits before its URL is "exited", with the last output lines', async () => {
  const spawn = fakeSpawn((child) => {
    child.stderr.emit('data', 'Traceback (most recent call last):\nSyntaxError: invalid syntax\n');
    child.emit('exit', 1);
  });
  await assert.rejects(engine.startEngine({ python: 'python3', cwd: '/repo', spawn, timeoutMs: 1000 }), (f) => {
    assert.strictEqual(f.code, 'exited');
    assert.deepStrictEqual(f.tail, ['Traceback (most recent call last):', 'SyntaxError: invalid syntax']);
    return true;
  });
});

test('an engine that exits later resolves exited', async () => {
  let child;
  const spawn = (...a) => { child = fakeSpawn((c) => { c.stdout.emit('data', 'Skill manager: http://127.0.0.1:5555/?token=' + TOKEN + '\n'); })(...a); return child; };
  const handle = await engine.startEngine({ python: 'python3', cwd: '/repo', spawn, timeoutMs: 1000 });
  child.emit('exit', 3);
  assert.deepStrictEqual(await handle.exited, { code: 3 });
});

test('each failure says what happened and what to do, and archived scores still show', () => {
  const missing = engine.describeFailure({ code: 'python-not-found' }, 'python3');
  assert.strictEqual(missing.title, '`python3` was not found');
  assert.match(missing.body, /Set `eurusSkills\.python` to your Python 3\.9 or later\. Scores from the archive still show\./);
  assert.match(engine.describeFailure({ code: 'no-url' }, 'python3').body, /within 15 s/);
  assert.match(engine.describeFailure({ code: 'exited' }, 'python3').body, /exited/);
  assert.match(engine.describeFailure({ code: 'untrusted' }, 'python3').title, /not trusted/);
  for (const code of ['python-not-found', 'no-url', 'exited', 'untrusted']) {
    assert.match(engine.describeFailure({ code }, 'python3').body, /archive/);
  }
});

test('a folder is this repository when it holds the engine and a marketplace named eurus-labs', () => {
  assert.strictEqual(engine.isSkillsRepo(REPO, fs), true);
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'eurus-'));
  try {
    assert.strictEqual(engine.isSkillsRepo(tmp, fs), false);
    fs.mkdirSync(path.join(tmp, 'tools'));
    fs.mkdirSync(path.join(tmp, '.github', 'plugin'), { recursive: true });
    fs.writeFileSync(path.join(tmp, 'tools', 'skill_manager.py'), '');
    fs.writeFileSync(path.join(tmp, '.github', 'plugin', 'marketplace.json'), JSON.stringify({ name: 'someone-else' }));
    assert.strictEqual(engine.isSkillsRepo(tmp, fs), false);
    fs.writeFileSync(path.join(tmp, '.github', 'plugin', 'marketplace.json'), '{broken');
    assert.strictEqual(engine.isSkillsRepo(tmp, fs), false);
    fs.writeFileSync(path.join(tmp, '.github', 'plugin', 'marketplace.json'), JSON.stringify({ name: 'eurus-labs' }));
    assert.strictEqual(engine.isSkillsRepo(tmp, fs), true);
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});

// --- the real engine ---

const python = spawnSync('python3', ['--version']);

test('the real engine starts headless, serves /api/catalog behind its token, and stops', { skip: python.status === 0 ? false : 'python3 is not installed' }, async () => {
  const lines = [];
  const handle = await engine.startEngine({ python: 'python3', cwd: REPO, onLine: (l) => lines.push(l), timeoutMs: 15000 });
  try {
    const raw = await handle.api.catalog();
    const checked = catalogs.validateCatalog(raw);
    assert.strictEqual(checked.ok, true, checked.error);
    assert.strictEqual(checked.catalog.plugins.length, 9);
    const job = await handle.api.job();
    assert.strictEqual(job.status, 'idle');
    const wrong = new engine.EngineApi({ port: handle.api.port, token: 'not-the-token-at-all' });
    await assert.rejects(wrong.catalog(), (e) => e.status === 403);
    await assert.rejects(handle.api.stop(), (e) => e.status === 409 && /nothing is running/.test(e.message));
    assert.ok(lines.every((l) => !l.includes(handle.api.token)));
  } finally {
    handle.stop();
  }
  const ended = await handle.exited;
  assert.ok(ended.code === null || typeof ended.code === 'number');
});
