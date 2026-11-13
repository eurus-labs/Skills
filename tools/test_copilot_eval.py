#!/usr/bin/env python3
"""tools/copilot_eval.py must grade what it can check, ask for the rest, and write a result the board keeps apart.

Copilot CLI has no eval runner, so a person grades what the workspace cannot show. These tests
drive the script with scripted answers instead of a person and without Copilot: they build real
workspaces from the scaffolds, so the checks that run on files run on real files.

    python3 tools/test_copilot_eval.py
"""

import contextlib
import glob
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_eval_board as board  # noqa: E402
import copilot_eval as ce  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERIFICATION = os.path.join(REPO, "plugins", "verification")
SHARED = os.path.join(VERIFICATION, "evals", "behavior", "verify-change-follows-shared-code")


def answers(*replies):
    """An input() stand-in that returns the replies in order and records the questions."""
    queue = list(replies)
    asked = []

    def answer(question=""):
        asked.append(question)
        return queue.pop(0) if queue else "y"
    answer.asked = asked
    return answer


class Cases(unittest.TestCase):
    def test_loads_graders_with_their_targets_and_arms(self):
        case = ce.load_case(SHARED)
        by_name = {g["name"]: g for g in case["graders"]}
        self.assertEqual(by_name["money-unchanged"]["target"], "shop/money.py")
        self.assertIn("stash", by_name["tree-preserved"]["match"])
        self.assertFalse(ce.scored(by_name["used-skill"]), "Skill graders only show the plugin fired")
        self.assertTrue(case["scaffold"])

    def test_filters_by_tag_and_glob(self):
        names = [c["name"] for c in ce.cases_of(VERIFICATION, tag="trigger", case_glob="none-*")]
        self.assertTrue(names)
        self.assertTrue(all(n.startswith("none-") for n in names))

    def test_with_only_graders_are_left_out_of_the_without_arm(self):
        grader = {"arm": "with-only"}
        self.assertTrue(ce.applies(grader, "with"))
        self.assertFalse(ce.applies(grader, "without"))


@unittest.skipUnless(ce.bash(), "the scaffolds need bash")
class Grading(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.case = ce.load_case(SHARED)
        self.workspace = ce.build_workspace(self.case, "with", self.tmp)
        quiet = contextlib.redirect_stdout(io.StringIO())
        quiet.__enter__()
        self.addCleanup(quiet.__exit__, None, None, None)

    def test_file_graders_are_checked_in_the_workspace_not_asked(self):
        answer = answers("y", "y", "y", "y", "y")
        results = ce.grade_run(self.case, "with", self.workspace, "", answer)
        money = [r for r in results if r["name"] == "money-unchanged"][0]
        self.assertTrue(money["passed"])
        self.assertEqual(money["how"], "checked in the workspace")
        self.assertFalse(any("money-unchanged" in q for q in answer.asked))

    def test_an_edited_file_fails_its_regex_without_asking(self):
        path = os.path.join(self.workspace, "shop", "money.py")
        with open(path, "a") as fh:
            fh.write("\n# fixed by the agent\n")
        with open(path) as fh:
            text = fh.read().replace('"%s$%d.%02d"', '"%s%d.%02d"')
        with open(path, "w") as fh:
            fh.write(text)
        results = ce.grade_run(self.case, "with", self.workspace, "", answers())
        self.assertFalse([r for r in results if r["name"] == "money-unchanged"][0]["passed"])

    def test_score_leaves_out_the_skill_indicator_and_skips(self):
        # used-skill answered "n": it must not lower the score. One rubric skipped.
        graders = [g["name"] for g in self.case["graders"] if ce.auto_grade(g, self.workspace) is None]
        replies = {"used-skill": "n", "invoice-checked": "s"}
        answer = answers(*[replies.get(n, "y") for n in graders])
        results = ce.grade_run(self.case, "with", self.workspace, "", answer)
        self.assertNotIn("invoice-checked", [r["name"] for r in results])
        self.assertEqual(ce.score(results), 1.0)

    def test_hints_quote_the_transcript_lines_that_match(self):
        tree = [g for g in self.case["graders"] if g["name"] == "tree-preserved"][0]
        found = ce.hints(tree, "ran tests\n$ git stash -u\nok\n")
        self.assertEqual(found, ["$ git stash -u"])


@unittest.skipUnless(ce.bash(), "the scaffolds need bash")
class EndToEnd(unittest.TestCase):
    def test_a_manual_session_writes_a_copilot_result_the_board_keeps_apart(self):
        results_root = os.path.join(VERIFICATION, "evals", "results")
        before = set(glob.glob(os.path.join(results_root, "copilot-*")))
        # Enter after each arm, then every hand-graded grader: all pass with, all fail without.
        case = ce.load_case(SHARED)
        hand = lambda arm: [g for g in case["graders"] if ce.applies(g, arm) and g["type"] in ("tool_used", "llm")]
        with_arm = [""] + ["y"] * len(hand("with"))
        without_arm = [""] + ["n"] * len(hand("without"))
        with patch("time.strftime", return_value="2099-01-01T00-00-00Z"), contextlib.redirect_stdout(io.StringIO()):
            ce.main([os.path.relpath(VERIFICATION), "--case", "verify-change-follows-shared-code"],
                    answer=answers(*(with_arm + without_arm)))
        made = set(glob.glob(os.path.join(results_root, "copilot-*"))) - before
        self.assertEqual(len(made), 1)
        out = made.pop()
        self.addCleanup(shutil.rmtree, out, ignore_errors=True)
        path = os.path.join(out, "aggregate-result.json")
        with open(path) as fh:
            doc = json.load(fh)
        self.assertEqual(doc["host"], "copilot")
        case = doc["cases"][0]
        self.assertEqual(case["name"], "verify-change-follows-shared-code")
        self.assertEqual(case["aggregates"]["score"], 1.0)
        self.assertGreater(case["aggregates"]["delta"], 0)
        runs = board.load_results([path])["verification/verify-change-follows-shared-code"]
        self.assertEqual(runs[0]["host"], "copilot")
        self.assertTrue(board.trusted(runs[0]))


class Command(unittest.TestCase):
    def test_only_the_with_arm_loads_the_plugin(self):
        case = {"name": "c", "prompt": "verify my branch"}
        with_cmd = ce.copilot_command(case, "with", "/ws", VERIFICATION, "/out")
        without_cmd = ce.copilot_command(case, "without", "/ws", VERIFICATION, "/out")
        self.assertIn("--plugin-dir", with_cmd)
        self.assertNotIn("--plugin-dir", without_cmd)
        for cmd in (with_cmd, without_cmd):
            self.assertEqual(cmd[:3], ["copilot", "-p", "verify my branch"])
            self.assertIn("-C", cmd)
            self.assertIn("json", cmd)

    def test_partial_documents_are_never_trusted_on_the_board(self):
        doc = ce.result_doc("verification", {"c": {"with": [{"score": 1.0, "error": None, "graders": []}]}},
                            True, "interrupted", "2099-01-01T00-00-00Z")
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        path = os.path.join(tmp, "r.json")
        with open(path, "w") as fh:
            json.dump(doc, fh)
        run = board.load_results([path])["verification/c"][0]
        self.assertFalse(board.trusted(run))


if __name__ == "__main__":
    unittest.main(verbosity=1)
