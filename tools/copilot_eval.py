#!/usr/bin/env python3
"""Run a plugin's eval cases on GitHub Copilot CLI and record the scores where the eval board reads them.

`claude plugin eval` runs and grades the suites under plugins/<plugin>/evals/ on Claude Code.
Copilot CLI has no runner for that format, but it can run one prompt non-interactively in a
directory with exactly the plugins it is given. This script drives that: for every case and both
arms it builds a fresh workspace from the case's scaffold.sh, runs (or asks you to run) Copilot
there with the plugin (`--plugin-dir`) and without it, and records a pass or fail for every grader.

    python3 tools/copilot_eval.py plugins/verification --tag behavior --run
    python3 tools/copilot_eval.py plugins/verification --case 'none-*'          # you run Copilot yourself

What it grades itself, and what it asks you:
- `file_exists` and `regex` over a file: checked in the workspace.
- `tool_used` and `regex` over the reply: you decide from the transcript. With --run it saves the
  JSONL output and a markdown transcript, and prints the transcript lines that match the grader's
  pattern as a hint; the hint is not a verdict.
- `llm`: you read the rubric and decide. Grade before you open fixtures/EXPECTED.md.

Each run is scored as the share of graders that passed, leaving out `tool_used: Skill`, which only
shows whether the plugin fired. The result goes to plugins/<plugin>/evals/results/copilot-<time>/
aggregate-result.json in the schema `claude plugin eval` writes (schemaVersion 1) plus
`"host": "copilot"`, so tools/build_eval_board.py shows it beside the Claude runs, never mixed in.
An interrupted session is saved as partial.

--run starts `copilot -p` in the scratch workspace with --allow-all-tools: the agent may run any
command there, as you. It uses your existing Copilot sign-in and is billed to your Copilot plan.
Standard library only; the scaffolds need bash (Git Bash on Windows).
"""

import argparse
import fnmatch
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_eval_board import frontmatter, read, unquote  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET_PATH = re.compile(r"path:\s*([^,}]+)")


def load_case(case_dir):
    fields, prompt = frontmatter(read(os.path.join(case_dir, "prompt.md")))
    graders = []
    for path in sorted(glob.glob(os.path.join(case_dir, "graders", "*.md"))):
        g_fields, rubric = frontmatter(read(path))
        target = TARGET_PATH.search(g_fields.get("target", ""))
        graders.append({
            "name": os.path.basename(path)[:-3],
            "type": g_fields.get("type", "?"),
            "tool": g_fields.get("tool", ""),
            "match": unquote(g_fields.get("input_match", "")),
            "pattern": unquote(g_fields.get("pattern", "")),
            "path": unquote(g_fields.get("path", "")),
            "target": target.group(1).strip() if target else None,
            "min": int(g_fields["min"]) if g_fields.get("min", "").isdigit() else 1,
            "max": int(g_fields["max"]) if g_fields.get("max", "").isdigit() else None,
            "arm": g_fields.get("arm", "both"),
            "rubric": rubric,
        })
    scaffold = os.path.join(case_dir, "scaffold.sh")
    return {
        "name": os.path.basename(case_dir),
        "kind": os.path.basename(os.path.dirname(case_dir)),
        "description": unquote(fields.get("description", "")),
        "tags": re.findall(r"[\w-]+", fields.get("tags", "")),
        "prompt": prompt,
        "graders": graders,
        "scaffold": scaffold if os.path.isfile(scaffold) else None,
    }


def cases_of(plugin_dir, tag=None, case_glob=None):
    found = []
    for prompt in sorted(glob.glob(os.path.join(plugin_dir, "evals", "*", "*", "prompt.md"))):
        case = load_case(os.path.dirname(prompt))
        if tag and tag not in case["tags"] and tag != case["kind"]:
            continue
        if case_glob and not fnmatch.fnmatch(case["name"], case_glob):
            continue
        found.append(case)
    return found


def scored(grader):
    """`tool_used: Skill` graders only show whether the plugin fired; they are not part of the score."""
    return not (grader["type"] == "tool_used" and grader["tool"] == "Skill")


def applies(grader, arm):
    return grader["arm"] != "with-only" or arm == "with"


def auto_grade(grader, workspace):
    """True or False for what can be checked in the workspace itself, else None."""
    if grader["type"] == "file_exists" and grader["path"]:
        return bool(glob.glob(os.path.join(workspace, grader["path"]), recursive=True))
    if grader["type"] == "regex" and grader["target"]:
        path = os.path.join(workspace, grader["target"])
        if not os.path.isfile(path):
            return False
        try:
            return re.search(grader["pattern"], read(path)) is not None
        except re.error:
            return None
    return None


def hints(grader, transcript):
    """Transcript lines matching the grader's pattern: a hint for the person grading, never a verdict."""
    pattern = grader["match"] or (grader["pattern"] if grader["type"] == "regex" else "")
    if not pattern or not transcript:
        return []
    try:
        rx = re.compile(pattern)
    except re.error:
        return []
    return [line.strip()[:160] for line in transcript.splitlines() if rx.search(line)][:5]


def describe(grader):
    if grader["type"] == "tool_used":
        what = "must NOT call" if grader["max"] == 0 else "must call"
        target = grader["tool"] + (" with input matching %s" % grader["match"] if grader["match"] else "")
        return "%s %s" % (what, target)
    if grader["type"] == "regex":
        return "%s matches %s" % (grader["target"] or "the reply", grader["pattern"])
    if grader["type"] == "file_exists":
        return "a file exists at %s" % grader["path"]
    return grader["rubric"]


def ask(question, choices, answer=input):
    while True:
        reply = answer(question).strip().lower()
        if reply in choices:
            return reply
        print("  answer one of: %s" % "/".join(choices))


def grade_run(case, arm, workspace, transcript, answer=input):
    """[{name, type, passed, how}] for every grader that applies to this arm."""
    results = []
    for grader in case["graders"]:
        if not applies(grader, arm):
            continue
        verdict = auto_grade(grader, workspace)
        how = "checked in the workspace"
        if verdict is None:
            print("\n  [%s] %s%s" % (grader["name"], grader["type"],
                                     "" if scored(grader) else " (shows whether the plugin fired; not scored)"))
            print("  " + describe(grader).replace("\n", "\n  "))
            for line in hints(grader, transcript):
                print("    transcript: %s" % line)
            reply = ask("  passed? [y/n/s=skip] ", ("y", "n", "s"), answer)
            if reply == "s":
                continue
            verdict, how = reply == "y", "graded by hand"
        else:
            print("  [%s] %s -- %s" % (grader["name"], "pass" if verdict else "FAIL", how))
        results.append({"name": grader["name"], "type": grader["type"], "passed": verdict,
                        "scored": scored(grader), "how": how})
    return results


def score(results):
    counted = [r for r in results if r["scored"]]
    return round(sum(1 for r in counted if r["passed"]) / len(counted), 4) if counted else None


def bash():
    for candidate in (shutil.which("bash"), r"C:\Program Files\Git\bin\bash.exe"):
        if candidate and os.path.isfile(candidate):
            return candidate
    return None


def build_workspace(case, arm, root):
    workspace = os.path.join(root, "%s-%s" % (case["name"], arm))
    os.makedirs(workspace)
    if case["scaffold"]:
        shell = bash()
        if not shell:
            raise SystemExit("bash not found: install Git for Windows, or run from a shell that has bash")
        subprocess.run([shell, case["scaffold"]], cwd=workspace, check=True)
    return workspace


def copilot_command(case, arm, workspace, plugin_dir, out_dir, model=None):
    command = ["copilot", "-p", case["prompt"], "-C", workspace, "--allow-all-tools", "--no-ask-user",
               "--output-format", "json", "--share", os.path.join(out_dir, "%s-%s.md" % (case["name"], arm))]
    if arm == "with":
        command += ["--plugin-dir", os.path.abspath(plugin_dir)]
    if model:
        command += ["--model", model]
    return command


def run_copilot(command, log_path):
    env = dict(os.environ, COPILOT_PLUGIN_DIR_ONLY="true")
    started = time.time()
    with open(log_path, "w", encoding="utf-8") as log:
        proc = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, env=env)
    return proc.returncode, round(time.time() - started, 1)


def result_doc(plugin, records, partial, reason, started):
    cases = []
    for name, arms in records.items():
        with_runs, without_runs = arms.get("with", []), arms.get("without", [])
        with_scores = [r["score"] for r in with_runs if r["score"] is not None]
        without_scores = [r["score"] for r in without_runs if r["score"] is not None]
        agg = {"score": round(sum(with_scores) / len(with_scores), 4) if with_scores else None}
        if with_scores and without_scores:
            agg["delta"] = round(agg["score"] - sum(without_scores) / len(without_scores), 4)
        cases.append({"name": name, "aggregates": agg, "arms": {"with": with_runs, "without": without_runs}})
    scores = [c["aggregates"]["score"] for c in cases if c["aggregates"]["score"] is not None]
    deltas = [c["aggregates"]["delta"] for c in cases if "delta" in c["aggregates"]]
    return {
        "schemaVersion": 1,
        "host": "copilot",
        "partial": partial,
        "partialReason": reason,
        "suite": {"plugins": [{"name": plugin}]},
        "aggregates": {"overallScore": round(sum(scores) / len(scores), 4) if scores else None,
                       "meanDelta": round(sum(deltas) / len(deltas), 4) if deltas else None,
                       "casesTotal": len(cases)},
        "cases": cases,
        "startedAt": started,
    }


def main(argv=None, answer=input):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("plugin_dir", help="plugins/<plugin>")
    parser.add_argument("--tag", help="only cases with this tag (trigger, behavior)")
    parser.add_argument("--case", help="only cases whose name matches this glob")
    parser.add_argument("--arms", default="with,without", help="with, without, or both (default)")
    parser.add_argument("--run", action="store_true", help="start copilot -p yourself instead of asking")
    parser.add_argument("--model", help="passed to copilot --model")
    parser.add_argument("--keep", action="store_true", help="keep the scratch workspaces")
    args = parser.parse_args(argv)

    plugin_dir = os.path.abspath(args.plugin_dir)
    plugin = os.path.basename(plugin_dir.rstrip(os.sep))
    cases = cases_of(plugin_dir, args.tag, args.case)
    if not cases:
        raise SystemExit("no eval case matches under %s/evals" % args.plugin_dir)
    arms = [a for a in ("with", "without") if a in args.arms.split(",")]
    if args.run and not shutil.which("copilot"):
        raise SystemExit("copilot not found on PATH; install GitHub Copilot CLI or leave out --run")

    started = time.strftime("%Y-%m-%dT%H-%M-%SZ", time.gmtime())
    out_dir = os.path.join(plugin_dir, "evals", "results", "copilot-%s" % started)
    os.makedirs(out_dir)
    scratch = tempfile.mkdtemp(prefix="copilot-eval-")
    records, partial, reason = {}, False, None
    print("%d case(s) x %d arm(s); results go to %s" % (len(cases), len(arms), os.path.relpath(out_dir)))
    try:
        for case in cases:
            for arm in arms:
                print("\n=== %s · %s plugin ===" % (case["name"], arm))
                workspace = build_workspace(case, arm, scratch)
                command = copilot_command(case, arm, workspace, plugin_dir, out_dir, args.model)
                transcript, error = "", None
                if args.run:
                    log = os.path.join(out_dir, "%s-%s.jsonl" % (case["name"], arm))
                    code, seconds = run_copilot(command, log)
                    print("copilot exited %d after %ss" % (code, seconds))
                    error = None if code == 0 else "copilot exited %d" % code
                    for path in (log, os.path.join(out_dir, "%s-%s.md" % (case["name"], arm))):
                        if os.path.isfile(path):
                            transcript += read(path)
                else:
                    print("Workspace: %s" % workspace)
                    if arm == "with":
                        print("Start Copilot there with the plugin, for example:\n  set COPILOT_PLUGIN_DIR_ONLY=true"
                              "  (PowerShell: $env:COPILOT_PLUGIN_DIR_ONLY='true')\n  copilot -C \"%s\" --plugin-dir \"%s\""
                              % (workspace, plugin_dir))
                    else:
                        print("Start Copilot there WITHOUT the plugin:\n  (PowerShell: $env:COPILOT_PLUGIN_DIR_ONLY='true')\n"
                              "  copilot -C \"%s\"" % workspace)
                    print("Paste this prompt:\n" + "-" * 60 + "\n" + case["prompt"] + "\n" + "-" * 60)
                    answer("Press Enter when the agent has finished. ")
                results = grade_run(case, arm, workspace, transcript, answer)
                run = {"score": score(results), "error": error, "graders": results}
                records.setdefault(case["name"], {}).setdefault(arm, []).append(run)
                print("  -> score %s" % ("—" if run["score"] is None else "%.2f" % run["score"]))
    except KeyboardInterrupt:
        partial, reason = True, "interrupted"
        print("\ninterrupted; saving what was graded")
    doc = result_doc(plugin, records, partial, reason, started)
    with open(os.path.join(out_dir, "aggregate-result.json"), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2)
    if not args.keep:
        shutil.rmtree(scratch, ignore_errors=True)
    print("\nwrote %s" % os.path.relpath(os.path.join(out_dir, "aggregate-result.json")))
    print("see it with: python3 tools/build_eval_board.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
