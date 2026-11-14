#!/usr/bin/env python3
"""Skill manager: see every skill's goal, install state and eval status, install plugins, and run evals.

For people who develop the skills in this repository. It serves one local page with three tabs:

- Skills: one row per skill with its goal, its plugin's version, whether that plugin is installed in
  Copilot CLI and Claude Code, eval coverage in three directions (must fire, must stay quiet,
  behavior), the latest score per host, and a status, including "changed since last run" when the
  skill was committed after its latest result. "Run all cases" runs every case of the skill.
- Install: each plugin's version in this checkout and the version installed in each host, with
  Install, Update and Uninstall, and registering the marketplace from this checkout or from GitHub.
- Evals: the eval board (tools/build_eval_board.py), with a Run form on every case.

A run starts tools/copilot_eval.py (Copilot CLI) or `claude plugin eval` (Claude Code) on this
machine, streams the output to the page, and asks the grading questions there with Yes, No and Skip
buttons. When it ends, the page reloads.

    python3 tools/skill_manager.py              # opens http://127.0.0.1:<port>/?token=…
    python3 tools/skill_manager.py --port 8765 --no-open

What it can do, and what it refuses:
- It listens on 127.0.0.1 only, accepts only Host 127.0.0.1 or localhost, and every request needs
  the random token printed at start (in the URL for the page, in a header for the API), so another
  web page cannot drive it.
- It runs only eval cases that exist under plugins/*/evals and plugin commands it builds itself for
  plugins listed in the marketplace, with validated options, one job at a time. It never runs a
  command given by the page.
- An eval run is billed to your plan (Copilot) or key (Claude), and lets the agent run commands in a
  scratch workspace as you. Installing changes your Copilot or Claude Code configuration. The page
  asks you to confirm both.
- It never passes `--trust-plugin`. If `claude plugin eval` refuses an untrusted directory, run it
  once in a terminal and answer the prompt.

Standard library only.
"""

import argparse
import contextlib
import json
import os
import queue
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_eval_board as board  # noqa: E402
import copilot_eval  # noqa: E402

REPO = board.REPO
MARKETPLACE = "eurus-labs"
GITHUB_SOURCE = "eurus-labs/Skills"
MODEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")
EFFORTS = ("", "none", "minimal", "low", "medium", "high", "xhigh", "max")
# "[y/n/s=skip]": a label may not contain "/" or "]", so each option matches one way only (no backtracking).
CHOICES = re.compile(r"\[([a-z](?:/[a-z](?:=[^\]/]*)?)+)\]\s*$")
HOSTS = {"copilot": "copilot", "claude": "claude"}
STOP = object()
spawn = subprocess.Popen  # the one place a long-running command starts; the tests replace it


class LineWriter:
    """A file-like stdout that hands each finished line to `emit`."""

    def __init__(self, emit):
        self.emit, self.buffer = emit, ""

    def write(self, text):
        self.buffer += text
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            self.emit(line)
        return len(text)

    def flush(self):
        if self.buffer:
            self.emit(self.buffer)
            self.buffer = ""


class Job:
    """One job started from the page: its output, its current question, and how it ended."""

    def __init__(self, spec):
        self.spec = spec
        self.status = "running"
        self.lines = deque(maxlen=5000)
        self.question = None
        self.asked = 0
        self.answer_lock = threading.Lock()
        self.answers = queue.Queue()
        self.stopping = threading.Event()
        self.proc = None
        self.started = time.time()

    def log(self, line):
        self.lines.append(line)

    def ask(self, prompt=""):
        """The `answer` callable copilot_eval.main uses: the question goes to the page and waits."""
        if self.stopping.is_set():
            raise KeyboardInterrupt
        text = prompt.strip()
        if text.lower().startswith("press enter"):
            return ""
        found = CHOICES.search(text)
        with self.answer_lock:
            self.asked += 1
            self.question = {"id": self.asked, "text": CHOICES.sub("", text).strip(),
                             "choices": [c.split("=")[0] for c in found.group(1).split("/")] if found else ["y", "n"]}
        reply = self.answers.get()
        if reply is STOP:
            raise KeyboardInterrupt
        return reply

    def answer(self, question_id, reply):
        """Accept one answer for the question the person saw, once. Returns None, or why it was refused.

        The id ties an answer to the question shown: a second click, or a click that reaches the server after
        the runner moved on, must not grade a question the person never saw."""
        with self.answer_lock:
            question = self.question
            if not question or question["id"] != question_id:
                return "that question is no longer waiting"
            if reply not in question["choices"]:
                return "answer one of %s" % "/".join(question["choices"])
            self.question = None
            self.answers.put(reply)
        return None

    def stop(self):
        self.stopping.set()
        self.answers.put(STOP)
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()

    def snapshot(self):
        return {"status": self.status, "kind": self.spec["kind"], "title": self.spec["title"],
                "host": self.spec["host"], "question": self.question, "log": list(self.lines),
                "seconds": round(time.time() - self.started)}


def stream(job, command):
    """Run one command for a job, its output going to the job's log. Returns the exit code, or None."""
    job.log("$ " + " ".join([os.path.basename(command[0])] + command[1:]))
    try:
        job.proc = spawn(command, cwd=REPO, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True, bufsize=1)
    except OSError as exc:
        job.log("could not start %s: %s" % (command[0], exc))
        return None
    for line in job.proc.stdout:
        job.log(line.rstrip("\n"))
    return job.proc.wait()


def run_copilot(job, spec):
    """Each case in turn through copilot_eval.main; the Copilot check runs before the first only."""
    writer = LineWriter(job.log)
    try:
        for index, case in enumerate(spec["cases"]):
            if job.stopping.is_set():
                break
            argv = [os.path.join(REPO, "plugins", spec["plugin"]), "--case", case, "--arms",
                    "with" if spec["arms"] == "with" else "with,without", "--run"]
            if index:
                argv.append("--no-check")
            if spec["model"]:
                argv += ["--model", spec["model"]]
            if spec["effort"]:
                argv += ["--reasoning-effort", spec["effort"]]
            with contextlib.redirect_stdout(writer):
                copilot_eval.main(argv, answer=job.ask)
            writer.flush()
        job.status = "stopped" if job.stopping.is_set() else "done"
    except SystemExit as exc:
        writer.flush()
        if exc.code not in (0, None):
            job.log(str(exc.code))
        job.status = "failed" if exc.code not in (0, None) else "done"
    except KeyboardInterrupt:
        writer.flush()
        job.status = "stopped"


def claude_command(spec, case, kind, claude):
    command = [claude, "plugin", "eval", "plugins/%s" % spec["plugin"], "--case", case, "--no-publish",
               "--scaffold", "--max-cost-usd", "%g" % spec["max_cost_usd"]]
    if kind == "behavior":
        command += ["--allow-tools", "Bash", "Write", "Edit"]
    if spec["arms"] == "with":
        command += ["--ablation", "none"]
    if spec["model"]:
        command += ["--model", spec["model"]]
    return command


def run_claude(job, spec, kinds):
    claude = shutil.which("claude")
    failed = False
    for case in spec["cases"]:
        if job.stopping.is_set():
            break
        code = stream(job, claude_command(spec, case, kinds[case], claude))
        if code not in (0,) and not job.stopping.is_set():
            failed = True
            job.log("claude plugin eval exited %s. If it says the directory is not trusted, run it once in a "
                    "terminal and answer the prompt; this manager never passes --trust-plugin." % code)
    job.status = "stopped" if job.stopping.is_set() else "failed" if failed else "done"


def plugin_command(host, action, plugin=None, source=None):
    """The CLI command for an install action, built only from validated parts."""
    exe = shutil.which(HOSTS[host])
    ref = "%s@%s" % (plugin, MARKETPLACE) if plugin else None
    if action in ("install", "update", "uninstall"):
        return [exe, "plugin", action, ref]
    if action == "marketplace-add":
        return [exe, "plugin", "marketplace", "add", REPO if source == "checkout" else GITHUB_SOURCE]
    if action == "marketplace-update":
        return [exe, "plugin", "marketplace", "update", MARKETPLACE]
    raise ValueError("unknown action")


def run_commands(job, commands):
    for command in commands:
        if job.stopping.is_set():
            break
        code = stream(job, command)
        if code != 0 and not job.stopping.is_set():
            job.status = "failed"
            return
    job.status = "stopped" if job.stopping.is_set() else "done"


def list_json(command, timeout=60):
    """Parsed JSON from a read-only CLI listing, or (None, reason)."""
    try:
        proc = subprocess.run(command, cwd=REPO, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        return None, str(exc)
    if proc.returncode != 0:
        return None, (proc.stderr or proc.stdout).strip()[-300:]
    try:
        return json.loads(proc.stdout), None
    except ValueError:
        return None, "could not read the output of %s" % " ".join(command[1:])


def installed():
    """What each host has: the marketplace registration and this marketplace's plugins."""
    found = {}
    for host, exe_name in HOSTS.items():
        exe = shutil.which(exe_name)
        entry = {"available": bool(exe), "marketplace": None, "plugins": {}, "error": None}
        if exe:
            plugins, error = list_json([exe, "plugin", "list", "--json"])
            markets, error2 = list_json([exe, "plugin", "marketplace", "list", "--json"])
            entry["error"] = error or error2
            for market in markets or []:
                if isinstance(market, dict) and market.get("name") == MARKETPLACE:
                    entry["marketplace"] = market.get("source") if isinstance(market.get("source"), str) else "registered"
                    if market.get("path"):
                        entry["marketplace"] = "%s %s" % (market.get("source"), market["path"])
            for item in plugins or []:
                if not isinstance(item, dict):
                    continue
                if host == "copilot":
                    name, market = item.get("name"), item.get("marketplace")
                else:
                    name, _, market = (item.get("id") or "").partition("@")
                if market == MARKETPLACE and name:
                    entry["plugins"][name] = {"version": item.get("version"), "enabled": bool(item.get("enabled"))}
        found[host] = entry
    return found


def transcript_path(rel):
    """The file a transcript link names, only if it is a .md or .jsonl under plugins/*/evals/results/."""
    rel = rel.replace("\\", "/")
    if not re.match(r"^plugins/[a-z0-9-]+/evals/results/[^/]+/[^/]+\.(md|jsonl)$", rel) or ".." in rel:
        return None
    path = os.path.realpath(os.path.join(REPO, rel))
    root = os.path.realpath(os.path.join(REPO, "plugins"))
    if not path.startswith(root + os.sep) or not os.path.isfile(path):
        return None
    return path


class Manager:
    """The state the handlers share: the token and at most one job."""

    def __init__(self, token):
        self.token = token
        self.lock = threading.Lock()
        self.job = None

    def catalog(self):
        return board.catalog()

    def state(self):
        return {"plugins": self.catalog(), "results": board.load_results(board.result_files())}

    def _claim(self, spec, target):
        with self.lock:
            if self.job and self.job.status == "running":
                raise RuntimeError("another job is in progress")
            job = Job(spec)
            self.job = job
        def guarded():
            # Whatever goes wrong, the job ends: a job left "running" would block every later one.
            try:
                target(job)
            except BaseException as exc:  # noqa: B902 -- report it, never leave the job running
                job.log("the job stopped on an unexpected error: %s: %s" % (type(exc).__name__, exc))
                job.status = "failed"
            finally:
                if job.status == "running":
                    job.status = "failed"
        threading.Thread(target=guarded, daemon=True).start()
        return job.snapshot()

    def run_eval(self, body):
        catalog = {p["name"]: p for p in self.catalog()}
        plugin = str(body.get("plugin", ""))
        if plugin not in catalog:
            raise ValueError("unknown plugin: %s" % plugin)
        kinds = {c["name"]: c["kind"] for c in catalog[plugin]["cases"]}
        cases = body.get("cases") or ([body["case"]] if body.get("case") else [])
        if not isinstance(cases, list) or not cases or len(cases) > 100:
            raise ValueError("name one case, or a list of cases")
        cases = [str(c) for c in cases]
        unknown = [c for c in cases if c not in kinds]
        if unknown:
            raise ValueError("unknown case: %s/%s" % (plugin, unknown[0]))
        host = body.get("host")
        if host not in HOSTS:
            raise ValueError("host must be copilot or claude")
        arms = body.get("arms", "both")
        if arms not in ("both", "with"):
            raise ValueError("arms must be both or with")
        model = str(body.get("model") or "").strip()
        if model and not MODEL.match(model):
            raise ValueError("model names are letters, digits and . _ : -")
        effort = str(body.get("effort") or "").strip()
        if effort not in EFFORTS:
            raise ValueError("unknown reasoning effort")
        try:
            cost = float(body.get("max_cost_usd", 2))
        except (TypeError, ValueError):
            raise ValueError("cost ceiling must be a number")
        if not 0 < cost <= 50:
            raise ValueError("cost ceiling must be between 0 and 50 USD")
        if not shutil.which(HOSTS[host]):
            raise ValueError("%s is not on PATH" % HOSTS[host])
        title = cases[0] if len(cases) == 1 else "%s: %d cases" % (body.get("label") or plugin, len(cases))
        spec = {"kind": "eval", "title": title, "plugin": plugin, "cases": cases, "host": host, "arms": arms,
                "model": model, "effort": effort, "max_cost_usd": cost}
        if host == "copilot":
            return self._claim(spec, lambda job: run_copilot(job, spec))
        return self._claim(spec, lambda job: run_claude(job, spec, kinds))

    def run_install(self, body):
        host = body.get("host")
        if host not in HOSTS:
            raise ValueError("host must be copilot or claude")
        if not shutil.which(HOSTS[host]):
            raise ValueError("%s is not on PATH" % HOSTS[host])
        action = body.get("action")
        names = [p["name"] for p in self.catalog()]
        if action in ("install", "update", "uninstall"):
            plugins = body.get("plugins") or ([body["plugin"]] if body.get("plugin") else [])
            if not isinstance(plugins, list) or not plugins:
                raise ValueError("name a plugin")
            plugins = [str(p) for p in plugins]
            bad = [p for p in plugins if p not in names]
            if bad:
                raise ValueError("unknown plugin: %s" % bad[0])
            commands = [plugin_command(host, action, p) for p in plugins]
            title = "%s %s" % (action, plugins[0] if len(plugins) == 1 else "%d plugins" % len(plugins))
        elif action == "marketplace-add":
            source = body.get("source")
            if source not in ("checkout", "github"):
                raise ValueError("source must be checkout or github")
            commands = [plugin_command(host, action, source=source)]
            title = "register the marketplace from %s" % ("this checkout" if source == "checkout" else GITHUB_SOURCE)
        elif action == "marketplace-update":
            commands = [plugin_command(host, action)]
            title = "update the marketplace"
        else:
            raise ValueError("unknown action")
        spec = {"kind": "install", "title": title, "host": host}
        return self._claim(spec, lambda job: run_commands(job, commands))


def make_handler(state, port_ref):
    class Handler(BaseHTTPRequestHandler):
        server_version = "SkillManager/1"

        def log_message(self, fmt, *args):  # keep the terminal for the job's own output
            pass

        def _host_ok(self):
            host = (self.headers.get("Host") or "").lower()
            return host in ("127.0.0.1:%d" % port_ref[0], "localhost:%d" % port_ref[0])

        def _send(self, code, payload, kind="application/json; charset=utf-8"):
            data = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            self.wfile.write(data)

        def _authorized(self, url):
            if not self._host_ok():
                return False
            if url.path.startswith("/api/"):
                return secrets.compare_digest(self.headers.get("X-Board-Token", ""), state.token)
            return secrets.compare_digest((parse_qs(url.query).get("token") or [""])[0], state.token)

        def do_GET(self):
            url = urlparse(self.path)
            if not self._authorized(url):
                return self._send(403, {"error": "forbidden: open the URL printed by the server"})
            if url.path == "/":
                page = board.board(state.catalog(), board.load_results(board.result_files()), {"token": state.token})
                return self._send(200, page.encode("utf-8"), "text/html; charset=utf-8")
            if url.path == "/transcript":
                path = transcript_path((parse_qs(url.query).get("file") or [""])[0])
                if not path:
                    return self._send(404, {"error": "no such transcript"})
                with open(path, "rb") as fh:
                    return self._send(200, fh.read(), "text/plain; charset=utf-8")
            if url.path == "/api/state":
                return self._send(200, state.state())
            if url.path == "/api/installed":
                return self._send(200, installed())
            if url.path == "/api/job":
                return self._send(200, state.job.snapshot() if state.job else {"status": "idle"})
            return self._send(404, {"error": "not found"})

        def do_POST(self):
            url = urlparse(self.path)
            if not self._authorized(url) or not url.path.startswith("/api/"):
                return self._send(403, {"error": "forbidden"})
            length = int(self.headers.get("Content-Length") or 0)
            if length > 10000:
                return self._send(413, {"error": "request too large"})
            try:
                body = json.loads(self.rfile.read(length) or b"{}")
                if not isinstance(body, dict):
                    raise ValueError("expected a JSON object")
            except ValueError as exc:
                return self._send(400, {"error": "bad JSON: %s" % exc})
            if url.path in ("/api/run", "/api/install"):
                try:
                    start = state.run_eval if url.path == "/api/run" else state.run_install
                    return self._send(200, start(body))
                except ValueError as exc:
                    return self._send(400, {"error": str(exc)})
                except RuntimeError as exc:
                    return self._send(409, {"error": str(exc)})
            job = state.job
            if url.path == "/api/answer":
                if not job:
                    return self._send(409, {"error": "no question is waiting"})
                refused = job.answer(body.get("id"), body.get("reply"))
                if refused:
                    return self._send(400 if refused.startswith("answer one of") else 409, {"error": refused})
                return self._send(200, {"ok": True})
            if url.path == "/api/stop":
                if not job or job.status != "running":
                    return self._send(409, {"error": "nothing is running"})
                job.stop()
                return self._send(200, {"ok": True})
            return self._send(404, {"error": "not found"})

    return Handler


def serve(port=0, token=None):
    """(server, url) for a server on 127.0.0.1; call serve_forever() on it."""
    state = Manager(token or secrets.token_urlsafe(24))
    port_ref = [port]
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(state, port_ref))
    port_ref[0] = server.server_address[1]
    server.board = state
    return server, "http://127.0.0.1:%d/?token=%s" % (port_ref[0], state.token)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--port", type=int, default=0, help="port on 127.0.0.1 (default: any free one)")
    parser.add_argument("--no-open", action="store_true", help="do not open the browser")
    args = parser.parse_args(argv)
    server, url = serve(args.port)
    print("Skill manager: %s" % url)
    print("Only this machine can reach it. Press Ctrl+C to stop.")
    if not args.no_open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        if server.board.job and server.board.job.status == "running":
            server.board.job.stop()
        print("\nstopped")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
