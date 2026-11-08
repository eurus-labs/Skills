#!/usr/bin/env bash
# GENERATED FILE -- DO NOT EDIT. Regenerate with: python3 tools/build_eval_scaffolds.py
# Recreates a git repository: fixtures/08-codified-bug/base on main, then fixtures/08-codified-bug/change in the eval's empty workspace.
set -euo pipefail
cat > 'CONTRIBUTING.md' <<'EVAL_FIXTURE_EOF'
# Contributing

Run `make lint` and `make test` before opening a pull request; CI runs both and blocks the merge
on either.
EVAL_FIXTURE_EOF
cat > 'Makefile' <<'EVAL_FIXTURE_EOF'
lint:
	python3 -m pyflakes tally tests

test:
	python3 -m unittest discover -s tests -t . -v

.PHONY: lint test
EVAL_FIXTURE_EOF
cat > 'README.md' <<'EVAL_FIXTURE_EOF'
# tally

A tiny expense log for the command line. Entries are stored in `tally.json` in the current
directory, or in the file `TALLY_FILE` names.

```console
$ python3 -m tally add 12.50 food
added 12.50 food
$ python3 -m tally total
12.50
$ python3 -m tally total --category rent
0
$ python3 -m tally undo
removed 12.50 food
```

`undo` removes the most recent entry, so a typo can be taken back straight away.
EVAL_FIXTURE_EOF
cat > 'pyproject.toml' <<'EVAL_FIXTURE_EOF'
[project]
name = "tally"
version = "0.2.0"
description = "A tiny expense log for the command line"
requires-python = ">=3.9"
EVAL_FIXTURE_EOF
mkdir -p '.github/workflows'
cat > '.github/workflows/ci.yml' <<'EVAL_FIXTURE_EOF'
name: ci
on: [pull_request]
jobs:
  check:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: python3 -m pip install pyflakes
      - run: make lint
      - run: make test
EVAL_FIXTURE_EOF
mkdir -p 'tally'
: > 'tally/__init__.py'
mkdir -p 'tally'
cat > 'tally/__main__.py' <<'EVAL_FIXTURE_EOF'
"""Command line: python3 -m tally {add,total,undo}."""

import argparse
import os
import sys

from tally import core


def main(argv=None):
    parser = argparse.ArgumentParser(prog="tally", description="A tiny expense log.")
    commands = parser.add_subparsers(dest="command", required=True)
    add = commands.add_parser("add", help="record an expense")
    add.add_argument("amount")
    add.add_argument("category")
    total = commands.add_parser("total", help="print the sum of the expenses")
    total.add_argument("--category")
    commands.add_parser("undo", help="remove the most recent entry")
    args = parser.parse_args(argv)

    path = os.environ.get("TALLY_FILE", "tally.json")
    entries = core.load(path)
    if args.command == "add":
        try:
            entry = core.add(entries, args.amount, args.category)
        except ValueError as exc:
            print("error: %s" % exc, file=sys.stderr)
            return 2
        core.save(path, entries)
        print("added %s %s" % (entry["amount"], entry["category"]))
    elif args.command == "total":
        print(core.total(entries, args.category))
    else:
        entry = core.undo(entries)
        if entry is None:
            print("nothing to undo")
            return 0
        core.save(path, entries)
        print("removed %s %s" % (entry["amount"], entry["category"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
EVAL_FIXTURE_EOF
mkdir -p 'tally'
cat > 'tally/core.py' <<'EVAL_FIXTURE_EOF'
"""The expense log behind the tally CLI.

Entries are kept in the order they were added, oldest first.
"""

import json
import os
from decimal import Decimal


def load(path):
    """Return the entries stored in `path`; a file that does not exist is an empty log."""
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save(path, entries):
    """Write `entries` to `path`."""
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(entries, fh, indent=2)


def add(entries, amount, category):
    """Append an entry and return it. Raises ValueError unless `amount` is positive."""
    value = Decimal(amount)
    if value <= 0:
        raise ValueError("amount must be positive")
    entry = {"amount": str(value), "category": category}
    entries.append(entry)
    return entry


def total(entries, category=None):
    """Sum of the amounts, for one category when `category` is given."""
    return sum((Decimal(e["amount"]) for e in entries if category in (None, e["category"])),
               Decimal("0"))


def undo(entries):
    """Remove the most recent entry and return it; return None when the log is empty."""
    if not entries:
        return None
    return entries.pop(0)
EVAL_FIXTURE_EOF
mkdir -p 'tests'
: > 'tests/__init__.py'
mkdir -p 'tests'
cat > 'tests/test_core.py' <<'EVAL_FIXTURE_EOF'
import unittest
from decimal import Decimal

from tally import core


class CoreTest(unittest.TestCase):
    def test_add_appends(self):
        entries = []
        core.add(entries, "12.50", "food")
        self.assertEqual(entries, [{"amount": "12.50", "category": "food"}])

    def test_add_rejects_non_positive(self):
        with self.assertRaises(ValueError):
            core.add([], "0", "food")

    def test_total_by_category(self):
        entries = []
        core.add(entries, "5", "food")
        core.add(entries, "700", "rent")
        core.add(entries, "2.25", "food")
        self.assertEqual(core.total(entries), Decimal("707.25"))
        self.assertEqual(core.total(entries, "food"), Decimal("7.25"))

    def test_undo_removes_an_entry(self):
        entries = []
        core.add(entries, "5", "food")
        core.add(entries, "700", "rent")
        removed = core.undo(entries)
        self.assertEqual(removed["category"], "food")
        self.assertEqual(len(entries), 1)

    def test_undo_on_empty_log(self):
        self.assertIsNone(core.undo([]))
EVAL_FIXTURE_EOF
git init -q
git checkout -q -b main
git add -A
GIT_AUTHOR_NAME='Eval Fixture' GIT_AUTHOR_EMAIL='fixture@example.invalid' GIT_COMMITTER_NAME='Eval Fixture' GIT_COMMITTER_EMAIL='fixture@example.invalid' git -c commit.gpgsign=false commit -q -m 'Add the tally expense log'
mkdir -p 'tests'
cat > 'tests/test_cli.py' <<'EVAL_FIXTURE_EOF'
import os
import subprocess
import sys
import tempfile
import unittest


def tally(*args, path):
    env = dict(os.environ, TALLY_FILE=path)
    return subprocess.run([sys.executable, "-m", "tally", *args], env=env,
                          capture_output=True, text=True)


class CliTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "tally.json")

    def tearDown(self):
        self.dir.cleanup()

    def test_add_then_total(self):
        self.assertEqual(tally("add", "12.50", "food", path=self.path).stdout, "added 12.50 food\n")
        self.assertEqual(tally("total", path=self.path).stdout, "12.50\n")

    def test_rejects_a_negative_amount(self):
        result = tally("add", "-3", "food", path=self.path)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(os.path.exists(self.path))
EVAL_FIXTURE_EOF
git add -A
GIT_AUTHOR_NAME='Eval Fixture' GIT_AUTHOR_EMAIL='fixture@example.invalid' GIT_COMMITTER_NAME='Eval Fixture' GIT_COMMITTER_EMAIL='fixture@example.invalid' git -c commit.gpgsign=false commit -q -m 'Test the CLI end to end'
