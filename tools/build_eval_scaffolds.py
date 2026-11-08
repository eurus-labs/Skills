#!/usr/bin/env python3
"""Write each behavior eval's scaffold.sh from the fixture it runs on.

A `claude plugin eval` case starts in an empty workspace, and its `scaffold.sh` is what
puts a fixture there. Copying the fixture into the script by hand would let the two drift:
a fixture fixed or extended later would leave the eval measuring the old one. So the
scripts are generated from the fixture directories, and tools/test_eval_scaffolds.py fails
when a committed script no longer reproduces its fixture byte for byte.

    python3 tools/build_eval_scaffolds.py           # (re)write every scaffold.sh
    python3 tools/build_eval_scaffolds.py --check   # exit 1 if any is out of date

Each file is written with a quoted heredoc, so nothing in it is expanded, and the script
is plain text a reviewer can read.
"""

import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# eval case directory -> (fixture directory, files left out), relative to the repository root.
#
# A scenario README under fixtures/ explains what is planted and how an agent fails -- an
# answer key for a human running a demo. Copied into the workspace it would hand the agent
# under test the answer, in the no-plugin arm as much as the plugin arm, so it is left out.
# The contract the agent must work from is in the code's own docstrings.
SCAFFOLDS = {
    "plugins/testing/evals/behavior/write-tests-reports-contract-bugs":
        ("fixtures/01-buggy-code-no-tests", ("README.md",)),
    "plugins/testing/evals/behavior/debug-failing-test-blames-the-test":
        ("fixtures/02-wrong-test", ("README.md",)),
    "plugins/testing/evals/behavior/review-tests-finds-weak-suite":
        ("fixtures/03-weak-suite", ("README.md",)),
    "plugins/docs/evals/behavior/architecture-overview-of-layered-repo":
        ("tests/contracts/layered-repo", ()),
}

MARKER = "EVAL_FIXTURE_EOF"
SKIP_DIRS = {"__pycache__", ".pytest_cache", ".git"}


def fixture_files(source, exclude=()):
    """Every file of the fixture but those in `exclude`, as (relative path, text), in a
    stable order."""
    files = []
    for dirpath, dirnames, filenames in os.walk(source):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            if name.endswith(".pyc"):
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, source).replace(os.sep, "/")
            if rel in exclude:
                continue
            with open(path, encoding="utf-8") as fh:
                files.append((rel, fh.read()))
    return files


def render(source_rel, exclude=()):
    lines = [
        "#!/usr/bin/env bash",
        "# GENERATED FILE -- DO NOT EDIT. Regenerate with: python3 tools/build_eval_scaffolds.py",
        "# Recreates %s in the eval's empty workspace." % source_rel,
        "set -euo pipefail",
    ]
    for rel, text in fixture_files(os.path.join(REPO, source_rel), exclude):
        if MARKER in text:
            raise SystemExit("%s/%s contains the heredoc marker %s" % (source_rel, rel, MARKER))
        if text and not text.endswith("\n"):
            raise SystemExit("%s/%s does not end with a newline; a heredoc would add one"
                             % (source_rel, rel))
        parent = os.path.dirname(rel)
        if parent:
            lines.append("mkdir -p '%s'" % parent)
        if not text:
            # A heredoc always ends in a newline, so an empty file needs its own form.
            lines.append(": > '%s'" % rel)
            continue
        lines.append("cat > '%s' <<'%s'" % (rel, MARKER))
        lines.append(text.rstrip("\n"))
        lines.append(MARKER)
    return "\n".join(lines) + "\n"


def main(argv):
    check = "--check" in argv
    stale = []
    for case_rel, (source_rel, exclude) in sorted(SCAFFOLDS.items()):
        target = os.path.join(REPO, case_rel, "scaffold.sh")
        wanted = render(source_rel, exclude)
        current = None
        if os.path.isfile(target):
            with open(target, encoding="utf-8") as fh:
                current = fh.read()
        if current == wanted:
            continue
        if check:
            stale.append(case_rel)
            continue
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as fh:
            fh.write(wanted)
        os.chmod(target, 0o755)
        print("wrote %s" % os.path.relpath(target, REPO))
    if stale:
        for case_rel in stale:
            print("stale: %s/scaffold.sh -- run python3 tools/build_eval_scaffolds.py" % case_rel)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
