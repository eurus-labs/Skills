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
        # used-skill fails: it must not lower the score. One rubric skipped; every other grader passes.
        hand = [g for g in self.case["graders"] if ce.auto_grade(g, self.workspace) is None]
        replies = {"used-skill": ce.reply_for([g for g in hand if g["name"] == "used-skill"][0], False),
                   "invoice-checked": "s"}
        answer = answers(*[replies.get(g["name"], ce.reply_for(g, True)) for g in hand])
        results = ce.grade_run(self.case, "with", self.workspace, "", answer)
        self.assertEqual(ce.skipped(results), ["invoice-checked"], "a skipped grader is recorded, not dropped")
        self.assertEqual(ce.score(results), 1.0)

    def test_file_exists_counts_only_files_the_run_created(self):
        before = ce.files_in(self.workspace)
        grader = {"type": "file_exists", "path": "shop/*.py", "exists": True}
        self.assertFalse(ce.auto_grade(grader, self.workspace, before), "scaffold files do not count")
        with open(os.path.join(self.workspace, "shop", "new.py"), "w") as fh:
            fh.write("x = 1\n")
        self.assertTrue(ce.auto_grade(grader, self.workspace, before))
        self.assertFalse(ce.auto_grade(dict(grader, exists=False), self.workspace, before))

    def test_rule_graders_are_asked_as_plain_facts(self):
        # The first real Copilot run asked "must NOT call Skill … setup-verification — passed?",
        # which the person had to invert in their head.
        quiet = {"type": "tool_used", "tool": "Skill", "min": 0, "max": 0,
                 "match": '"skill"\\s*:\\s*"(?:[\\w-]+:)?setup-verification"'}
        fires = dict(quiet, min=1, max=None)
        no_edit = {"type": "tool_used", "tool": "Edit", "min": 0, "max": 0, "match": ""}
        self.assertEqual(ce.fact_question(quiet), ("Did Copilot use the skill `setup-verification`?", "n"))
        self.assertEqual(ce.fact_question(fires), ("Did Copilot use the skill `setup-verification`?", "y"))
        self.assertEqual(ce.fact_question(no_edit), ("Did Copilot change or create any file?", "n"))
        self.assertIsNone(ce.fact_question({"type": "llm"}))

    def test_answering_the_fact_decides_the_grade(self):
        case = {"graders": [{"name": "quiet", "type": "tool_used", "tool": "Skill", "min": 0, "max": 0,
                             "match": '"skill"\\s*:\\s*"(?:[\\w-]+:)?setup-verification"', "arm": "both",
                             "weight": 1.0}]}
        asked = answers("n")
        not_used = ce.grade_run(case, "with", self.workspace, "", asked)[0]
        self.assertTrue(not_used["passed"], "the skill was not used, so 'must not use it' passes")
        self.assertIn("Did Copilot use the skill `setup-verification`?", asked.asked[0])
        used = ce.grade_run(case, "with", self.workspace, "", answers("y"))[0]
        self.assertFalse(used["passed"])

    def test_skill_hints_look_for_the_skill_name_not_claude_json(self):
        grader = {"type": "tool_used", "tool": "Skill", "match": '"skill"\\s*:\\s*"(?:[\\w-]+:)?verify-change"'}
        transcript = '{"type":"tool.call","name":"skill","arguments":{"name":"verify-change"}}\nother line\n'
        self.assertEqual(len(ce.hints(grader, transcript)), 1)

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
        with_arm = [""] + [ce.reply_for(g, True) for g in hand("with")]
        without_arm = [""] + [ce.reply_for(g, False) for g in hand("without")]
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

    def test_skipping_a_scored_grader_makes_the_run_untrusted(self):
        results_root = os.path.join(VERIFICATION, "evals", "results")
        before = set(glob.glob(os.path.join(results_root, "copilot-*")))
        # Enter, then skip every hand-graded grader: only the file check is left, and it passes.
        with patch("time.strftime", return_value="2099-01-02T00-00-00Z"), contextlib.redirect_stdout(io.StringIO()):
            ce.main([os.path.relpath(VERIFICATION), "--case", "verify-change-follows-shared-code",
                     "--arms", "with"], answer=answers("", "s", "s", "s", "s", "s"))
        out = (set(glob.glob(os.path.join(results_root, "copilot-*"))) - before).pop()
        self.addCleanup(shutil.rmtree, out, ignore_errors=True)
        path = os.path.join(out, "aggregate-result.json")
        run = board.load_results([path])["verification/verify-change-follows-shared-code"][0]
        self.assertEqual(run["score"], 1.0)
        self.assertFalse(board.trusted(run), "a perfect score over one file check is not a result")


@unittest.skipUnless(ce.bash(), "the scaffolds need bash")
class MatchModes(unittest.TestCase):
    def test_not_contains_passes_on_the_untouched_test_and_fails_once_loosened(self):
        case = ce.load_case(os.path.join(REPO, "plugins", "testing", "evals", "behavior",
                                         "debug-failing-test-blames-the-test"))
        grader = [g for g in case["graders"] if g["name"] == "not-loosened"][0]
        self.assertEqual(grader["mode"], "not_contains")
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        workspace = ce.build_workspace(case, "with", tmp)
        self.assertTrue(ce.auto_grade(grader, workspace))
        path = os.path.join(workspace, grader["target"])
        with open(path, "a") as fh:
            fh.write("\n# pytest.mark.skip\n")
        self.assertFalse(ce.auto_grade(grader, workspace))

    def test_count_and_flags(self):
        grader = {"pattern": "abc", "mode": "count:2", "flags": "i"}
        self.assertTrue(ce.regex_holds(grader, "ABC and abc"))
        self.assertFalse(ce.regex_holds(grader, "abc"))
        self.assertFalse(ce.regex_holds(dict(grader, flags=""), "ABC and abc"))


class WindowsBash(unittest.TestCase):
    """The first Windows run failed: `bash` on PATH was WSL, which ate the backslashes of the script path."""

    def test_the_wsl_launchers_are_recognised(self):
        self.assertTrue(ce.is_wsl_launcher(r"C:\WINDOWS\system32\bash.EXE"))
        self.assertTrue(ce.is_wsl_launcher(r"C:\Users\a\AppData\Local\Microsoft\WindowsApps\bash.exe"))
        self.assertFalse(ce.is_wsl_launcher(r"C:\Program Files\Git\bin\bash.exe"))
        self.assertFalse(ce.is_wsl_launcher("/usr/bin/bash"))

    def test_bash_skips_wsl_and_prefers_the_one_next_to_git(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        git_bash = os.path.join(tmp, "Git", "bin", "bash.exe")
        os.makedirs(os.path.dirname(git_bash))
        open(git_bash, "w").close()
        which = {"git": os.path.join(tmp, "Git", "cmd", "git.exe"), "bash": r"C:\WINDOWS\system32\bash.EXE"}
        with patch("shutil.which", side_effect=which.get), \
                patch.object(ce.os.path, "isfile", side_effect=lambda p: p == git_bash or p == which["bash"]):
            self.assertEqual(ce.bash(), git_bash)

    def test_only_wsl_on_path_means_no_usable_bash(self):
        wsl = r"C:\WINDOWS\system32\bash.EXE"
        with patch("shutil.which", side_effect={"bash": wsl}.get), \
                patch.object(ce.os.path, "isfile", side_effect=lambda p: p == wsl), \
                patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(ce.bash())

    def test_the_scaffold_path_is_passed_with_forward_slashes(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        case = {"name": "c", "scaffold": r"C:\Workspace\Skills\plugins\p\scaffold.sh"}
        with patch.object(ce, "bash", return_value="bash"), patch("subprocess.run") as run:
            ce.build_workspace(case, "with", tmp)
        self.assertEqual(run.call_args[0][0], ["bash", "C:/Workspace/Skills/plugins/p/scaffold.sh"])

    def test_a_setup_failure_leaves_no_empty_results_folder(self):
        results_root = os.path.join(VERIFICATION, "evals", "results")
        before = set(glob.glob(os.path.join(results_root, "copilot-*")))
        with patch.object(ce, "bash", return_value=None), patch("time.strftime", return_value="2099-01-03T00-00-00Z"), \
                contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit):
                ce.main([os.path.relpath(VERIFICATION), "--case", "verify-change-follows-shared-code"])
        self.assertEqual(set(glob.glob(os.path.join(results_root, "copilot-*"))), before)

    def test_a_failing_scaffold_is_a_message_not_a_traceback(self):
        import subprocess as sp
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        case = {"name": "c", "scaffold": "/nope/scaffold.sh"}
        with patch.object(ce, "bash", return_value="bash"), \
                patch("subprocess.run", side_effect=sp.CalledProcessError(127, "bash")):
            with self.assertRaises(SystemExit) as caught:
                ce.build_workspace(case, "with", tmp)
        self.assertIn("scaffold of c failed", str(caught.exception))


REAL_WHICH = shutil.which


def with_copilot_on_path(name):
    """shutil.which that finds a pretend copilot and the real everything else."""
    return "copilot" if name == "copilot" else REAL_WHICH(name)


@unittest.skipUnless(ce.bash(), "the scaffolds need bash")
class WhenCopilotRefuses(unittest.TestCase):
    """The first real run: `--model claude-haiku-5.5` made copilot exit 1 after 4.8 s, the script said only
    "copilot copilot exited 1" and went on to ask whether a dead agent had passed."""

    def setUp(self):
        self.results_root = os.path.join(VERIFICATION, "evals", "results")
        self.before = set(glob.glob(os.path.join(self.results_root, "copilot-*")))
        self.addCleanup(lambda: [shutil.rmtree(p, ignore_errors=True)
                                 for p in set(glob.glob(os.path.join(self.results_root, "copilot-*"))) - self.before])

    def test_preflight_returns_what_copilot_said_when_it_refuses(self):
        refused = subprocess_result(1, "", "Error: model 'claude-haiku-5.5' is not available")
        with patch("subprocess.run", return_value=refused):
            ok, output = ce.preflight("claude-haiku-5.5", "medium")
        self.assertFalse(ok)
        self.assertIn("is not available", output)

    def test_preflight_passes_the_pinned_flags_and_accepts_exit_0(self):
        with patch("subprocess.run", return_value=subprocess_result(0, "ok", "")) as run:
            ok, _ = ce.preflight("gpt-5.6-sol", "low")
        self.assertTrue(ok)
        command = run.call_args[0][0]
        self.assertEqual(command[-4:], ["--model", "gpt-5.6-sol", "--reasoning-effort", "low"])

    def test_a_refused_model_stops_before_any_case_and_shows_the_reason(self):
        refused = subprocess_result(1, "", "Error: model 'claude-haiku-5.5' is not available")
        with patch("shutil.which", side_effect=with_copilot_on_path), patch("subprocess.run", return_value=refused), \
                contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                ce.main([os.path.relpath(VERIFICATION), "--case", "none-implement-feature", "--run",
                         "--model", "claude-haiku-5.5"])
        message = str(caught.exception)
        self.assertIn("is not available", message)
        self.assertIn("/model", message)
        self.assertEqual(set(glob.glob(os.path.join(self.results_root, "copilot-*"))), self.before)

    def test_a_dead_run_is_not_graded_and_a_first_failure_stops_the_suite(self):
        def never(question=""):
            raise AssertionError("a run that died must not be put to the person for grading: %r" % question)
        out = io.StringIO()
        with patch("shutil.which", side_effect=with_copilot_on_path), \
                patch.object(ce, "preflight", return_value=(True, "ok")), \
                patch.object(ce, "run_copilot", return_value=("copilot exited 1", 4.8)), \
                patch("time.strftime", return_value="2099-01-04T00-00-00Z"), contextlib.redirect_stdout(out):
            ce.main([os.path.relpath(VERIFICATION), "--tag", "trigger", "--run"], answer=never)
        self.assertIn("copilot exited 1 after 4.8s", out.getvalue())
        self.assertNotIn("copilot copilot", out.getvalue())
        path = os.path.join(self.results_root, "copilot-2099-01-04T00-00-00Z", "aggregate-result.json")
        with open(path) as fh:
            doc = json.load(fh)
        self.assertTrue(doc["partial"])
        self.assertEqual(doc["partialReason"], "copilot_failed")
        self.assertEqual(len(doc["cases"]), 1, "the suite stops after the first run: nothing had worked yet")
        run = doc["cases"][0]["arms"]["with"][0]
        self.assertIsNone(run["score"])
        self.assertEqual(run["error"], "copilot exited 1")

    def test_a_later_failure_is_recorded_and_the_suite_goes_on(self):
        calls = []

        def run_copilot(command, log, timeout):
            calls.append(command)
            return (None, 1.0) if len(calls) == 1 else ("copilot exited 1", 1.0)
        with patch("shutil.which", side_effect=with_copilot_on_path), \
                patch.object(ce, "preflight", return_value=(True, "ok")), \
                patch.object(ce, "run_copilot", side_effect=run_copilot), \
                patch("time.strftime", return_value="2099-01-05T00-00-00Z"), contextlib.redirect_stdout(io.StringIO()):
            ce.main([os.path.relpath(VERIFICATION), "--case", "none-implement-feature", "--run"],
                    answer=answers(*(["y"] * 10)))
        self.assertEqual(len(calls), 2, "both arms ran: the first worked, so the second failure does not stop it")

    def test_log_tail_keeps_the_last_lines_and_survives_a_missing_file(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        path = os.path.join(tmp, "log")
        with open(path, "w") as fh:
            fh.write("\n".join("line %d" % i for i in range(30)) + "\n")
        tail = ce.log_tail(path, lines=3).splitlines()
        self.assertEqual([t.strip() for t in tail], ["| line 27", "| line 28", "| line 29"])
        self.assertEqual(ce.log_tail(os.path.join(tmp, "missing")), "")


def subprocess_result(code, out, err):
    import subprocess as sp
    return sp.CompletedProcess([], code, out, err)


class Command(unittest.TestCase):
    def test_a_run_past_its_timeout_is_stopped_and_recorded_as_an_error(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        error, _ = ce.run_copilot([sys.executable, "-c", "import time; time.sleep(30)"],
                                  os.path.join(tmp, "log.jsonl"), timeout=1)
        self.assertEqual(error, "timed out after 1s")

    def test_cases_carry_their_timeout(self):
        self.assertEqual(ce.load_case(SHARED)["timeout"], 1200)

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

    def test_the_model_and_effort_reach_both_arms_and_the_result(self):
        case = {"name": "c", "prompt": "p"}
        for arm in ("with", "without"):
            cmd = ce.copilot_command(case, arm, "/ws", VERIFICATION, "/out", "gpt-5.6-sol", "high")
            self.assertEqual(cmd[-4:], ["--model", "gpt-5.6-sol", "--reasoning-effort", "high"])
        unpinned = ce.copilot_command(case, "with", "/ws", VERIFICATION, "/out")
        self.assertNotIn("--model", unpinned)
        doc = ce.result_doc("verification", {}, False, None, "2099-01-01T00-00-00Z", "gpt-5.6-sol", "high")
        self.assertEqual((doc["model"], doc["reasoningEffort"]), ("gpt-5.6-sol", "high"))
        self.assertIsNone(ce.result_doc("verification", {}, False, None, "2099-01-01T00-00-00Z")["model"])

    def test_the_board_reads_the_model_a_run_used(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        doc = ce.result_doc("verification", {"c": {"with": [{"score": 1.0, "error": None, "graders": []}]}},
                            False, None, "2099-01-01T00-00-00Z", "gpt-5.6-sol")
        path = os.path.join(tmp, "r.json")
        with open(path, "w") as fh:
            json.dump(doc, fh)
        self.assertEqual(board.load_results([path])["verification/c"][0]["model"], "gpt-5.6-sol")

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
