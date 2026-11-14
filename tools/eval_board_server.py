#!/usr/bin/env python3
"""Serve the eval board locally and run a case from it with one click.

tools/build_eval_board.py writes a static page: it can show cases and results but cannot start
anything. This server serves the same page with a Run form on every case. Running a case starts
tools/copilot_eval.py (Copilot CLI) or `claude plugin eval` (Claude Code) on this machine, streams
the output to the page, and asks the grading questions there, with Yes, No and Skip buttons. When
the run ends, the board reloads its results.

    python3 tools/eval_board_server.py              # opens http://127.0.0.1:<port>/?token=…
    python3 tools/eval_board_server.py --port 8765 --no-open

What it can do, and what it refuses:
- It listens on 127.0.0.1 only, accepts only Host 127.0.0.1 or localhost, and every request needs
  the random token printed at start (in the URL for the page, in a header for the API), so another
  web page cannot drive it.
- It runs only the eval cases that exist under plugins/*/evals, with validated options, one run at
  a time. It never runs a command given by the page.
- A run is billed to your plan (Copilot) or key (Claude), and lets the agent run commands in a
  scratch workspace as you, as the two runners do from a terminal. The page asks you to confirm.
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
MODEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")
EFFORTS = ("", "none", "minimal", "low", "medium", "high", "xhigh", "max")
CHOICES = re.compile(r"\[([a-z](?:/[a-z](?:=[^\]]*)?)+)\]\s*$")
STOP = object()


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
    """One run started from the page: its output, its current question, and how it ended."""

    def __init__(self, spec):
        self.spec = spec
        self.status = "running"
        self.lines = deque(maxlen=3000)
        self.question = None
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
        self.question = {"text": CHOICES.sub("", text).strip(),
                         "choices": [c.split("=")[0] for c in found.group(1).split("/")] if found else ["y", "n"]}
        reply = self.answers.get()
        self.question = None
        if reply is STOP:
            raise KeyboardInterrupt
        return reply

    def stop(self):
        self.stopping.set()
        self.answers.put(STOP)
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()

    def snapshot(self):
        return {"status": self.status, "case": self.spec["case"], "plugin": self.spec["plugin"],
                "host": self.spec["host"], "question": self.question, "log": list(self.lines),
                "seconds": round(time.time() - self.started)}


def run_copilot(job, spec):
    argv = [os.path.join(REPO, "plugins", spec["plugin"]), "--case", spec["case"], "--arms",
            "with" if spec["arms"] == "with" else "with,without", "--run"]
    if spec["model"]:
        argv += ["--model", spec["model"]]
    if spec["effort"]:
        argv += ["--reasoning-effort", spec["effort"]]
    writer = LineWriter(job.log)
    try:
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


def claude_command(spec, kind, claude):
    command = [claude, "plugin", "eval", "plugins/%s" % spec["plugin"], "--case", spec["case"], "--no-publish",
               "--scaffold", "--max-cost-usd", "%g" % spec["max_cost_usd"]]
    if kind == "behavior":
        command += ["--allow-tools", "Bash", "Write", "Edit"]
    if spec["arms"] == "with":
        command += ["--ablation", "none"]
    if spec["model"]:
        command += ["--model", spec["model"]]
    return command


def run_claude(job, spec, kind):
    claude = shutil.which("claude")
    command = claude_command(spec, kind, claude)
    job.log("$ " + " ".join(["claude"] + command[1:]))
    try:
        job.proc = subprocess.Popen(command, cwd=REPO, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True, bufsize=1)
    except OSError as exc:
        job.log("could not start claude: %s" % exc)
        job.status = "failed"
        return
    for line in job.proc.stdout:
        job.log(line.rstrip("\n"))
    code = job.proc.wait()
    if job.stopping.is_set():
        job.status = "stopped"
    elif code == 0:
        job.status = "done"
    else:
        job.status = "failed"
        job.log("claude plugin eval exited %d. If it says the directory is not trusted, run it once in a "
                "terminal and answer the prompt; this server never passes --trust-plugin." % code)


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


class Board:
    """The state the handlers share: the token, the catalog, and at most one job."""

    def __init__(self, token):
        self.token = token
        self.lock = threading.Lock()
        self.job = None

    def cases(self):
        return {(p["name"], c["name"]): c["kind"] for p in board.catalog() for c in p["cases"]}

    def state(self):
        return {"plugins": board.catalog(), "results": board.load_results(board.result_files())}

    def validate(self, body):
        plugin, case = str(body.get("plugin", "")), str(body.get("case", ""))
        kind = self.cases().get((plugin, case))
        if not kind:
            raise ValueError("unknown case: %s/%s" % (plugin, case))
        host = body.get("host")
        if host not in ("copilot", "claude"):
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
        tool = "copilot" if host == "copilot" else "claude"
        if not shutil.which(tool):
            raise ValueError("%s is not on PATH" % tool)
        return {"plugin": plugin, "case": case, "host": host, "arms": arms, "model": model,
                "effort": effort, "max_cost_usd": cost}, kind

    def start(self, body):
        spec, kind = self.validate(body)
        with self.lock:
            if self.job and self.job.status == "running":
                raise RuntimeError("another run is in progress")
            job = Job(spec)
            self.job = job
        target = (lambda: run_copilot(job, spec)) if spec["host"] == "copilot" else (lambda: run_claude(job, spec, kind))
        threading.Thread(target=target, daemon=True).start()
        return job.snapshot()


def make_handler(state, port_ref):
    class Handler(BaseHTTPRequestHandler):
        server_version = "EvalBoard/1"

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
                page = board.board(board.catalog(), board.load_results(board.result_files()), {"token": state.token})
                return self._send(200, page.encode("utf-8"), "text/html; charset=utf-8")
            if url.path == "/transcript":
                path = transcript_path((parse_qs(url.query).get("file") or [""])[0])
                if not path:
                    return self._send(404, {"error": "no such transcript"})
                with open(path, "rb") as fh:
                    return self._send(200, fh.read(), "text/plain; charset=utf-8")
            if url.path == "/api/state":
                return self._send(200, state.state())
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
            if url.path == "/api/run":
                try:
                    return self._send(200, state.start(body))
                except ValueError as exc:
                    return self._send(400, {"error": str(exc)})
                except RuntimeError as exc:
                    return self._send(409, {"error": str(exc)})
            job = state.job
            if url.path == "/api/answer":
                reply = body.get("reply")
                if not job or not job.question:
                    return self._send(409, {"error": "no question is waiting"})
                if reply not in job.question["choices"]:
                    return self._send(400, {"error": "answer one of %s" % "/".join(job.question["choices"])})
                job.answers.put(reply)
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
    state = Board(token or secrets.token_urlsafe(24))
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
    print("Eval board: %s" % url)
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
