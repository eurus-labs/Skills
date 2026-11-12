#!/usr/bin/env bash
# GENERATED FILE -- DO NOT EDIT. Regenerate with: python3 tools/build_eval_scaffolds.py
# Recreates a git repository: fixtures/14-local-verify-skill/base on main, then fixtures/14-local-verify-skill/change in the eval's empty workspace.
set -euo pipefail
cat > 'Makefile' <<'EVAL_FIXTURE_EOF'
test:
	python3 -m unittest discover -s tests -t . -v

.PHONY: test
EVAL_FIXTURE_EOF
cat > 'README.md' <<'EVAL_FIXTURE_EOF'
# orders

Order totals for the shop.
EVAL_FIXTURE_EOF
mkdir -p '.claude/skills/verify-orders'
cat > '.claude/skills/verify-orders/SKILL.md' <<'EVAL_FIXTURE_EOF'
---
name: verify-orders
description: Verify behavior of orders after a change or for a regression sweep — map the diff to feature
  areas, run a fresh build, run the unit tests, capture evidence, and review it against the goal. Use after
  implementing or fixing anything in orders.
---

# Verify orders

## Checks
| Check | Kind | Command | Applies when | Required | Passes when |
| ----- | ---- | ------- | ------------ | -------- | ----------- |
| unit | tests | `make test` | always | yes | exit 0 and at least one test collected |

## Procedure
1. Run `make test`.
2. Review the result against the goal.
EVAL_FIXTURE_EOF
mkdir -p 'orders'
: > 'orders/__init__.py'
mkdir -p 'orders'
cat > 'orders/total.py' <<'EVAL_FIXTURE_EOF'
"""Order totals."""

from decimal import Decimal


def total(prices):
    """Sum of `prices`, rounded to cents."""
    return sum((Decimal(str(p)) for p in prices), Decimal("0")).quantize(Decimal("0.01"))
EVAL_FIXTURE_EOF
mkdir -p 'tests'
: > 'tests/__init__.py'
mkdir -p 'tests'
cat > 'tests/test_total.py' <<'EVAL_FIXTURE_EOF'
import unittest
from decimal import Decimal

from orders.total import total


class TotalTest(unittest.TestCase):
    def test_sum(self):
        self.assertEqual(total([1, "2.50"]), Decimal("3.50"))
EVAL_FIXTURE_EOF
git init -q
git checkout -q -b main
git add -A
GIT_AUTHOR_NAME='Eval Fixture' GIT_AUTHOR_EMAIL='fixture@example.invalid' GIT_COMMITTER_NAME='Eval Fixture' GIT_COMMITTER_EMAIL='fixture@example.invalid' git -c commit.gpgsign=false commit -q -m 'Add order totals and their verify skill'
git checkout -q -b 'fix-rounding'
mkdir -p 'orders'
cat > 'orders/total.py' <<'EVAL_FIXTURE_EOF'
"""Order totals."""

from decimal import ROUND_HALF_UP, Decimal


def total(prices):
    """Sum of `prices`, rounded half up to cents."""
    amount = sum((Decimal(str(p)) for p in prices), Decimal("0"))
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
EVAL_FIXTURE_EOF
git add -A
GIT_AUTHOR_NAME='Eval Fixture' GIT_AUTHOR_EMAIL='fixture@example.invalid' GIT_COMMITTER_NAME='Eval Fixture' GIT_COMMITTER_EMAIL='fixture@example.invalid' git -c commit.gpgsign=false commit -q -m 'Round totals half up (#31)'
