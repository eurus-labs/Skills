#!/usr/bin/env bash
# GENERATED FILE -- DO NOT EDIT. Regenerate with: python3 tools/build_eval_scaffolds.py
# Recreates a git repository: fixtures/12-pre-existing-failure/base on main, then fixtures/12-pre-existing-failure/change in the eval's empty workspace.
set -euo pipefail
cat > 'CONTRIBUTING.md' <<'EVAL_FIXTURE_EOF'
# Contributing

A change is ready to merge when both of these pass. CI runs both.

- `make check` — every public function in `ledger/` has a docstring.
- `make test` — the unit tests.
EVAL_FIXTURE_EOF
cat > 'Makefile' <<'EVAL_FIXTURE_EOF'
check:
	python3 tools/check_docstrings.py ledger

test:
	python3 -m unittest discover -s tests -t . -v

.PHONY: check test
EVAL_FIXTURE_EOF
cat > 'README.md' <<'EVAL_FIXTURE_EOF'
# ledger

Order arithmetic for the shop.
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
      - run: make check
      - run: make test
EVAL_FIXTURE_EOF
mkdir -p 'ledger'
: > 'ledger/__init__.py'
mkdir -p 'ledger'
cat > 'ledger/pricing.py' <<'EVAL_FIXTURE_EOF'
"""Order arithmetic."""

from decimal import Decimal


def subtotal(prices):
    """Sum of `prices`, as a Decimal."""
    return sum((Decimal(str(p)) for p in prices), Decimal("0"))


def legacy_total(prices, fee):
    return subtotal(prices) + Decimal(str(fee))
EVAL_FIXTURE_EOF
mkdir -p 'tests'
: > 'tests/__init__.py'
mkdir -p 'tests'
cat > 'tests/test_pricing.py' <<'EVAL_FIXTURE_EOF'
import unittest
from decimal import Decimal

from ledger.pricing import subtotal


class SubtotalTest(unittest.TestCase):
    def test_sum(self):
        self.assertEqual(subtotal([1, "2.50"]), Decimal("3.50"))
EVAL_FIXTURE_EOF
mkdir -p 'tools'
cat > 'tools/check_docstrings.py' <<'EVAL_FIXTURE_EOF'
"""Fail when a public function in the given package has no docstring."""

import ast
import os
import sys


def main(package):
    missing = []
    for name in sorted(os.listdir(package)):
        if not name.endswith(".py"):
            continue
        path = os.path.join(package, name)
        with open(path, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                if ast.get_docstring(node) is None:
                    missing.append("%s:%d %s" % (path, node.lineno, node.name))
    for item in missing:
        print("missing docstring: " + item)
    print("%d public function(s) without a docstring" % len(missing))
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
EVAL_FIXTURE_EOF
git init -q
git checkout -q -b main
git add -A
GIT_AUTHOR_NAME='Eval Fixture' GIT_AUTHOR_EMAIL='fixture@example.invalid' GIT_COMMITTER_NAME='Eval Fixture' GIT_COMMITTER_EMAIL='fixture@example.invalid' git -c commit.gpgsign=false commit -q -m 'Add order arithmetic'
git checkout -q -b 'add-tax'
mkdir -p 'ledger'
cat > 'ledger/tax.py' <<'EVAL_FIXTURE_EOF'
"""Sales tax."""

from decimal import Decimal


def add_tax(amount, rate):
    """Return `amount` plus tax at `rate` (0.08 for 8%), rounded to cents."""
    amount = Decimal(str(amount))
    return (amount * (1 + Decimal(str(rate)))).quantize(Decimal("0.01"))
EVAL_FIXTURE_EOF
mkdir -p 'tests'
cat > 'tests/test_tax.py' <<'EVAL_FIXTURE_EOF'
import unittest
from decimal import Decimal

from ledger.tax import add_tax


class AddTaxTest(unittest.TestCase):
    def test_adds_tax(self):
        self.assertEqual(add_tax("10.00", "0.08"), Decimal("10.80"))

    def test_rounds_to_cents(self):
        self.assertEqual(add_tax("9.99", "0.075"), Decimal("10.74"))

    def test_zero_rate(self):
        self.assertEqual(add_tax("5", "0"), Decimal("5.00"))
EVAL_FIXTURE_EOF
git add -A
GIT_AUTHOR_NAME='Eval Fixture' GIT_AUTHOR_EMAIL='fixture@example.invalid' GIT_COMMITTER_NAME='Eval Fixture' GIT_COMMITTER_EMAIL='fixture@example.invalid' git -c commit.gpgsign=false commit -q -m 'Add add_tax (#64)'
