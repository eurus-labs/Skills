#!/usr/bin/env python3
"""Behavioural tests for the eval scaffolds.

An eval measures a skill against a fixture only while its scaffold.sh recreates that
fixture exactly. These tests run every committed scaffold in an empty directory and
compare the result with the fixture byte for byte, and check the committed scripts are
what the generator writes today.

Stdlib only, no test framework -- see tools/test_check_env.py for why.

    python3 tools/test_eval_scaffolds.py
"""

import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))

import build_eval_scaffolds as build  # noqa: E402

FAILURES = []


def check(name, condition, detail=""):
    if condition:
        print("ok   %s" % name)
    else:
        print("FAIL %s %s" % (name, detail))
        FAILURES.append(name)


def tree(root):
    found = {}
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            path = os.path.join(dirpath, name)
            with open(path, "rb") as fh:
                found[os.path.relpath(path, root).replace(os.sep, "/")] = fh.read()
    return found


def main():
    proc = subprocess.run([sys.executable, os.path.join(REPO, "tools", "build_eval_scaffolds.py"),
                           "--check"], capture_output=True, text=True)
    check("every scaffold.sh matches what the generator writes", proc.returncode == 0,
          proc.stdout + proc.stderr)

    if shutil.which("bash") is None:
        print("skip: no bash to run the scaffolds")
        return 1 if FAILURES else 0

    for case_rel, (source_rel, exclude) in sorted(build.SCAFFOLDS.items()):
        script = os.path.join(REPO, case_rel, "scaffold.sh")
        if not os.path.isfile(script):
            check("%s has a scaffold.sh" % case_rel, False)
            continue
        workspace = tempfile.mkdtemp(prefix="eval-scaffold-")
        try:
            run = subprocess.run(["bash", script], cwd=workspace, capture_output=True, text=True)
            check("%s scaffold runs" % case_rel, run.returncode == 0, run.stderr)
            expected = {rel: text.encode("utf-8") for rel, text in
                        build.fixture_files(os.path.join(REPO, source_rel), exclude)}
            got = tree(workspace)
            check("%s carries no scenario README, which states the answer" % case_rel,
                  not (source_rel.startswith("fixtures/") and "README.md" in got))
            check("%s recreates %s exactly" % (case_rel, source_rel), got == expected,
                  "missing %s, extra %s, differing %s" % (
                      sorted(set(expected) - set(got)), sorted(set(got) - set(expected)),
                      sorted(k for k in set(got) & set(expected) if got[k] != expected[k])))
        finally:
            shutil.rmtree(workspace, ignore_errors=True)

    # The heredoc is quoted, so nothing in a fixture is expanded: prove it on the hardest case.
    workspace = tempfile.mkdtemp(prefix="eval-scaffold-expand-")
    try:
        source = os.path.join(workspace, "src")
        os.makedirs(source)
        with open(os.path.join(source, "x.sh"), "w", encoding="utf-8") as fh:
            fh.write('echo "$HOME" `whoami` $(id) \\n\n')
        rendered = build.render(os.path.relpath(source, build.REPO))
        out = os.path.join(workspace, "out")
        os.makedirs(out)
        script = os.path.join(workspace, "scaffold.sh")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write(rendered)
        subprocess.run(["bash", script], cwd=out, check=True)
        with open(os.path.join(out, "x.sh"), encoding="utf-8") as fh:
            check("shell syntax in a fixture is copied, not expanded",
                  fh.read() == 'echo "$HOME" `whoami` $(id) \\n\n')
    finally:
        shutil.rmtree(workspace, ignore_errors=True)

    print()
    if FAILURES:
        print("%d failure(s): %s" % (len(FAILURES), ", ".join(FAILURES)))
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
