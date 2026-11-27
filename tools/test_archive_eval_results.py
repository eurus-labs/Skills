#!/usr/bin/env python3
"""tools/archive_eval_results.py must keep a run's two files with local paths scrubbed and secrets refused.

The tests build a small repository in a temporary folder, archive fixture results into it, and check what is
written and what is refused. The last class runs `--check` on this repository.

    python3 tools/test_archive_eval_results.py
"""

import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import archive_eval_results as ar  # noqa: E402

def slurp(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


STAMP = "2026-11-20T03-09-33-479Z"


def sample(repo, **extra):
    """A result that holds every kind of absolute path the plan names."""
    doc = {
        "schemaVersion": 1,
        "suite": {"root": "/root/x", "plugins": [{"name": "docs", "path": repo + "/plugins/docs"}]},
        "cases": [{
            "name": "c",
            "arms": {"with": [{
                "tracePath": "/tmp/claude-eval-1/out/trace.jsonl",
                "reply": "wrote /home/alice/y and /Users/bob/z and C:\\Users\\carol\\w, see /tmp/claude-eval-1/home/cwd.",
                "ok": "plugins/docs/skills/x/SKILL.md and docs/tmp/notes stay as they are",
                "inside": repo + "/plugins/docs/skills/x.py",
            }]},
        }],
    }
    doc.update(extra)
    return doc


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.repo = os.path.join(self.tmp, "repo")
        for plugin in ("docs", "reasoning", "_template"):
            os.makedirs(os.path.join(self.repo, "plugins", plugin))
        self.src = os.path.join(self.tmp, "bundle")

    def make_run(self, plugin="docs", stamp=STAMP, doc=None, html="<p>report</p>\n", raw=None, in_bundle=True):
        """Write a result folder; returns the folder. The plugin is in the path, as claude plugin eval writes it."""
        base = os.path.join(self.src, "plugins", plugin, "evals", "results") if in_bundle else os.path.join(self.tmp, "x")
        folder = os.path.join(base, stamp)
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "aggregate-result.json"), "w", encoding="utf-8") as fh:
            fh.write(raw if raw is not None else json.dumps(doc if doc is not None else sample(self.repo), indent=2) + "\n")
        if html is not None:
            with open(os.path.join(folder, "report.html"), "w", encoding="utf-8") as fh:
                fh.write(html)
        with open(os.path.join(folder, "case-with.jsonl"), "w") as fh:
            fh.write('{"transcript": true}\n')
        return folder

    def run_tool(self, *sources, replace=False, email=None):
        lines = []
        code = ar.archive(list(sources), self.repo, replace, email, lines.append)
        return code, "\n".join(lines)

    def archived(self, plugin="docs", stamp=STAMP, name="aggregate-result.json"):
        return os.path.join(self.repo, "plugins", plugin, "evals", "archive", stamp, name)

    def all_files(self):
        return sorted(os.path.relpath(os.path.join(d, f), self.repo)
                      for d, _, fs in os.walk(self.repo) for f in fs)


class Scrubbing(Base):
    def test_every_path_is_replaced_and_the_json_stays_valid_and_indented(self):
        self.make_run(html="<pre>/root/x\nC:\\Users\\carol\\w\n%s/plugins/docs/a.py</pre>\n" % self.repo)
        code, out = self.run_tool(self.src)
        self.assertEqual(code, 0, out)
        raw = slurp(self.archived())
        doc = json.loads(raw)
        run = doc["cases"][0]["arms"]["with"][0]
        self.assertIsNone(run["tracePath"], "the trace is not archived")
        self.assertEqual(run["reply"], "wrote <local> and <local> and <local>, see <local>.")
        self.assertEqual(run["inside"], "<local>/plugins/docs/skills/x.py", "a repository path keeps its relative part")
        self.assertEqual(doc["suite"]["root"], "<local>")
        self.assertEqual(doc["suite"]["plugins"][0]["path"], "<local>/plugins/docs")
        self.assertIn("docs/tmp/notes", run["ok"], "a relative path is not touched")
        self.assertTrue(raw.startswith('{\n  "schemaVersion"'), "same two-space indentation")
        self.assertTrue(raw.endswith("}\n"))
        for needle in ("/root/", "/home/alice", "/Users/bob", "carol", "/tmp/claude-eval", self.repo):
            self.assertNotIn(needle, raw)
        html = slurp(self.archived(name="report.html"))
        self.assertEqual(html, "<pre><local>\n<local>\n<local>/plugins/docs/a.py</pre>\n")

    def test_a_result_with_nothing_to_scrub_is_written_unchanged(self):
        doc = {"schemaVersion": 1, "cases": [{"name": "c", "score": 0.5, "text": "plain"}]}
        original = json.dumps(doc, indent=2) + "\n"
        self.make_run(raw=original)
        self.assertEqual(self.run_tool(self.src)[0], 0)
        self.assertEqual(slurp(self.archived()), original)

    def test_only_the_two_files_are_written_and_only_under_archive(self):
        self.make_run()
        before = self.all_files()
        self.assertEqual(self.run_tool(self.src)[0], 0)
        new = [f for f in self.all_files() if f not in before]
        stem = os.path.join("plugins", "docs", "evals", "archive", STAMP)
        self.assertEqual(sorted(new), [os.path.join(stem, "aggregate-result.json"), os.path.join(stem, "report.html")],
                         "the transcript is not copied")

    def test_trailing_punctuation_and_odd_shapes(self):
        text, count = ar.scrub_text("see /tmp/a/b. Then (/root/x), `/home/u/p`, file:///var/folders/ab/c: "
                                    "and C:/Users/dan/p and /rooted and /homework/x and a.b/root/x", self.repo)
        self.assertEqual(text, "see <local>. Then (<local>), `<local>`, file://<local>: and <local> and /rooted "
                               "and /homework/x and a.b/root/x")
        self.assertEqual(count, 5)

    def test_the_html_is_replaced_as_text(self):
        text, _ = ar.scrub_text('<script>{"p":"C:\\\\Users\\\\erin\\\\x"}</script>', self.repo)
        self.assertEqual(text, '<script>{"p":"<local>"}</script>')


class Sources(Base):
    def test_a_results_folder_a_json_file_and_a_bundle_all_work(self):
        folder = self.make_run()
        for source in (folder, os.path.join(folder, "aggregate-result.json"), self.src,
                       os.path.join(self.src, "plugins", "docs", "evals", "results")):
            shutil.rmtree(os.path.join(self.repo, "plugins", "docs", "evals"), ignore_errors=True)
            code, out = self.run_tool(source)
            self.assertEqual(code, 0, (source, out))
            self.assertTrue(os.path.isfile(self.archived()), source)

    def test_a_source_without_a_result_is_a_usage_error(self):
        empty = os.path.join(self.tmp, "empty")
        os.makedirs(empty)
        self.assertEqual(self.run_tool(empty)[0], 2)

    def test_a_moved_case_keeps_the_plugin_it_ran_under(self):
        doc = sample(self.repo, suite={"plugins": [{"name": "planning"}]})
        self.make_run(plugin="reasoning", doc=doc)
        self.assertEqual(self.run_tool(self.src)[0], 0)
        self.assertTrue(os.path.isfile(self.archived("reasoning")))

    def test_the_plugin_comes_from_the_suite_when_the_path_names_none(self):
        folder = self.make_run(in_bundle=False, doc=sample(self.repo, suite={"plugins": [{"name": "reasoning"}]}))
        self.assertEqual(self.run_tool(folder)[0], 0)
        self.assertTrue(os.path.isfile(self.archived("reasoning")))

    def test_the_html_is_optional(self):
        self.make_run(html=None)
        self.assertEqual(self.run_tool(self.src)[0], 0)
        self.assertTrue(os.path.isfile(self.archived()))
        self.assertFalse(os.path.exists(self.archived(name="report.html")))


class Refusals(Base):
    def assert_refused(self, code, out, *words, forbidden=()):
        self.assertEqual(code, 1, out)
        for word in words:
            self.assertIn(word, out)
        for word in forbidden:
            self.assertNotIn(word, out)
        self.assertFalse(os.path.exists(os.path.join(self.repo, "plugins", "docs", "evals", "archive")),
                         "nothing is written")

    def test_each_secret_pattern_is_refused_by_name_and_never_printed(self):
        secrets = {
            "sk-ant-": "sk-ant-api03-ZZZZsecretvalue",
            "ghp_": "ghp_ZZZZsecretvalue1234",
            "gho_": "gho_ZZZZsecretvalue1234",
            "github_pat_": "github_pat_ZZZZsecretvalue1234",
            "AKIA access key id": "AKIAZZZZZZZZZZZZZZZZ",
            "Authorization: Bearer token": "Authorization: Bearer ZZZZsecrettoken1234",
        }
        for name, value in secrets.items():
            for where in ("json", "html"):
                shutil.rmtree(self.src, ignore_errors=True)
                doc = sample(self.repo)
                doc["cases"][0]["note"] = "x " + value if where == "json" else "clean"
                self.make_run(doc=doc, html="<p>%s</p>" % value if where == "html" else "<p>clean</p>")
                code, out = self.run_tool(self.src)
                self.assert_refused(code, out, name, "aggregate-result.json" if where == "json" else "report.html",
                                    forbidden=("ZZZZ",))

    def test_a_secret_hidden_by_escaping_is_refused(self):
        def doc_with(value):
            doc = sample(self.repo)
            doc["cases"][0]["note"] = value
            return json.dumps(doc, indent=2) + "\n"

        cases = [
            ("Authorization: Bearer token", doc_with("Authorization:\tBearer\tabcdefghijklmnopqrstuvwxyz0123"), None, "tab"),
            ("sk-ant-", doc_with("x").replace('"x"', '"sk\\u002dant-ZZZZsecretvalue"'), None, "unicode escape"),
            ("ghp_", None, "<p>ghp&#95;ZZZZsecretvalue1234</p>", "html entity"),
            ("sk-ant-", None, "<p>sk&#x2d;ant-ZZZZsecretvalue</p>", "html hex entity"),
        ]
        for name, raw, html, _why in cases:
            shutil.rmtree(self.src, ignore_errors=True)
            self.make_run(raw=raw, html=html if html is not None else "<p>clean</p>")
            code, out = self.run_tool(self.src)
            self.assert_refused(code, out, name, forbidden=("ZZZZ", "abcdefghij"))

    def test_a_private_key_block_is_refused(self):
        key = "-----BEGIN RSA PRIVATE KEY-----\nMIIZZZZkeybody\n-----END RSA PRIVATE KEY-----"
        doc = sample(self.repo)
        doc["cases"][0]["note"] = key
        self.make_run(doc=doc)
        code, out = self.run_tool(self.src)
        self.assert_refused(code, out, "private key block", forbidden=("ZZZZ", "MIIZ"))

    def test_the_git_user_email_is_refused_without_printing_it(self):
        doc = sample(self.repo)
        doc["cases"][0]["note"] = "committed by Dev.Person@example.test"
        self.make_run(doc=doc)
        code, out = self.run_tool(self.src, email="dev.person@example.test")
        self.assert_refused(code, out, "git config user.email", forbidden=("example.test", "person"))
        self.assertEqual(self.run_tool(self.src, email=None)[0], 0, "no email set, no refusal")

    def test_a_bearer_placeholder_is_not_a_token(self):
        doc = sample(self.repo)
        doc["cases"][0]["note"] = "send Authorization: Bearer <token>"
        self.make_run(doc=doc)
        self.assertEqual(self.run_tool(self.src)[0], 0)

    def test_a_file_over_5_mb_is_refused(self):
        big = sample(self.repo)
        big["cases"][0]["note"] = "x" * (ar.MAX_BYTES + 10)
        self.make_run(doc=big)
        code, out = self.run_tool(self.src)
        self.assert_refused(code, out, "over 5 MB", "aggregate-result.json")
        shutil.rmtree(self.src)
        self.make_run(html="y" * (ar.MAX_BYTES + 10))
        code, out = self.run_tool(self.src)
        self.assert_refused(code, out, "over 5 MB", "report.html")

    def test_the_same_timestamp_with_other_content_needs_replace(self):
        self.make_run()
        self.assertEqual(self.run_tool(self.src)[0], 0)
        code, out = self.run_tool(self.src)
        self.assertEqual(code, 0, "the same content is skipped")
        self.assertIn("skipped", out)
        changed = sample(self.repo)
        changed["cases"][0]["name"] = "other"
        self.make_run(doc=changed)
        kept = slurp(self.archived())
        code, out = self.run_tool(self.src)
        self.assertEqual(code, 1, out)
        self.assertIn("--replace", out)
        self.assertEqual(slurp(self.archived()), kept, "the archived run is untouched")
        code, out = self.run_tool(self.src, replace=True)
        self.assertEqual(code, 0, out)
        self.assertIn("replaced", out)
        self.assertEqual(json.loads(slurp(self.archived()))["cases"][0]["name"], "other")

    def test_replace_removes_a_report_the_new_source_lacks(self):
        self.make_run()
        self.assertEqual(self.run_tool(self.src)[0], 0)
        self.assertTrue(os.path.exists(self.archived(name="report.html")))
        shutil.rmtree(self.src)
        changed = sample(self.repo)
        changed["cases"][0]["name"] = "other"
        self.make_run(doc=changed, html=None)
        code, out = self.run_tool(self.src)
        self.assertEqual(code, 1, "a differing run still needs --replace")
        self.assertTrue(os.path.exists(self.archived(name="report.html")))
        code, out = self.run_tool(self.src, replace=True)
        self.assertEqual(code, 0, out)
        self.assertFalse(os.path.exists(self.archived(name="report.html")), "the stale report is gone")
        self.assertIn("removed", out)
        self.assertIn("report.html", out)
        self.assertEqual(json.loads(slurp(self.archived()))["cases"][0]["name"], "other")

    def test_replace_with_both_files_keeps_both(self):
        self.make_run()
        self.run_tool(self.src)
        shutil.rmtree(self.src)
        changed = sample(self.repo)
        changed["cases"][0]["name"] = "other"
        self.make_run(doc=changed, html="<p>new report</p>")
        code, out = self.run_tool(self.src, replace=True)
        self.assertEqual(code, 0, out)
        self.assertNotIn("removed", out)
        self.assertEqual(slurp(self.archived(name="report.html")), "<p>new report</p>")

    def test_an_unknown_plugin_is_refused_with_the_reason(self):
        self.make_run(plugin="vanished")
        code, out = self.run_tool(self.src)
        self.assertEqual(code, 1, out)
        self.assertIn("unknown plugin 'vanished'", out)
        self.assertFalse(os.path.exists(os.path.join(self.repo, "plugins", "vanished")))

    def test_a_plugin_the_suite_names_but_the_repository_lacks_is_refused(self):
        folder = self.make_run(in_bundle=False, doc=sample(self.repo, suite={"plugins": [{"name": "gone"}]}))
        code, out = self.run_tool(folder)
        self.assertEqual(code, 1)
        self.assertIn("unknown plugin 'gone'", out)

    def test_the_template_and_odd_names_are_not_plugins(self):
        self.make_run(plugin="_template")
        code, out = self.run_tool(self.src)
        self.assertEqual(code, 1)
        self.assertIn("_template", out)
        shutil.rmtree(self.src)
        folder = self.make_run(in_bundle=False, doc=sample(self.repo, suite={"plugins": [{"name": "../evil"}]}))
        self.assertEqual(self.run_tool(folder)[0], 1)

    def test_one_refusal_writes_nothing_for_the_other_runs(self):
        self.make_run(stamp="2026-11-20T00-00-00Z")
        bad = sample(self.repo)
        bad["cases"][0]["note"] = "sk-ant-ZZZZ"
        self.make_run(stamp="2026-11-21T00-00-00Z", doc=bad)
        code, out = self.run_tool(self.src)
        self.assertEqual(code, 1)
        self.assertIn("2026-11-21T00-00-00Z", out)
        self.assertFalse(os.path.exists(os.path.join(self.repo, "plugins", "docs", "evals", "archive")))

    def test_invalid_json_and_a_non_result_are_refused(self):
        self.make_run(raw='{"cases": [')
        code, out = self.run_tool(self.src)
        self.assertEqual(code, 1)
        self.assertIn("not valid JSON", out)
        shutil.rmtree(self.src)
        self.make_run(raw='{"hello": 1}')
        self.assertEqual(self.run_tool(self.src)[0], 1)


class Check(Base):
    def run_check(self, email=None):
        lines = []
        with redirect_stdout(io.StringIO()):
            code = ar.check(self.repo, email, lines.append)
        return code, "\n".join(lines)

    def test_a_clean_archive_passes(self):
        self.make_run()
        self.run_tool(self.src)
        code, out = self.run_check()
        self.assertEqual(code, 0, out)
        self.assertIn("clean", out)

    def test_a_planted_path_fails_and_names_the_file(self):
        self.make_run()
        self.run_tool(self.src)
        for planted in ("/home/mallory/x", "/Users/mallory/x", "/root/x", "/tmp/x", "C:\\\\Users\\\\mallory\\\\x"):
            path = self.archived()
            with open(path, encoding="utf-8") as fh:
                original = fh.read()
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(original.replace('"schemaVersion": 1', '"schemaVersion": 1, "leak": "%s"' % planted))
            code, out = self.run_check()
            self.assertEqual(code, 1, planted)
            self.assertIn("plugins/docs/evals/archive/%s/aggregate-result.json: absolute local path" % STAMP, out)
            self.assertNotIn("mallory", out)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(original)
        self.assertEqual(self.run_check()[0], 0)

    def test_a_planted_escaped_secret_fails_and_is_named_never_shown(self):
        self.make_run()
        self.run_tool(self.src)
        for planted in ('"sk\\u002dant-ZZZZsecretvalue"', '"Authorization:\\tBearer\\tabcdefghijklmnop0123"'):
            path = self.archived()
            original = slurp(path)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(original.replace('"schemaVersion": 1', '"schemaVersion": 1, "leak": ' + planted))
            code, out = self.run_check()
            self.assertEqual(code, 1, planted)
            self.assertIn("aggregate-result.json: secret pattern", out)
            self.assertNotIn("ZZZZ", out)
            self.assertNotIn("abcdefghij", out)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(original)
        with open(self.archived(name="report.html"), "a", encoding="utf-8") as fh:
            fh.write("<p>ghp&#95;ZZZZsecretvalue1234 and &#x2F;root&#x2F;x</p>")
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("report.html: secret pattern 'ghp_'", out)
        self.assertIn("report.html: absolute local path", out)
        self.assertNotIn("ZZZZ", out)

    def test_a_planted_path_in_the_html_and_the_repository_path_fail(self):
        self.make_run()
        self.run_tool(self.src)
        with open(self.archived(name="report.html"), "a", encoding="utf-8") as fh:
            fh.write("<p>%s/elsewhere</p>" % self.repo)
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("report.html: absolute local path", out)

    def test_a_planted_secret_an_oversized_file_and_broken_json_fail(self):
        self.make_run()
        self.run_tool(self.src)
        with open(self.archived(name="report.html"), "a", encoding="utf-8") as fh:
            fh.write("ghp_ZZZZsecretvalue1234")
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("report.html: secret pattern 'ghp_'", out)
        self.assertNotIn("ZZZZ", out)
        with open(self.archived(name="report.html"), "w", encoding="utf-8") as fh:
            fh.write("x" * (ar.MAX_BYTES + 1))
        self.assertIn("over 5 MB", self.run_check()[1])
        with open(self.archived(name="report.html"), "w", encoding="utf-8") as fh:
            fh.write("ok")
        with open(self.archived(), "w", encoding="utf-8") as fh:
            fh.write("{broken")
        self.assertIn("not valid JSON", self.run_check()[1])

    def test_check_writes_nothing(self):
        self.make_run()
        self.run_tool(self.src)
        before = self.all_files()
        self.run_check()
        self.assertEqual(self.all_files(), before)


class Repository(unittest.TestCase):
    def test_the_archive_in_this_repository_is_clean(self):
        lines = []
        code = ar.check(ar.REPO, None, lines.append)
        self.assertEqual(code, 0, "\n".join(lines))

    def test_main_check_takes_no_source(self):
        with redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as raised:
            with mock.patch("sys.stderr", io.StringIO()):
                ar.main(["--check", "somewhere"])
        self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
