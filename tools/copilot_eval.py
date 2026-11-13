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
- `file_exists` (only files created during the run count, as in claude plugin eval) and `regex` over a
  file, with its `match` mode (`not_contains`, `count:N`) and `flags`: checked in the workspace.
- `tool_used` and `regex` over the reply: you decide from the transcript. With --run it saves the
  JSONL output and a markdown transcript, and prints the transcript lines that match the grader's
  pattern as a hint; the hint is not a verdict.
- `llm`: you read the rubric and decide. Grade before you open fixtures/EXPECTED.md.

Each run is scored as the weighted share of graders that passed, leaving out `tool_used: Skill`,
which only shows whether the plugin fired. A grader you skip is recorded, and a run with a skipped
scored grader is marked incomplete, so the board never counts its score as trusted. With --run, a
Copilot run is stopped at the case's `timeout_seconds` and recorded as an error. The result goes to plugins/<plugin>/evals/results/copilot-<time>/
aggregate-result.json in the schema `claude plugin eval` writes (schemaVersion 1) plus
`"host": "copilot"`, so tools/build_eval_board.py shows it beside the Claude runs, never mixed in.
An interrupted session is saved as partial.

--run starts `copilot -p` in the scratch workspace with --allow-all-tools: the agent may run any
command there, as you. It uses your existing Copilot sign-in and is billed to your Copilot plan.
Pin the model with --model (and --reasoning-effort) so runs can be compared: both arms get the same flags,
and the result records them. Without --model, Copilot uses its own default, which can change between runs.
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
            "mode": unquote(g_fields.get("match", "")) or "contains",
            "flags": unquote(g_fields.get("flags", "")),
            "exists": unquote(g_fields.get("exists", "true")).lower() != "false",
            "weight": float(g_fields["weight"]) if re.match(r"^\d+(\.\d+)?$", g_fields.get("weight", "")) else 1.0,
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
        "timeout": int(fields["timeout_seconds"]) if fields.get("timeout_seconds", "").isdigit() else 600,
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


FLAGS = {"i": re.IGNORECASE, "m": re.MULTILINE, "s": re.DOTALL}


def files_in(workspace):
    """Every file under the workspace, relative, leaving out .git."""
    found = set()
    for root, dirs, names in os.walk(workspace):
        dirs[:] = [d for d in dirs if d != ".git"]
        for name in names:
            found.add(os.path.relpath(os.path.join(root, name), workspace).replace(os.sep, "/"))
    return found


def regex_holds(grader, text):
    """A regex grader's condition on `text`, honouring `match` (contains, not_contains, count:N) and `flags`."""
    flags = 0
    for letter in grader["flags"]:
        flags |= FLAGS.get(letter, 0)
    hits = len(re.findall(grader["pattern"], text, flags))
    mode = grader["mode"]
    if mode == "not_contains":
        return hits == 0
    if mode.startswith("count:") and mode[6:].isdigit():
        return hits == int(mode[6:])
    return hits > 0


def auto_grade(grader, workspace, before=frozenset()):
    """True or False for what can be checked in the workspace itself, else None.

    `before` is the set of files the scaffold made: file_exists counts only files created during
    the run, as claude plugin eval does."""
    if grader["type"] == "file_exists" and grader["path"]:
        created = files_in(workspace) - set(before)
        found = any(fnmatch.fnmatch(path, grader["path"]) for path in created)
        return found if grader["exists"] else not found
    if grader["type"] == "regex" and grader["target"]:
        path = os.path.join(workspace, grader["target"])
        if not os.path.isfile(path):
            return grader["mode"] == "not_contains"
        try:
            return regex_holds(grader, read(path))
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


def grade_run(case, arm, workspace, transcript, answer=input, before=frozenset()):
    """[{name, type, passed, how}] for every grader that applies to this arm; passed is None when skipped."""
    results = []
    for grader in case["graders"]:
        if not applies(grader, arm):
            continue
        verdict = auto_grade(grader, workspace, before)
        how = "checked in the workspace"
        if verdict is None:
            print("\n  [%s] %s%s" % (grader["name"], grader["type"],
                                     "" if scored(grader) else " (shows whether the plugin fired; not scored)"))
            print("  " + describe(grader).replace("\n", "\n  "))
            for line in hints(grader, transcript):
                print("    transcript: %s" % line)
            reply = ask("  passed? [y/n/s=skip] ", ("y", "n", "s"), answer)
            verdict = None if reply == "s" else reply == "y"
            how = "skipped" if reply == "s" else "graded by hand"
        else:
            print("  [%s] %s -- %s" % (grader["name"], "pass" if verdict else "FAIL", how))
        results.append({"name": grader["name"], "type": grader["type"], "passed": verdict,
                        "scored": scored(grader), "weight": grader["weight"], "how": how})
    return results


def skipped(results):
    """Scored graders nobody graded: a run missing any of them is incomplete."""
    return [r["name"] for r in results if r["scored"] and r["passed"] is None]


def score(results):
    """Weighted share of the graded, scored graders that passed."""
    counted = [r for r in results if r["scored"] and r["passed"] is not None]
    total = sum(r.get("weight", 1.0) for r in counted)
    if not total:
        return None
    return round(sum(r.get("weight", 1.0) for r in counted if r["passed"]) / total, 4)


def is_wsl_launcher(path):
    """C:\\Windows\\System32\\bash.exe and the WindowsApps stubs start WSL, which reads C:\\a\\b as escapes."""
    lowered = path.lower().replace("/", "\\")
    return "\\windows\\system32\\" in lowered or "\\windowsapps\\" in lowered


def bash():
    """A bash that can run the scaffolds: Git Bash on Windows, found next to git, else the one on PATH."""
    candidates = []
    git = shutil.which("git")
    if git:
        root = os.path.dirname(os.path.dirname(git))
        candidates += [os.path.join(root, "bin", "bash.exe"), os.path.join(root, "usr", "bin", "bash.exe")]
    for var in ("ProgramFiles", "ProgramFiles(x86)"):
        if os.environ.get(var):
            candidates.append(os.path.join(os.environ[var], "Git", "bin", "bash.exe"))
    if os.environ.get("LOCALAPPDATA"):
        candidates.append(os.path.join(os.environ["LOCALAPPDATA"], "Programs", "Git", "bin", "bash.exe"))
    candidates.append(shutil.which("bash"))
    for candidate in candidates:
        if candidate and os.path.isfile(candidate) and not is_wsl_launcher(candidate):
            return candidate
    return None


def build_workspace(case, arm, root):
    workspace = os.path.join(root, "%s-%s" % (case["name"], arm))
    os.makedirs(workspace)
    if case["scaffold"]:
        shell = bash()
        if not shell:
            raise SystemExit("no usable bash found: install Git for Windows (Git Bash). The bash.exe in "
                             "C:\\Windows\\System32 is WSL and cannot run the scaffolds.")
        # Forward slashes: Git Bash reads C:/a/b, and reads C:\a\b as escape sequences.
        script = case["scaffold"].replace("\\", "/")
        try:
            subprocess.run([shell, script], cwd=workspace, check=True)
        except subprocess.CalledProcessError as exc:
            raise SystemExit("the scaffold of %s failed (exit %d, bash: %s)" % (case["name"], exc.returncode, shell))
    return workspace


def model_flags(model=None, effort=None):
    """The copilot flags that pin the model and its reasoning effort; both arms must get the same ones."""
    return (["--model", model] if model else []) + (["--reasoning-effort", effort] if effort else [])


def copilot_command(case, arm, workspace, plugin_dir, out_dir, model=None, effort=None):
    command = ["copilot", "-p", case["prompt"], "-C", workspace, "--allow-all-tools", "--no-ask-user",
               "--output-format", "json", "--share", os.path.join(out_dir, "%s-%s.md" % (case["name"], arm))]
    if arm == "with":
        command += ["--plugin-dir", os.path.abspath(plugin_dir)]
    return command + model_flags(model, effort)


def run_copilot(command, log_path, timeout):
    """(error or None, seconds). A run past the case's timeout_seconds is stopped and is an error."""
    env = dict(os.environ, COPILOT_PLUGIN_DIR_ONLY="true")
    started = time.time()
    with open(log_path, "w", encoding="utf-8") as log:
        try:
            proc = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, env=env, timeout=timeout)
        except subprocess.TimeoutExpired:
            return "timed out after %ds" % timeout, round(time.time() - started, 1)
    error = None if proc.returncode == 0 else "copilot exited %d" % proc.returncode
    return error, round(time.time() - started, 1)


def result_doc(plugin, records, partial, reason, started, model=None, effort=None):
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
        # What produced the scores: null means Copilot's own default at the time, which can change.
        "model": model,
        "reasoningEffort": effort,
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
    parser.add_argument("--model", help="pin the model for every run, passed to copilot --model "
                                        "(see /model in Copilot for the names your plan offers)")
    parser.add_argument("--reasoning-effort", dest="effort",
                        choices=("none", "minimal", "low", "medium", "high", "xhigh", "max"),
                        help="pin the reasoning effort, passed to copilot --reasoning-effort "
                             "(the levels a model offers depend on the model)")
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
                before = files_in(workspace)
                command = copilot_command(case, arm, workspace, plugin_dir, out_dir, args.model, args.effort)
                pinned = "".join(" %s" % flag for flag in model_flags(args.model, args.effort))
                transcript, error = "", None
                if args.run:
                    log = os.path.join(out_dir, "%s-%s.jsonl" % (case["name"], arm))
                    error, seconds = run_copilot(command, log, case["timeout"])
                    print("copilot %s after %ss" % (error or "finished", seconds))
                    for path in (log, os.path.join(out_dir, "%s-%s.md" % (case["name"], arm))):
                        if os.path.isfile(path):
                            transcript += read(path)
                else:
                    print("Workspace: %s" % workspace)
                    if arm == "with":
                        print("Start Copilot there with the plugin, for example:\n  set COPILOT_PLUGIN_DIR_ONLY=true"
                              "  (PowerShell: $env:COPILOT_PLUGIN_DIR_ONLY='true')\n  copilot -C \"%s\" --plugin-dir \"%s\"%s"
                              % (workspace, plugin_dir, pinned))
                    else:
                        print("Start Copilot there WITHOUT the plugin:\n  (PowerShell: $env:COPILOT_PLUGIN_DIR_ONLY='true')\n"
                              "  copilot -C \"%s\"%s" % (workspace, pinned))
                    print("Paste this prompt:\n" + "-" * 60 + "\n" + case["prompt"] + "\n" + "-" * 60)
                    answer("Press Enter when the agent has finished. ")
                results = grade_run(case, arm, workspace, transcript, answer, before)
                missing = skipped(results)
                if missing and not error:
                    # Not an abnormal end, but the score covers less than the case asks: never trusted.
                    error = "not graded: %s" % ", ".join(missing)
                run = {"score": score(results), "error": error, "graders": results, "skippedGraders": missing}
                records.setdefault(case["name"], {}).setdefault(arm, []).append(run)
                print("  -> score %s" % ("—" if run["score"] is None else "%.2f" % run["score"]))
    except KeyboardInterrupt:
        partial, reason = True, "interrupted"
        print("\ninterrupted; saving what was graded")
    except SystemExit:
        # A scaffold that cannot be built is a setup problem, not a result: leave no empty results folder.
        if not records:
            shutil.rmtree(out_dir, ignore_errors=True)
        shutil.rmtree(scratch, ignore_errors=True)
        raise
    doc = result_doc(plugin, records, partial, reason, started, args.model, args.effort)
    with open(os.path.join(out_dir, "aggregate-result.json"), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2)
    if not args.keep:
        shutil.rmtree(scratch, ignore_errors=True)
    print("\nwrote %s" % os.path.relpath(os.path.join(out_dir, "aggregate-result.json")))
    print("see it with: python3 tools/build_eval_board.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
