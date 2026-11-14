#!/usr/bin/env python3
"""tools/eval_board_server.py must run only real cases, only for its own page, and ask the grading on the page.

The server starts commands on the user's machine from a browser, so the tests pin what a request
can and cannot do: no token or another Host is refused, unknown cases and odd options are refused,
one run at a time, `--trust-plugin` never appears. They also drive a whole run through the API with
the runners replaced, so nothing is billed and no agent runs.

    python3 tools/test_eval_board_server.py
"""

import http.client
import io
import json
import os
import shutil
import sys
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eval_board_server as ebs  # noqa: E402

REAL_WHICH = shutil.which


def on_path(*tools):
    return lambda name: ("/usr/bin/%s" % name) if name in tools else REAL_WHICH(name)


class Server(unittest.TestCase):
    def setUp(self):
        self.server, self.url = ebs.serve(0, token="t0k3n")
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def request(self, method, path, body=None, token="t0k3n", host=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        headers = {"Host": host or "127.0.0.1:%d" % self.port, "Content-Type": "application/json"}
        if token is not None:
            headers["X-Board-Token"] = token
        conn.request(method, path, body=json.dumps(body) if body is not None else None, headers=headers)
        res = conn.getresponse()
        data = res.read()
        conn.close()
        try:
            return res.status, json.loads(data)
        except ValueError:
            return res.status, data.decode("utf-8")

    def wait_for(self, predicate, timeout=10):
        deadline = time.time() + timeout
        while time.time() < deadline:
            _, job = self.request("GET", "/api/job")
            if predicate(job):
                return job
            time.sleep(0.05)
        self.fail("timed out; last job state: %r" % job)


class Access(Server):
    def test_the_page_needs_the_token_in_its_url(self):
        self.assertEqual(self.request("GET", "/", token=None)[0], 403)
        status, page = self.request("GET", "/?token=t0k3n", token=None)
        self.assertEqual(status, 200)
        self.assertIn('const SERVER = {"token": "t0k3n"}', page)
        self.assertIn('id="runpanel"', page)

    def test_the_api_needs_the_token_header(self):
        self.assertEqual(self.request("GET", "/api/job", token=None)[0], 403)
        self.assertEqual(self.request("GET", "/api/job", token="wrong")[0], 403)
        self.assertEqual(self.request("GET", "/api/job")[0], 200)

    def test_another_host_name_is_refused(self):
        # A page on another site that rebinds its DNS name to 127.0.0.1 still sends its own Host.
        self.assertEqual(self.request("GET", "/api/job", host="evil.example:%d" % self.port)[0], 403)
        self.assertEqual(self.request("GET", "/api/job", host="localhost:%d" % self.port)[0], 200)

    def test_only_real_cases_and_sane_options_run(self):
        with patch("shutil.which", side_effect=on_path("copilot", "claude")):
            bad = [
                {"plugin": "verification", "case": "no-such-case", "host": "copilot"},
                {"plugin": "../../etc", "case": "passwd", "host": "copilot"},
                {"plugin": "verification", "case": "none-implement-feature", "host": "bash"},
                {"plugin": "verification", "case": "none-implement-feature", "host": "copilot", "model": "x; rm -rf /"},
                {"plugin": "verification", "case": "none-implement-feature", "host": "copilot", "effort": "huge"},
                {"plugin": "verification", "case": "none-implement-feature", "host": "claude", "max_cost_usd": 500},
            ]
            for body in bad:
                status, data = self.request("POST", "/api/run", body)
                self.assertEqual(status, 400, (body, data))

    def test_a_missing_runner_is_reported(self):
        with patch("shutil.which", side_effect=lambda name: None if name == "copilot" else REAL_WHICH(name)):
            status, data = self.request("POST", "/api/run",
                                        {"plugin": "verification", "case": "none-implement-feature", "host": "copilot"})
        self.assertEqual(status, 400)
        self.assertIn("not on PATH", data["error"])


class Transcripts(Server):
    def test_only_result_transcripts_are_served(self):
        folder = os.path.join(ebs.REPO, "plugins", "verification", "evals", "results", "copilot-2099-01-06T00-00-00Z")
        os.makedirs(folder)
        self.addCleanup(shutil.rmtree, folder, ignore_errors=True)
        with open(os.path.join(folder, "c-with.md"), "w") as fh:
            fh.write("# transcript\n")
        ok = "/transcript?token=t0k3n&file=plugins/verification/evals/results/copilot-2099-01-06T00-00-00Z/c-with.md"
        status, body = self.request("GET", ok, token=None)
        self.assertEqual((status, body), (200, "# transcript\n"))
        for bad in ("AGENTS.md", "fixtures/EXPECTED.md", "plugins/verification/evals/results/../../../AGENTS.md",
                    "plugins/verification/evals/trigger/none-implement-feature/prompt.md"):
            status, _ = self.request("GET", "/transcript?token=t0k3n&file=" + bad, token=None)
            self.assertEqual(status, 404, bad)
        self.assertEqual(self.request("GET", ok.replace("t0k3n", "nope"), token=None)[0], 403)


class CopilotRun(Server):
    def test_a_run_streams_its_output_and_asks_on_the_page(self):
        seen = {}

        def fake_main(argv, answer):
            seen["argv"] = argv
            print("=== none-implement-feature · with plugin ===")
            seen["reply"] = answer("  Did Copilot use the skill `setup-verification`? [y/n/s=skip] ")
            print("  -> score 1.00")
            return 0

        with patch("shutil.which", side_effect=on_path("copilot")), patch.object(ebs.copilot_eval, "main", fake_main):
            status, _ = self.request("POST", "/api/run", {"plugin": "verification", "case": "none-implement-feature",
                                                          "host": "copilot", "arms": "with",
                                                          "model": "claude-haiku-5.5", "effort": "low"})
            self.assertEqual(status, 200)
            job = self.wait_for(lambda j: j.get("question"))
            self.assertEqual(job["question"]["text"], "Did Copilot use the skill `setup-verification`?")
            self.assertEqual(job["question"]["choices"], ["y", "n", "s"])
            self.assertEqual(self.request("POST", "/api/answer", {"reply": "maybe"})[0], 400)
            self.assertEqual(self.request("POST", "/api/answer", {"reply": "n"})[0], 200)
            job = self.wait_for(lambda j: j["status"] != "running")
        self.assertEqual(job["status"], "done")
        self.assertEqual(seen["reply"], "n")
        self.assertIn("  -> score 1.00", job["log"])
        argv = seen["argv"]
        self.assertEqual(argv[argv.index("--case") + 1], "none-implement-feature")
        self.assertEqual(argv[argv.index("--arms") + 1], "with")
        self.assertIn("--run", argv)
        self.assertEqual(argv[argv.index("--model") + 1], "claude-haiku-5.5")
        self.assertEqual(argv[argv.index("--reasoning-effort") + 1], "low")

    def test_one_run_at_a_time_and_stop_ends_it(self):
        def fake_main(argv, answer):
            answer("  passed? [y/n/s=skip] ")
            return 0

        body = {"plugin": "verification", "case": "none-implement-feature", "host": "copilot"}
        with patch("shutil.which", side_effect=on_path("copilot")), patch.object(ebs.copilot_eval, "main", fake_main):
            self.assertEqual(self.request("POST", "/api/run", body)[0], 200)
            self.wait_for(lambda j: j.get("question"))
            self.assertEqual(self.request("POST", "/api/run", body)[0], 409)
            self.assertEqual(self.request("POST", "/api/stop", {})[0], 200)
            job = self.wait_for(lambda j: j["status"] != "running")
        self.assertEqual(job["status"], "stopped")

    def test_a_refused_copilot_is_a_failed_run_with_the_reason(self):
        def fake_main(argv, answer):
            raise SystemExit("    | Error: model 'x' is not available")

        with patch("shutil.which", side_effect=on_path("copilot")), patch.object(ebs.copilot_eval, "main", fake_main):
            self.request("POST", "/api/run", {"plugin": "verification", "case": "none-implement-feature", "host": "copilot"})
            job = self.wait_for(lambda j: j["status"] != "running")
        self.assertEqual(job["status"], "failed")
        self.assertIn("is not available", "\n".join(job["log"]))


class ClaudeRun(Server):
    def test_the_claude_command_is_built_from_the_case_and_never_trusts_for_you(self):
        trigger = ebs.claude_command({"plugin": "verification", "case": "none-implement-feature", "arms": "with",
                                      "model": "", "max_cost_usd": 2.0}, "trigger", "claude")
        behavior = ebs.claude_command({"plugin": "verification", "case": "verify-change-follows-shared-code",
                                       "arms": "both", "model": "claude-sonnet-5-5", "max_cost_usd": 5.0},
                                      "behavior", "claude")
        for cmd in (trigger, behavior):
            self.assertNotIn("--trust-plugin", cmd)
            self.assertIn("--no-publish", cmd)
            self.assertIn("--scaffold", cmd)
        self.assertEqual(trigger[trigger.index("--ablation") + 1], "none")
        self.assertNotIn("--allow-tools", trigger)
        self.assertNotIn("--ablation", behavior)
        self.assertEqual(behavior[behavior.index("--allow-tools") + 1:behavior.index("--allow-tools") + 4],
                         ["Bash", "Write", "Edit"])
        self.assertEqual(behavior[behavior.index("--model") + 1], "claude-sonnet-5-5")

    def test_a_claude_run_streams_and_reports_a_failure(self):
        class FakeProc:
            def __init__(self, *a, **k):
                self.stdout = io.StringIO("Plugin under test: \"verification\"\nNot logged in\n")
                self.code = 1

            def wait(self):
                return self.code

            def poll(self):
                return self.code

            def terminate(self):
                pass

        with patch("shutil.which", side_effect=on_path("claude")), patch("subprocess.Popen", FakeProc):
            self.request("POST", "/api/run", {"plugin": "verification", "case": "none-implement-feature", "host": "claude"})
            job = self.wait_for(lambda j: j["status"] != "running")
        self.assertEqual(job["status"], "failed")
        log = "\n".join(job["log"])
        self.assertIn("Not logged in", log)
        self.assertIn("never passes --trust-plugin", log)


class StaticPage(unittest.TestCase):
    def test_the_static_board_has_no_run_controls(self):
        import build_eval_board as board
        page = board.board([], {})
        self.assertIn("const SERVER = null;", page)


if __name__ == "__main__":
    unittest.main(verbosity=1)
