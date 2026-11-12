#!/usr/bin/env bash
# GENERATED FILE -- DO NOT EDIT. Regenerate with: python3 tools/build_eval_scaffolds.py
# Recreates a git repository: fixtures/13-pipes-in-ci/base on main, then fixtures/13-pipes-in-ci/change in the eval's empty workspace.
set -euo pipefail
cat > 'CONTRIBUTING.md' <<'EVAL_FIXTURE_EOF'
# Contributing

CI runs the unit tests and checks that the README's examples still produce what they show. Run the same
commands as `.github/workflows/ci.yml` before opening a pull request.
EVAL_FIXTURE_EOF
cat > 'README.md' <<'EVAL_FIXTURE_EOF'
# textkit

Small text helpers with a command line.

```console
$ python3 -m textkit slugify "Release Notes"
release-notes
```
EVAL_FIXTURE_EOF
mkdir -p '.github/workflows'
cat > '.github/workflows/ci.yml' <<'EVAL_FIXTURE_EOF'
name: ci
on: [pull_request]
jobs:
  check:
    runs-on: ubuntu-24.04
    defaults:
      run:
        shell: bash
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: python3 -m unittest discover -s tests -t . -v 2>&1 | tee test.log
      - run: python3 scripts/check_readme.py || (echo "README examples are stale" && exit 1)
EVAL_FIXTURE_EOF
mkdir -p 'scripts'
cat > 'scripts/check_readme.py' <<'EVAL_FIXTURE_EOF'
"""Run every `$ python3 -m textkit ...` example in README.md and compare its output."""

import shlex
import subprocess
import sys


def main():
    with open("README.md", encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    stale = 0
    for i, line in enumerate(lines):
        if line.startswith("$ python3 -m textkit"):
            expected = lines[i + 1]
            got = subprocess.run([sys.executable] + shlex.split(line[2:])[1:], capture_output=True,
                                 text=True).stdout.strip()
            if got != expected:
                print("README line %d: expected %r, got %r" % (i + 1, expected, got))
                stale += 1
    print("%d stale example(s)" % stale)
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
EVAL_FIXTURE_EOF
mkdir -p 'tests'
: > 'tests/__init__.py'
mkdir -p 'tests'
cat > 'tests/test_slug.py' <<'EVAL_FIXTURE_EOF'
import unittest

from textkit.slug import slugify


class SlugifyTest(unittest.TestCase):
    def test_lowercases_and_joins_words(self):
        self.assertEqual(slugify("Release Notes"), "release-notes")

    def test_docstring_example(self):
        self.assertEqual(slugify("Hello,  World!"), "hello-world")
EVAL_FIXTURE_EOF
mkdir -p 'textkit'
: > 'textkit/__init__.py'
mkdir -p 'textkit'
cat > 'textkit/__main__.py' <<'EVAL_FIXTURE_EOF'
"""Command line: python3 -m textkit slugify <title>."""

import sys

from textkit.slug import slugify


def main(argv):
    if len(argv) != 2 or argv[0] != "slugify":
        print("usage: python3 -m textkit slugify <title>", file=sys.stderr)
        return 2
    print(slugify(argv[1]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
EVAL_FIXTURE_EOF
mkdir -p 'textkit'
cat > 'textkit/slug.py' <<'EVAL_FIXTURE_EOF'
"""Turn titles into URL slugs."""

import re


def slugify(title):
    """Lowercase `title`, replace each run of characters that are not letters or digits with a single
    dash, and strip dashes from both ends: slugify("Hello,  World!") == "hello-world".
    """
    return re.sub(r"[^a-z0-9]", "-", title.lower()).strip("-")
EVAL_FIXTURE_EOF
git init -q
git checkout -q -b main
git add -A
GIT_AUTHOR_NAME='Eval Fixture' GIT_AUTHOR_EMAIL='fixture@example.invalid' GIT_COMMITTER_NAME='Eval Fixture' GIT_COMMITTER_EMAIL='fixture@example.invalid' git -c commit.gpgsign=false commit -q -m 'Add textkit'
cat > 'CHANGELOG.md' <<'EVAL_FIXTURE_EOF'
# Changelog

## 0.3.0

- `python3 -m textkit slugify` prints a URL slug for a title.
EVAL_FIXTURE_EOF
git add -A
GIT_AUTHOR_NAME='Eval Fixture' GIT_AUTHOR_EMAIL='fixture@example.invalid' GIT_COMMITTER_NAME='Eval Fixture' GIT_COMMITTER_EMAIL='fixture@example.invalid' git -c commit.gpgsign=false commit -q -m 'Note the slugify command in the changelog'
