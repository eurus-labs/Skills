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
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for name in filenames:
            path = os.path.join(dirpath, name)
            with open(path, "rb") as fh:
                found[os.path.relpath(path, root).replace(os.sep, "/")] = fh.read()
    return found


def as_bytes(data):
    return data if isinstance(data, bytes) else data.encode("utf-8")


def scenario_readme(source_rel):
    """The scenario README above a fixture, which states its answer, as bytes, or None."""
    parts = source_rel.split("/")
    if parts[0] != "fixtures" or len(parts) < 2:
        return None
    path = os.path.join(REPO, "fixtures", parts[1], "README.md")
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as fh:
        return fh.read()


def git(workspace, *args):
    return subprocess.run(["git", *args], cwd=workspace, capture_output=True,
                          text=True).stdout.strip()


def check_git_case(case_rel, spec):
    script = os.path.join(REPO, case_rel, "scaffold.sh")
    if not os.path.isfile(script):
        check("%s has a scaffold.sh" % case_rel, False)
        return
    workspace = tempfile.mkdtemp(prefix="eval-scaffold-git-")
    try:
        # Whoever runs the eval may have an identity in the environment, which outranks
        # `git -c user.*`. The commits must still be the fixture's.
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        env.update(HOME=workspace, GIT_CONFIG_NOSYSTEM="1",
                   GIT_AUTHOR_NAME="Someone Else", GIT_AUTHOR_EMAIL="someone@example.com",
                   GIT_COMMITTER_NAME="Someone Else", GIT_COMMITTER_EMAIL="someone@example.com")
        run = subprocess.run(["bash", script], cwd=workspace, capture_output=True, text=True,
                             env=env)
        check("%s scaffold runs" % case_rel, run.returncode == 0, run.stderr)
        base = dict((rel, as_bytes(data)) for rel, data in
                    build.fixture_files(os.path.join(REPO, spec["base"])))
        change = dict((rel, as_bytes(data)) for rel, data in
                      build.fixture_files(os.path.join(REPO, spec["change"])))
        expected = dict(base, **change)
        got = tree(workspace)
        check("%s recreates base + change exactly" % case_rel, got == expected,
              "missing %s, extra %s, differing %s" % (
                  sorted(set(expected) - set(got)), sorted(set(got) - set(expected)),
                  sorted(k for k in set(got) & set(expected) if got[k] != expected[k])))
        readme = scenario_readme(spec["base"])
        check("%s carries no scenario README, which states the answer" % case_rel,
              readme is None or readme not in got.values())
        check("%s leaves a clean tree" % case_rel, git(workspace, "status", "--porcelain") == "")
        head = spec["branch"] or "main"
        check("%s checks out %s" % (case_rel, head),
              git(workspace, "rev-parse", "--abbrev-ref", "HEAD") == head)
        if spec["branch"]:
            changed = git(workspace, "diff", "--name-only", "main...HEAD").splitlines()
            label = "main...%s" % spec["branch"]
        else:
            changed = git(workspace, "diff", "--name-only", "HEAD~1", "HEAD").splitlines()
            label = "the last commit"
        check("%s: %s changes exactly the change's files" % (case_rel, label),
              sorted(changed) == sorted(change), "got %s" % changed)
        authors = set(git(workspace, "log", "--all",
                          "--format=%an <%ae>%n%cn <%ce>").splitlines())
        check("%s commits as the fixture, not the user" % case_rel,
              authors == {"Eval Fixture <fixture@example.invalid>"}, "got %s" % authors)
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


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
            expected = {rel: as_bytes(data) for rel, data in
                        build.fixture_files(os.path.join(REPO, source_rel), exclude)}
            got = tree(workspace)
            readme = scenario_readme(source_rel)
            check("%s carries no scenario README, which states the answer" % case_rel,
                  readme is None or readme not in got.values())
            check("%s recreates %s exactly" % (case_rel, source_rel), got == expected,
                  "missing %s, extra %s, differing %s" % (
                      sorted(set(expected) - set(got)), sorted(set(got) - set(expected)),
                      sorted(k for k in set(got) & set(expected) if got[k] != expected[k])))
        finally:
            shutil.rmtree(workspace, ignore_errors=True)

    if shutil.which("git") is None:
        print("skip: no git to build the git scaffolds")
    else:
        for case_rel, spec in sorted(build.GIT_SCAFFOLDS.items()):
            check_git_case(case_rel, spec)

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

    # A binary file goes through base64; prove the round trip on bytes no text heredoc could carry.
    workspace = tempfile.mkdtemp(prefix="eval-scaffold-binary-")
    try:
        source = os.path.join(workspace, "src")
        os.makedirs(os.path.join(source, "deep"))
        blob = bytes(range(256)) * 3 + b"EVAL_FIXTURE_EOF\n\x00"
        with open(os.path.join(source, "deep", "blob.bin"), "wb") as fh:
            fh.write(blob)
        out = os.path.join(workspace, "out")
        os.makedirs(out)
        script = os.path.join(workspace, "scaffold.sh")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write(build.render(os.path.relpath(source, build.REPO)))
        subprocess.run(["bash", script], cwd=out, check=True)
        with open(os.path.join(out, "deep", "blob.bin"), "rb") as fh:
            check("a binary fixture file is recreated byte for byte", fh.read() == blob)
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
