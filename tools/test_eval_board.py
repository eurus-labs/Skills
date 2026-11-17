#!/usr/bin/env python3
"""The eval board must tie every case to the skills it tests, and never trust a score it should not.

tools/build_eval_board.py reads the eval cases and the git-ignored `aggregate-result.json`
files of local runs. The first real run of this repository's evals stopped on a failed sign-in
and still printed a score of 1.00 for a case whose agent never started; a board that showed that
as a pass would mislead more than no board.

    python3 tools/test_eval_board.py
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_eval_board as board  # noqa: E402


def result(cases, partial=False, reason=None):
    return {"schemaVersion": 1, "partial": partial, "partialReason": reason, "cases": cases}


def case(name, score, delta=None, errors=(), skipped=False):
    runs = [{"error": e, "skippedPaidGraders": skipped} for e in errors] or [{"error": None, "skippedPaidGraders": skipped}]
    agg = {"score": score}
    if delta is not None:
        agg["delta"] = delta
    return {"name": name, "aggregates": agg, "arms": {"with": runs}}


class Catalog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plugins = {p["name"]: p for p in board.catalog()}

    def test_every_case_belongs_to_a_skill_of_its_plugin(self):
        for plugin in self.plugins.values():
            names = {s[0] for s in plugin["skills"]}
            for c in plugin["cases"]:
                self.assertTrue(c["skills"], c["name"])
                self.assertLessEqual(set(c["skills"]), names, c["name"])

    def test_a_should_fire_case_names_its_skill(self):
        fires = [c for c in self.plugins["verification"]["cases"] if c["name"] == "verify-change-pr-vs-issue"][0]
        self.assertEqual(fires["fires"], ["verify-change"])
        self.assertIn("setup-verification", fires["skills"], "its quiet grader ties it to the sibling skill too")

    def test_a_none_case_keeps_every_named_skill_quiet(self):
        none = [c for c in self.plugins["verification"]["cases"] if c["name"] == "none-implement-feature"][0]
        self.assertEqual(none["fires"], [])
        self.assertEqual(sorted(none["skills"]), ["setup-verification", "verify-change"])

    def test_behavior_cases_are_tied_to_the_skill_they_run(self):
        behavior = [c for c in self.plugins["verification"]["cases"] if c["kind"] == "behavior"]
        self.assertTrue(behavior)
        for c in behavior:
            self.assertEqual(len(c["fires"]), 1, c["name"])

    def test_a_tool_grader_keeps_the_input_it_restricts(self):
        case_ = [c for c in self.plugins["verification"]["cases"]
                 if c["name"] == "verify-change-runs-skipped-tests"][0]
        tree = [g for g in case_["graders"] if g["name"] == "tree-preserved"][0]
        self.assertEqual(tree["tool"], "Bash")
        self.assertIn("stash", tree["match"])

    def test_plugins_carry_their_version_and_skills_their_last_change(self):
        plugin = self.plugins["verification"]
        self.assertRegex(plugin["version"], r"^\d+\.\d+\.\d+$")
        for name, _, changed in plugin["skills"]:
            self.assertIsInstance(changed, int, "%s: no git time; the 'changed since last run' status needs it" % name)

    def test_a_run_time_comes_from_its_results_folder(self):
        self.assertEqual(board.stamp_time("copilot-2026-11-14T07-38-16Z"), 1794641896)
        self.assertEqual(board.stamp_time("2026-11-14T07-38-16-539Z"), 1794641896)
        self.assertIsNone(board.stamp_time("sample", None))

    def test_plugins_without_evals_are_listed_with_their_skills(self):
        self.assertEqual(self.plugins["skill-authoring"]["cases"], [])
        self.assertIn("evaluate-skill", [s[0] for s in self.plugins["skill-authoring"]["skills"]])


class Results(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def write(self, stamp, doc):
        folder = os.path.join(self.tmp.name, stamp)
        os.makedirs(folder)
        path = os.path.join(folder, "aggregate-result.json")
        with open(path, "w") as fh:
            json.dump(doc, fh)
        return path

    def test_reads_score_delta_and_orders_newest_first(self):
        old = self.write("2026-11-01T00-00-00Z", result([case("a", 0.5, 0.1)]))
        new = self.write("2026-11-02T00-00-00Z", result([case("a", 0.9, 0.4)]))
        runs = board.load_results([("p", old), ("p", new)])["p/a"]
        self.assertEqual([r["score"] for r in runs], [0.9, 0.5])
        self.assertEqual(runs[0]["delta"], 0.4)
        self.assertTrue(board.trusted(runs[0]))

    def test_the_failed_sign_in_run_is_never_trusted(self):
        # The real second run: score 1.00, the run ended "Not logged in", the suite stopped.
        path = self.write("2026-11-12T15-22-41-539Z", result(
            [case("none-implement-feature", 1.0, errors=["exit 1: Not logged in · Please run /login"])],
            partial=True, reason="auth_failed"))
        run = board.load_results([("verification", path)])["verification/none-implement-feature"][0]
        self.assertFalse(board.trusted(run))
        self.assertEqual(run["partialReason"], "auth_failed")

    def test_an_errored_run_or_skipped_judges_are_not_trusted(self):
        a = self.write("s1", result([case("x", 1.0, errors=["timed out after 300s"])]))
        b = self.write("s2", result([case("y", 1.0, skipped=True)]))
        loaded = board.load_results([("p", a), ("p", b)])
        self.assertFalse(board.trusted(loaded["p/x"][0]))
        self.assertFalse(board.trusted(loaded["p/y"][0]))

    def test_the_same_case_name_in_two_plugins_keeps_two_histories(self):
        # none-implement-feature exists in both testing and verification.
        root = os.path.join(self.tmp.name, "repo")
        paths = []
        for plugin, score in (("testing", 0.2), ("verification", 0.9)):
            folder = os.path.join(root, "plugins", plugin, "evals", "results", "2026-11-13T00-00-00Z")
            os.makedirs(folder)
            path = os.path.join(folder, "aggregate-result.json")
            with open(path, "w") as fh:
                json.dump(result([case("none-implement-feature", score)]), fh)
            paths.append(path)
        loaded = board.load_results(paths)
        self.assertEqual(loaded["testing/none-implement-feature"][0]["score"], 0.2)
        self.assertEqual(loaded["verification/none-implement-feature"][0]["score"], 0.9)

    def test_a_result_outside_results_takes_its_plugin_from_the_suite_or_is_skipped(self):
        named = self.write("named", dict(result([case("a", 1.0)]), suite={"plugins": [{"name": "docs"}]}))
        unnamed = self.write("unnamed", result([case("b", 1.0)]))
        loaded = board.load_results([named, unnamed])
        self.assertIn("docs/a", loaded)
        self.assertEqual([k for k in loaded if k.endswith("/b")], [])

    def test_each_run_carries_its_host(self):
        claude = self.write("c1", result([case("a", 0.9)]))
        copilot = self.write("p1", dict(result([case("a", 0.4)]), host="copilot"))
        runs = board.load_results([("p", claude), ("p", copilot)])["p/a"]
        self.assertEqual(sorted(r["host"] for r in runs), ["claude", "copilot"])

    def test_a_file_that_is_not_a_result_is_skipped(self):
        bad = os.path.join(self.tmp.name, "other.json")
        with open(bad, "w") as fh:
            fh.write('{"hello": 1}')
        self.assertEqual(board.load_results([bad]), {})


class Page(unittest.TestCase):
    def test_page_embeds_the_data_safely_and_has_both_languages(self):
        plugins = [{"name": "p", "skills": [["s", "Does </script> things."]],
                    "cases": [{"name": "c", "kind": "trigger", "description": "d", "prompt": "<b>",
                               "graders": [], "fires": ["s"], "quiet": [], "skills": ["s"]}]}]
        page = board.board(plugins, {})
        self.assertEqual(page.count("</script>"), 1)
        self.assertIn("const r = h[0],", page, "the badge shows the newest run, trusted or not")
        self.assertNotIn("scorePill(c.name)", page, "results are keyed by plugin and case, never case alone")
        self.assertIn('data-lang="en"', page)
        self.assertIn('data-lang="vi"', page)
        self.assertNotIn("__DATA__", page)
        self.assertNotRegex(page, r"https?://(?!www\.w3\.org)")

    def test_skills_and_their_cases_share_one_evals_tab(self):
        page = board.board([], {})
        self.assertEqual(sorted(set(__import__("re").findall(r'data-tab="([a-z]+)"', page))), ["evals", "install"])
        self.assertEqual(sorted(set(__import__("re").findall(r'data-view="([a-z]+)"', page))), ["evals", "install", "run"])
        self.assertIn("data-expand=", page, "a skill row opens to its cases")
        self.assertIn('runFormFor(keyOf(c), c.name, t("runCase"))', page, "the case panel has the case's run form")
        self.assertIn('t("runAllOf")', page, "and the skill can run all its cases")
        # A case shared by two open skills has two forms; every read must take the form that was used.
        self.assertIn('formOf(k, go.closest("form"))', page)
        self.assertNotRegex(page, r"formOf\(\w+\)", "a bare formOf(k) reads the first copy on the page")

    def test_the_redesign_keeps_its_decisions(self):
        page = board.board([], {})
        # Hosts are data: one list, embedded in the page and read by the server.
        self.assertIn('"hosts": [{"id": "copilot"', page)
        self.assertEqual([h["id"] for h in board.HOSTS], ["copilot", "claude"])
        self.assertNotIn('const HOSTS = ["', page, "the page has no host list of its own")
        # Search and the status filters.
        self.assertIn('id="q"', page)
        for f in ("all", "notrun", "noevals"):
            self.assertIn('["%s", "f' % f, page)
        # Grading buttons are tinted and carry an icon, so colour is not the only cue.
        for c, icon in (("y", "✓"), ("n", "✕"), ("s", "→")):
            self.assertIn('b("%s", "%s"' % (c, icon), page)
        # Install: one platform at a time, fixed action slots, a fix for a host that is not on PATH.
        self.assertIn('data-platform=', page)
        self.assertIn('class="btn ghost small hold"', page, "an empty second slot keeps its width")
        self.assertIn('t("fixPath")', page)
        # Graders are tagged by kind in the case panel.
        self.assertIn('tool_used: "tool", llm: "llm", regex: "regex"', page)

    def test_polling_keeps_focus_and_a_finished_job_stays_reachable(self):
        page = board.board([], {})
        # Redrawing the question card every second would drop the keyboard focus on the answer buttons.
        self.assertIn('setHTML($("runside"), card', page)
        self.assertIn('setHTML($("runhead"), `<h2>', page)
        self.assertNotIn('$("runside").innerHTML', page)
        # A job that ended before its output was opened keeps its chip and, for installs, its notice.
        self.assertIn('(j.status !== "running" && JOB.seen)', page)
        self.assertIn('(j.status === "running" || !JOB.seen)', page)


HARNESS = """
const els = {};
const mk = () => ({innerHTML:"", textContent:"", hidden:false, style:{}, dataset:{}, setAttribute(){}, addEventListener(){},
  closest(){return null}, querySelector(){return null}, querySelectorAll(){return []}});
global.document = {getElementById: id => els[id] || (els[id] = mk()), querySelectorAll: () => [], addEventListener(t, f){ if (t === "click") global.clickHandler = f; }, documentElement:{}};
global.window = {scrollTo(){}};
global.localStorage = {getItem(){return null}, setItem(){}};
global.fetch = () => new Promise(() => {});
"""
LISTING = """
;INSTALLED = {copilot:{available:true, marketplace:"x", plugins:{reasoning:{version:"0.2.2", enabled:false},
  review:{version:"0.3.0", enabled:true}, "code-review":{version:"0.2.0", enabled:true}}},
  claude:{available:true, marketplace:"x", plugins:{}}};
state.platform = "copilot"; installTab();
const pick = {"[data-install]": {dataset: {install: "uninstall", host: "copilot", allinstalled: "1"}}};
global.clickHandler({target: {closest: sel => pick[sel] || null}}).then(() => {
console.log(JSON.stringify({all: state.installing, body: els.installbody.innerHTML, confirm: commandText("copilot", "enable", ["reasoning"]),
  confirmClaude: commandText("claude", "enable", ["reasoning"]), uninstall: commandText("copilot", "uninstall", ["code-review"])}));
});
"""


class SkillsTab(unittest.TestCase):
    def test_the_tab_reads_skills_and_keeps_its_view_id(self):
        page = board.board([], {}, {"token": "t"})
        self.assertIn('tabInstall:"Skills"', page)
        self.assertEqual(page.count('tabInstall:"Skills"'), 2, "in English and in Vietnamese")
        self.assertIn('backInstall:"← Back to skills"', page)
        self.assertIn('backInstall:"← Về Skills"', page)
        self.assertIn('data-tab="install"', page)
        self.assertIn('data-view="install"', page)

    @unittest.skipUnless(shutil.which("node"), "node is needed to run the page script")
    def test_the_plugin_table_shows_enable_uninstall_all_and_stale_rows(self):
        plugins = [{"name": n, "version": "0.3.0", "skills": [["s-" + n, "g"]], "cases": []}
                   for n in ("reasoning", "review", "docs")]
        script = re.search(r"<script>(.*)</script>", board.board(plugins, {}, {"token": "t"}), re.S).group(1)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "page.js")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(HARNESS + script + LISTING)
            out = subprocess.run(["node", path], capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)
        got = json.loads(out.stdout.strip().splitlines()[-1])
        rows = {m.group(1): m.group(2) for m in re.finditer(r'<tr><td><b class="mono">([^<]+)</b>(.*?)</tr>', got["body"], re.S)}
        self.assertEqual(sorted(rows), ["code-review", "docs", "reasoning", "review"])
        def buttons(row):
            return re.findall(r'data-install="([a-z-]+)"[^>]*data-iplugin="([^"]+)"', rows[row])
        self.assertEqual(buttons("reasoning"), [("enable", "reasoning"), ("uninstall", "reasoning")])
        self.assertEqual(buttons("review"), [("update", "review"), ("uninstall", "review")])
        self.assertEqual(buttons("docs"), [("install", "docs")])
        self.assertEqual(buttons("code-review"), [("uninstall", "code-review")], "a stale plugin offers Uninstall only")
        self.assertIn("no longer in this marketplace", rows["code-review"])
        head = re.search(r'<th><div class="slots head">(.*?)</div></th>', got["body"], re.S).group(1)
        self.assertEqual(re.findall(r'data-install="([a-z-]+)"([^>]*)data-(all|allinstalled)="1"', head)[2][::2],
                         ("uninstall", "allinstalled"))
        self.assertNotIn(" disabled>Uninstall all", head)
        self.assertEqual(got["confirm"], "copilot plugin enable reasoning")
        self.assertEqual(got["confirmClaude"], "claude plugin enable reasoning@eurus-labs")
        self.assertEqual(got["uninstall"], "copilot plugin uninstall code-review@eurus-labs")
        self.assertEqual(got["all"]["plugins"], ["reasoning", "review", "code-review"],
                         "Uninstall all names exactly what the host has installed, stale ones included")
        self.assertEqual(got["all"]["action"], "uninstall")


if __name__ == "__main__":
    unittest.main(verbosity=1)
