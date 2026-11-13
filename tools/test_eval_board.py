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
            names = {s for s, _ in plugin["skills"]}
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

    def test_plugins_without_evals_are_listed_with_their_skills(self):
        self.assertEqual(self.plugins["code-review"]["cases"], [])
        self.assertIn("review-code", [s for s, _ in self.plugins["code-review"]["skills"]])


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
        self.assertIn("const r = h[0];", page, "the badge shows the newest run, trusted or not")
        self.assertNotIn("scorePill(c.name)", page, "results are keyed by plugin and case, never case alone")
        self.assertIn('data-lang="en"', page)
        self.assertIn('data-lang="vi"', page)
        self.assertNotIn("__DATA__", page)
        self.assertNotRegex(page, r"https?://(?!www\.w3\.org)")


if __name__ == "__main__":
    unittest.main(verbosity=1)
