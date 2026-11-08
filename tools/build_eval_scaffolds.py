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

import base64
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
    "plugins/presentation/evals/behavior/workflow-slide-from-wordy-slide":
        ("fixtures/09-wordy-process-slide", ("README.md",)),
}

# eval case directory -> a git repository built from two snapshots, for skills that work on a change.
#
# `base` is committed on `main`. `change` holds only the files the change adds or replaces; it is
# laid over the base and committed on `branch`, which is left checked out -- or on `main`, as a
# later commit, when `branch` is None. Each is a fixture directory relative to the repository root.
GIT_SCAFFOLDS = {
    "plugins/verification/evals/behavior/verify-change-catches-unwired-expiry": {
        "base": "fixtures/07-unverified-change/base",
        "change": "fixtures/07-unverified-change/change",
        "branch": "reset-token-expiry",
        "messages": ("Add password-reset tokens", "Expire reset tokens after 30 minutes (#41)"),
    },
    "plugins/verification/evals/behavior/setup-verification-reports-codified-bug": {
        "base": "fixtures/08-codified-bug/base",
        "change": "fixtures/08-codified-bug/change",
        "branch": None,
        "messages": ("Add the tally expense log", "Test the CLI end to end"),
    },
}

# The commits are the fixture's, not anyone's. The identity is set through the environment,
# because GIT_AUTHOR_* and GIT_COMMITTER_* already set by the caller override `-c user.name`:
# with -c alone, the commits would carry the email of whoever runs the eval. Signing is off so no
# key is needed.
GIT = ("GIT_AUTHOR_NAME='Eval Fixture' GIT_AUTHOR_EMAIL='fixture@example.invalid' "
       "GIT_COMMITTER_NAME='Eval Fixture' GIT_COMMITTER_EMAIL='fixture@example.invalid' "
       "git -c commit.gpgsign=false")

MARKER = "EVAL_FIXTURE_EOF"
SKIP_DIRS = {"__pycache__", ".pytest_cache", ".git"}


def fixture_files(source, exclude=()):
    """Every file of the fixture but those in `exclude`, as (relative path, content), in a
    stable order. Content is text, or bytes for a file that is not UTF-8, such as a .pptx."""
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
            with open(path, "rb") as fh:
                data = fh.read()
            try:
                data = data.decode("utf-8")
            except UnicodeDecodeError:
                pass
            files.append((rel, data))
    return files


def _write(lines, source_rel, exclude=()):
    for rel, text in fixture_files(os.path.join(REPO, source_rel), exclude):
        if isinstance(text, bytes):
            # Binary: base64 in a quoted heredoc, wrapped so the script stays reviewable as text.
            if "'" in rel:
                raise SystemExit("%s/%s: a quote in a path would break the script" % (source_rel, rel))
            parent = os.path.dirname(rel)
            if parent:
                lines.append("mkdir -p '%s'" % parent)
            encoded = base64.b64encode(text).decode("ascii")
            lines.append("base64 -d > '%s' <<'%s'" % (rel, MARKER))
            lines.extend(encoded[i:i + 76] for i in range(0, len(encoded), 76))
            lines.append(MARKER)
            continue
        if MARKER in text:
            raise SystemExit("%s/%s contains the heredoc marker %s" % (source_rel, rel, MARKER))
        if text and not text.endswith("\n"):
            raise SystemExit("%s/%s does not end with a newline; a heredoc would add one"
                             % (source_rel, rel))
        if "'" in rel:
            raise SystemExit("%s/%s: a quote in a path would break the script" % (source_rel, rel))
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


def _header(what):
    return [
        "#!/usr/bin/env bash",
        "# GENERATED FILE -- DO NOT EDIT. Regenerate with: python3 tools/build_eval_scaffolds.py",
        "# Recreates %s in the eval's empty workspace." % what,
        "set -euo pipefail",
    ]


def render(source_rel, exclude=()):
    lines = _header(source_rel)
    _write(lines, source_rel, exclude)
    return "\n".join(lines) + "\n"


def render_git(spec):
    first, second = spec["messages"]
    for value in (first, second, spec["branch"] or ""):
        if "'" in value:
            raise SystemExit("%r: a quote would break the script" % value)
    lines = _header("a git repository: %s on main, then %s" % (spec["base"], spec["change"]))
    _write(lines, spec["base"])
    lines += ["git init -q", "git checkout -q -b main", "git add -A",
              "%s commit -q -m '%s'" % (GIT, first)]
    if spec["branch"]:
        lines.append("git checkout -q -b '%s'" % spec["branch"])
    _write(lines, spec["change"])
    lines += ["git add -A", "%s commit -q -m '%s'" % (GIT, second)]
    return "\n".join(lines) + "\n"


def scripts():
    """Every case directory with the scaffold.sh it should have."""
    found = {case: render(source, exclude) for case, (source, exclude) in SCAFFOLDS.items()}
    found.update({case: render_git(spec) for case, spec in GIT_SCAFFOLDS.items()})
    return sorted(found.items())


def main(argv):
    check = "--check" in argv
    stale = []
    for case_rel, wanted in scripts():
        target = os.path.join(REPO, case_rel, "scaffold.sh")
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
