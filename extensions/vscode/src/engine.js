'use strict';
// The eval engine: tools/skill_manager.py run headless, and a small client for its local API.
// The token it prints lives in this module and in the extension host only; it never reaches a webview or a log.
// No `vscode` import.

const http = require('http');
const path = require('path');
const childProcess = require('child_process');

const URL_LINE = /^Skill manager: http:\/\/(127\.0\.0\.1):(\d{1,5})\/\?token=([A-Za-z0-9_-]{8,128})\s*$/;
const START_TIMEOUT_MS = 15000;
const REQUEST_TIMEOUT_MS = 15000;
const TAIL_LINES = 20;

// {host, port, token} from the line the engine prints, or null. Only 127.0.0.1 is accepted, and a token is required.
function parseUrlLine(line) {
  const found = URL_LINE.exec(String(line));
  if (!found) return null;
  const port = Number(found[2]);
  if (!(port >= 1 && port <= 65535)) return null;
  return { host: found[1], port, token: found[3] };
}

// The text with the token replaced by an ellipsis; any `token=...` is masked too, whatever its value.
function maskToken(value, token) {
  let out = String(value);
  if (token) out = out.split(token).join('…');
  return out.replace(/token=[A-Za-z0-9_-]+/g, 'token=…');
}

// Is this folder a checkout of this marketplace? It holds the engine and a marketplace named eurus-labs.
function isSkillsRepo(folder, fs) {
  try {
    if (!fs.statSync(path.join(folder, 'tools', 'skill_manager.py')).isFile()) return false;
    const manifest = JSON.parse(fs.readFileSync(path.join(folder, '.github', 'plugin', 'marketplace.json'), 'utf8'));
    return !!manifest && manifest.name === 'eurus-labs';
  } catch (error) {
    return false;
  }
}

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

// The engine's API over Node http, with X-Board-Token on every request.
class EngineApi {
  constructor(options) {
    this.host = options.host || '127.0.0.1';
    this.port = options.port;
    this.token = options.token;
    this.timeoutMs = options.timeoutMs || REQUEST_TIMEOUT_MS;
  }

  request(method, route, body) {
    return new Promise((resolve, reject) => {
      const payload = body === undefined ? null : Buffer.from(JSON.stringify(body), 'utf8');
      const headers = { 'X-Board-Token': this.token, Accept: 'application/json' };
      if (payload) {
        headers['Content-Type'] = 'application/json';
        headers['Content-Length'] = payload.length;
      }
      const req = http.request({ host: this.host, port: this.port, method, path: route, headers }, (res) => {
        const chunks = [];
        res.on('data', (chunk) => chunks.push(chunk));
        res.on('end', () => {
          const raw = Buffer.concat(chunks).toString('utf8');
          let data = null;
          try {
            data = raw ? JSON.parse(raw) : null;
          } catch (error) {
            data = null;
          }
          if (res.statusCode >= 200 && res.statusCode < 300) {
            resolve(data);
            return;
          }
          reject(new ApiError((data && data.error) || 'The eval engine answered HTTP ' + res.statusCode, res.statusCode));
        });
        res.on('error', (error) => reject(new ApiError(error.message, 0)));
      });
      req.on('error', (error) => reject(new ApiError('The eval engine is not reachable: ' + error.message, 0)));
      req.setTimeout(this.timeoutMs, () => {
        req.destroy();
        reject(new ApiError('The eval engine did not answer in time', 0));
      });
      if (payload) req.write(payload);
      req.end();
    });
  }

  catalog() { return this.request('GET', '/api/catalog'); }
  job() { return this.request('GET', '/api/job'); }
  run(body) { return this.request('POST', '/api/run', body); }
  answer(id, reply) { return this.request('POST', '/api/answer', { id, reply }); }
  stop() { return this.request('POST', '/api/stop', {}); }
}

// What to tell the person when the engine cannot be used. `failure` is {code, message, tail}.
function describeFailure(failure, python) {
  const script = 'tools/skill_manager.py';
  const archive = 'Scores from the archive still show.';
  switch (failure && failure.code) {
    case 'python-not-found':
      return { title: '`' + python + '` was not found',
        body: 'Running evals needs `' + script + '`. Set `eurusSkills.python` to your Python 3.9 or later. ' + archive };
    case 'no-url':
      return { title: 'The eval engine did not start',
        body: 'No address came from `' + script + '` within 15 s. ' + archive + ' The last output lines are in the Eurus Skills output channel.' };
    case 'exited':
      return { title: 'The eval engine stopped',
        body: 'It exited before a run could finish. ' + archive + ' The last output lines are in the Eurus Skills output channel.' };
    case 'untrusted':
      return { title: 'This workspace is not trusted',
        body: 'Running evals starts `' + script + '` from the workspace. Trust the workspace to allow it. ' + archive };
    default:
      return { title: 'The eval engine did not start', body: String((failure && failure.message) || 'Unknown error') + ' ' + archive };
  }
}

// Start the engine. Resolves {api, stop, exited} once its address line arrives, and rejects with
// {code: 'python-not-found' | 'no-url' | 'exited', message, tail}. `spawn` and `onLine` are replaceable in tests;
// onLine gets every output line with the token already masked.
function startEngine(options) {
  const spawn = options.spawn || childProcess.spawn;
  const timeoutMs = options.timeoutMs || START_TIMEOUT_MS;
  const onLine = options.onLine || (() => {});
  return new Promise((resolve, reject) => {
    const tail = [];
    let token = '';
    let started = false;
    let settled = false;
    let child;
    let timer;
    const settle = (fn, value) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      fn(value);
    };
    const failure = (code, message) => ({ code, message, tail: tail.slice() });
    let onExit = () => {};
    const exited = new Promise((done) => { onExit = done; });
    try {
      child = spawn(options.python, ['-u', path.join('tools', 'skill_manager.py'), '--no-open'],
        { cwd: options.cwd, stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true });
    } catch (error) {
      reject(failure(error && error.code === 'ENOENT' ? 'python-not-found' : 'exited', String(error.message || error)));
      return;
    }
    const stop = () => {
      try { child.kill(); } catch (error) { /* already gone */ }
    };
    const feed = (stream) => {
      let buffer = '';
      stream.setEncoding('utf8');
      stream.on('data', (chunk) => {
        buffer += chunk;
        let at = buffer.indexOf('\n');
        while (at >= 0) {
          const line = buffer.slice(0, at).replace(/\r$/, '');
          buffer = buffer.slice(at + 1);
          const parsed = started ? null : parseUrlLine(line);
          if (parsed) {
            started = true;
            token = parsed.token;
            settle(resolve, { api: new EngineApi({ host: parsed.host, port: parsed.port, token }), stop, exited });
          }
          const masked = maskToken(line, token);
          tail.push(masked);
          if (tail.length > TAIL_LINES) tail.shift();
          onLine(masked);
          at = buffer.indexOf('\n');
        }
      });
    };
    if (child.stdout) feed(child.stdout);
    if (child.stderr) feed(child.stderr);
    child.on('error', (error) => {
      settle(reject, failure(error && error.code === 'ENOENT' ? 'python-not-found' : 'exited', String(error.message || error)));
      onExit({ code: null });
    });
    child.on('exit', (code) => {
      settle(reject, failure('exited', 'The eval engine exited with code ' + code));
      onExit({ code });
    });
    timer = setTimeout(() => {
      settle(reject, failure('no-url', 'No address within ' + Math.round(timeoutMs / 1000) + ' s'));
      stop();
    }, timeoutMs);
  });
}

module.exports = { URL_LINE, START_TIMEOUT_MS, parseUrlLine, maskToken, isSkillsRepo, ApiError, EngineApi, describeFailure, startEngine };
