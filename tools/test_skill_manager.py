#!/usr/bin/env python3
"""tools/skill_manager.py must run only real cases, only for its own page, and ask the grading on the page.

The server starts commands on the user's machine from a browser, so the tests pin what a request
can and cannot do: no token or another Host is refused, unknown cases and odd options are refused,
one run at a time, `--trust-plugin` never appears. They also drive a whole run through the API with
the runners replaced, so nothing is billed and no agent runs.

    python3 tools/test_skill_manager.py
"""

import http.client
import io
import json
import os
import re
import shutil
import sys
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skill_manager as ebs  # noqa: E402

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
        ok = "/transcript?token=t0k3n&raw=1&file=plugins/verification/evals/results/copilot-2099-01-06T00-00-00Z/c-with.md"
        status, body = self.request("GET", ok, token=None)
        self.assertEqual((status, body), (200, "# transcript\n"))
        for bad in ("AGENTS.md", "fixtures/EXPECTED.md", "plugins/verification/evals/results/../../../AGENTS.md",
                    "plugins/verification/evals/trigger/none-implement-feature/prompt.md"):
            status, _ = self.request("GET", "/transcript?token=t0k3n&file=" + bad, token=None)
            self.assertEqual(status, 404, bad)
        self.assertEqual(self.request("GET", ok.replace("t0k3n", "nope"), token=None)[0], 403)



SAMPLE_SHARE = """# Copilot CLI Session

> [!NOTE]
> - **Session ID:** `99931c43`
> - **Duration:** 35s

---

<sub>6s</sub>

### User

Write an architecture overview of this codebase.

---

<sub>9s</sub>

### `powershell`

**List repository files**

<details>
<summary>Arguments</summary>

```json
{
  "command": "Get-ChildItem -Recurse -File -Depth 3 | Select-Object -First 3"
}
```

</details>

<details>
<summary>14 lines</summary>

```
C:\\\\ws\\\\pyproject.toml
<script>alert(1)</script>
```

</details>

### Copilot

Done. See `docs/architecture.md`.
"""


class TranscriptPage(unittest.TestCase):
    def test_the_share_markdown_renders_roles_tools_and_folded_sections(self):
        page = ebs.render_transcript(SAMPLE_SHARE, "plugins/x/evals/results/r/c-with.md")
        self.assertIn('<h3 class="role user">User</h3>', page)
        self.assertIn('<h3 class="role copilot">Copilot</h3>', page)
        self.assertIn('<h3 class="tool"><span>tool</span> powershell</h3>', page)
        self.assertIn("<details>", page)
        self.assertIn("<summary>Arguments</summary>", page)
        self.assertIn('<div class="time">9s</div>', page)
        self.assertIn("<code>docs/architecture.md</code>", page)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page, "code output stays text")

    def test_nothing_the_agent_wrote_becomes_markup(self):
        hostile = "\n".join([
            "<script>alert(1)</script>",
            "### <img src=x onerror=alert(1)>",
            "<summary><img src=x onerror=alert(2)></summary>",
            "<details open ontoggle=alert(3)>",
            "<sub><svg onload=alert(4)></sub>",
            "> <iframe src=//evil.example></iframe>",
            "- <a href=javascript:alert(5)>x</a>",
            "**<b onclick=alert(6)>bold</b>**",
            "`<x onmouseover=alert(7)>`",
        ])
        page = ebs.render_transcript(hostile, "t")
        body = page.split("<main>", 1)[1].rsplit("</main>", 1)[0]
        allowed = {"p", "br", "b", "code", "pre", "h1", "h2", "h3", "h4", "details", "summary", "div", "hr",
                   "blockquote", "ul", "li", "span"}
        tags = re.findall(r"<(/?)([A-Za-z0-9]+)([^>]*)>", body)
        self.assertTrue(tags)
        for closing, name, attrs in tags:
            self.assertIn(name.lower(), allowed, "a tag the agent wrote became markup: <%s%s>" % (name, attrs))
            self.assertRegex(attrs, r'^(\s+class="[a-z ]+")?$', "attributes on <%s>: %r" % (name, attrs))


class TranscriptServe(Server):
    def test_markdown_is_served_as_a_page_without_scripts_and_raw_on_request(self):
        folder = os.path.join(ebs.REPO, "plugins", "verification", "evals", "results", "copilot-2099-01-07T00-00-00Z")
        os.makedirs(folder)
        self.addCleanup(shutil.rmtree, folder, ignore_errors=True)
        with open(os.path.join(folder, "c-with.md"), "w") as fh:
            fh.write(SAMPLE_SHARE)
        path = "/transcript?token=t0k3n&file=plugins/verification/evals/results/copilot-2099-01-07T00-00-00Z/c-with.md"
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.request("GET", path, headers={"Host": "127.0.0.1:%d" % self.port})
        res = conn.getresponse()
        body = res.read().decode("utf-8")
        conn.close()
        self.assertEqual(res.status, 200)
        self.assertTrue(res.getheader("Content-Type").startswith("text/html"))
        self.assertIn("default-src 'none'", res.getheader("Content-Security-Policy"))
        self.assertIn('<h3 class="tool"><span>tool</span> powershell</h3>', body)
        status, raw = self.request("GET", path + "&raw=1", token=None)
        self.assertEqual(status, 200)
        self.assertTrue(raw.startswith("# Copilot CLI Session"))


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
            qid = job["question"]["id"]
            self.assertEqual(self.request("POST", "/api/answer", {"id": qid, "reply": "maybe"})[0], 400)
            self.assertEqual(self.request("POST", "/api/answer", {"id": qid, "reply": "n"})[0], 200)
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
        trigger = ebs.claude_command({"plugin": "verification", "arms": "with", "model": "", "max_cost_usd": 2.0},
                                     "none-implement-feature", "trigger", "claude")
        behavior = ebs.claude_command({"plugin": "verification", "arms": "both", "model": "claude-sonnet-5-5",
                                       "max_cost_usd": 5.0}, "verify-change-follows-shared-code", "behavior", "claude")
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

        with patch("shutil.which", side_effect=on_path("claude")), patch.object(ebs, "spawn", FakeProc):
            self.request("POST", "/api/run", {"plugin": "verification", "case": "none-implement-feature", "host": "claude"})
            job = self.wait_for(lambda j: j["status"] != "running")
        self.assertEqual(job["status"], "failed")
        log = "\n".join(job["log"])
        self.assertIn("Not logged in", log)
        self.assertIn("never passes --trust-plugin", log)


class SkillRuns(Server):
    def test_all_cases_of_a_skill_run_in_turn_and_check_copilot_once(self):
        calls = []

        def fake_main(argv, answer):
            calls.append(argv)
            return 0

        cases = ["verify-change-pr-vs-issue", "verify-change-working-tree"]
        with patch("shutil.which", side_effect=on_path("copilot")), patch.object(ebs.copilot_eval, "main", fake_main):
            status, job = self.request("POST", "/api/run", {"plugin": "verification", "cases": cases,
                                                            "host": "copilot", "label": "verify-change"})
            self.assertEqual(status, 200)
            self.assertEqual(job["title"], "verify-change: 2 cases")
            job = self.wait_for(lambda j: j["status"] != "running")
        self.assertEqual(job["status"], "done")
        self.assertEqual([a[a.index("--case") + 1] for a in calls], cases)
        self.assertNotIn("--no-check", calls[0])
        self.assertIn("--no-check", calls[1])

    def test_a_list_with_an_unknown_case_is_refused(self):
        with patch("shutil.which", side_effect=on_path("copilot")):
            status, data = self.request("POST", "/api/run", {"plugin": "verification", "host": "copilot",
                                                             "cases": ["verify-change-pr-vs-issue", "rm -rf"]})
        self.assertEqual(status, 400)


class Answers(Server):
    def test_an_answer_counts_once_and_only_for_the_question_shown(self):
        seen = []

        def fake_main(argv, answer):
            seen.append(answer("  Did Copilot use the skill `a`? [y/n/s=skip] "))
            seen.append(answer("  Did Copilot use the skill `b`? [y/n/s=skip] "))
            return 0

        with patch("shutil.which", side_effect=on_path("copilot")), patch.object(ebs.copilot_eval, "main", fake_main):
            self.request("POST", "/api/run", {"plugin": "verification", "case": "none-implement-feature", "host": "copilot"})
            first = self.wait_for(lambda j: j.get("question"))["question"]
            self.assertEqual(self.request("POST", "/api/answer", {"id": first["id"], "reply": "n"})[0], 200)
            # A double click: the same question again is refused, never applied to the next one.
            self.assertEqual(self.request("POST", "/api/answer", {"id": first["id"], "reply": "y"})[0], 409)
            second = self.wait_for(lambda j: j.get("question") and j["question"]["id"] != first["id"])["question"]
            self.assertIn("`b`", second["text"])
            self.assertEqual(self.request("POST", "/api/answer", {"id": 999, "reply": "y"})[0], 409)
            self.assertEqual(self.request("POST", "/api/answer", {"id": second["id"], "reply": "s"})[0], 200)
            self.wait_for(lambda j: j["status"] != "running")
        self.assertEqual(seen, ["n", "s"])

    def test_an_unexpected_error_ends_the_job_instead_of_blocking_the_next(self):
        def fake_main(argv, answer):
            raise FileExistsError("results/copilot-2099")

        body = {"plugin": "verification", "case": "none-implement-feature", "host": "copilot"}
        with patch("shutil.which", side_effect=on_path("copilot")), patch.object(ebs.copilot_eval, "main", fake_main):
            self.request("POST", "/api/run", body)
            job = self.wait_for(lambda j: j["status"] != "running")
            self.assertEqual(job["status"], "failed")
            self.assertIn("FileExistsError", "\n".join(job["log"]))
            self.assertEqual(self.request("POST", "/api/run", body)[0], 200, "the next job can start")


class Install(Server):
    def test_commands_are_built_for_this_marketplace_only(self):
        with patch("shutil.which", side_effect=on_path("copilot", "claude")):
            self.assertEqual(ebs.plugin_command("copilot", "install", "testing")[1:],
                             ["plugin", "install", "testing@eurus-labs"])
            self.assertEqual(ebs.plugin_command("claude", "uninstall", "docs")[1:],
                             ["plugin", "uninstall", "docs@eurus-labs"])
            self.assertEqual(ebs.plugin_command("claude", "marketplace-add", source="checkout")[-1], ebs.REPO)
            self.assertEqual(ebs.plugin_command("copilot", "marketplace-add", source="github")[-1], "eurus-labs/Skills")
            self.assertEqual(ebs.plugin_command("copilot", "marketplace-update")[1:],
                             ["plugin", "marketplace", "update", "eurus-labs"])

    def test_odd_requests_are_refused(self):
        with patch("shutil.which", side_effect=on_path("copilot", "claude")):
            for body in ({"host": "copilot", "action": "install", "plugin": "not-a-plugin"},
                         {"host": "copilot", "action": "rm", "plugin": "testing"},
                         {"host": "zsh", "action": "install", "plugin": "testing"},
                         {"host": "claude", "action": "marketplace-add", "source": "https://evil.example/x"}):
                self.assertEqual(self.request("POST", "/api/install", body)[0], 400, body)

    def test_an_install_job_runs_each_plugin_and_streams_output(self):
        started = []

        class FakeProc:
            def __init__(self, command, **kwargs):
                started.append(command)
                self.stdout = io.StringIO("Plugin \"%s\" installed successfully.\n" % command[-1])

            def wait(self):
                return 0

            def poll(self):
                return 0

            def terminate(self):
                pass

        with patch("shutil.which", side_effect=on_path("copilot")), patch.object(ebs, "spawn", FakeProc):
            status, _ = self.request("POST", "/api/install", {"host": "copilot", "action": "install",
                                                              "plugins": ["testing", "docs"]})
            self.assertEqual(status, 200)
            job = self.wait_for(lambda j: j["status"] != "running")
        self.assertEqual(job["status"], "done")
        self.assertEqual([c[-1] for c in started], ["testing@eurus-labs", "docs@eurus-labs"])
        self.assertIn('Plugin "docs@eurus-labs" installed successfully.', job["log"])

    def test_installed_reads_both_hosts_listings(self):
        listings = {
            ("copilot", "list"): ([{"name": "testing", "marketplace": "eurus-labs", "version": "0.3.5", "enabled": True},
                                  {"name": "other", "marketplace": "awesome-copilot", "version": "1", "enabled": True}], None),
            ("copilot", "marketplace"): ([{"name": "eurus-labs", "source": "GitHub: eurus-labs/Skills"}], None),
            ("claude", "list"): ([{"id": "docs@eurus-labs", "version": "1.3.6", "enabled": True}], None),
            ("claude", "marketplace"): ([{"name": "eurus-labs", "source": "directory", "path": "/x"}], None),
        }

        def fake(command, timeout=60):
            host = os.path.basename(command[0])
            return listings[(host, "marketplace" if "marketplace" in command else "list")]

        with patch("shutil.which", side_effect=on_path("copilot", "claude")), patch.object(ebs, "list_json", fake):
            found = ebs.installed()
        self.assertEqual(found["copilot"]["plugins"], {"testing": {"version": "0.3.5", "enabled": True}})
        self.assertEqual(found["copilot"]["marketplace"], "GitHub: eurus-labs/Skills")
        self.assertEqual(found["claude"]["plugins"], {"docs": {"version": "1.3.6", "enabled": True}})
        self.assertEqual(found["claude"]["marketplace"], "directory /x")


class Choices(unittest.TestCase):
    def test_choices_parse_and_a_hostile_prompt_cannot_stall_the_parser(self):
        self.assertEqual(ebs.CHOICES.search("  passed? [y/n/s=skip] ").group(1), "y/n/s=skip")
        hostile = "[a/a=" + "/a=" * 20000 + "x"
        started = time.time()
        self.assertIsNone(ebs.CHOICES.search(hostile))
        self.assertLess(time.time() - started, 1.0)


class StaticPage(unittest.TestCase):
    def test_the_static_board_has_no_run_controls(self):
        import build_eval_board as board
        page = board.board([], {})
        self.assertIn("const SERVER = null;", page)


if __name__ == "__main__":
    unittest.main(verbosity=1)
