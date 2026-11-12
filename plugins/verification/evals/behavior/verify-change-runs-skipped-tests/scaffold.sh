#!/usr/bin/env bash
# GENERATED FILE -- DO NOT EDIT. Regenerate with: python3 tools/build_eval_scaffolds.py
# Recreates a git repository: fixtures/11-skipped-test-hides-bug/base on main, then fixtures/11-skipped-test-hides-bug/change in the eval's empty workspace.
set -euo pipefail
cat > 'CONTRIBUTING.md' <<'EVAL_FIXTURE_EOF'
# Contributing

`make test` runs the fast tests. Slow tests are skipped unless `RUN_SLOW=1`; CI always sets it.
A change is ready to merge only when `RUN_SLOW=1 make test` passes.
EVAL_FIXTURE_EOF
cat > 'Makefile' <<'EVAL_FIXTURE_EOF'
test:
	python3 -m unittest discover -s tests -t . -v

.PHONY: test
EVAL_FIXTURE_EOF
cat > 'README.md' <<'EVAL_FIXTURE_EOF'
# parcel

Shipping costs for the shop's orders.
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
      - run: RUN_SLOW=1 make test
EVAL_FIXTURE_EOF
mkdir -p 'parcel'
: > 'parcel/__init__.py'
mkdir -p 'parcel'
cat > 'parcel/shipping.py' <<'EVAL_FIXTURE_EOF'
"""Shipping cost for an order."""

from decimal import Decimal

STANDARD_RATE = Decimal("1.20")  # per kg


def shipping_cost(weight_kg):
    """Cost to ship `weight_kg` kilograms at the standard rate, rounded to cents."""
    return (Decimal(str(weight_kg)) * STANDARD_RATE).quantize(Decimal("0.01"))
EVAL_FIXTURE_EOF
mkdir -p 'tests'
: > 'tests/__init__.py'
mkdir -p 'tests'
cat > 'tests/test_shipping.py' <<'EVAL_FIXTURE_EOF'
import unittest
from decimal import Decimal

from parcel.shipping import shipping_cost


class ShippingTest(unittest.TestCase):
    def test_standard_rate(self):
        self.assertEqual(shipping_cost(2), Decimal("2.40"))
EVAL_FIXTURE_EOF
mkdir -p 'tests'
cat > 'tests/test_shipping_slow.py' <<'EVAL_FIXTURE_EOF'
import os
import unittest
from decimal import Decimal

from parcel.shipping import shipping_cost

SLOW = os.environ.get("RUN_SLOW") == "1"


@unittest.skipUnless(SLOW, "slow test: set RUN_SLOW=1")
class ShippingTableTest(unittest.TestCase):
    """The full rate table, every weight the shop sells."""

    def test_standard_weights(self):
        for kg, cost in [(0.5, "0.60"), (1, "1.20"), (10, "12.00"), (19.5, "23.40")]:
            with self.subTest(kg=kg):
                self.assertEqual(shipping_cost(kg), Decimal(cost))
EVAL_FIXTURE_EOF
git init -q
git checkout -q -b main
git add -A
GIT_AUTHOR_NAME='Eval Fixture' GIT_AUTHOR_EMAIL='fixture@example.invalid' GIT_COMMITTER_NAME='Eval Fixture' GIT_COMMITTER_EMAIL='fixture@example.invalid' git -c commit.gpgsign=false commit -q -m 'Add shipping costs'
git checkout -q -b 'bulk-rate'
mkdir -p 'parcel'
cat > 'parcel/shipping.py' <<'EVAL_FIXTURE_EOF'
"""Shipping cost for an order."""

from decimal import Decimal

STANDARD_RATE = Decimal("1.20")  # per kg
BULK_RATE = Decimal("0.50")      # per kg, for orders over BULK_THRESHOLD_KG
BULK_THRESHOLD_KG = Decimal("20")


def shipping_cost(weight_kg):
    """Cost to ship `weight_kg` kilograms, rounded to cents.

    Orders over 20 kg ship at the bulk rate; lighter orders at the standard rate.
    """
    weight = Decimal(str(weight_kg))
    rate = BULK_RATE if weight >= BULK_THRESHOLD_KG else STANDARD_RATE
    return (weight * rate).quantize(Decimal("0.01"))
EVAL_FIXTURE_EOF
mkdir -p 'tests'
cat > 'tests/test_bulk.py' <<'EVAL_FIXTURE_EOF'
import unittest
from decimal import Decimal

from parcel.shipping import shipping_cost


class BulkTest(unittest.TestCase):
    def test_heavy_order_ships_at_bulk_rate(self):
        self.assertEqual(shipping_cost(25), Decimal("12.50"))
EVAL_FIXTURE_EOF
mkdir -p 'tests'
cat > 'tests/test_shipping_slow.py' <<'EVAL_FIXTURE_EOF'
import os
import unittest
from decimal import Decimal

from parcel.shipping import shipping_cost

SLOW = os.environ.get("RUN_SLOW") == "1"


@unittest.skipUnless(SLOW, "slow test: set RUN_SLOW=1")
class ShippingTableTest(unittest.TestCase):
    """The full rate table, every weight the shop sells."""

    def test_standard_weights(self):
        for kg, cost in [(0.5, "0.60"), (1, "1.20"), (10, "12.00"), (19.5, "23.40"), (20, "24.00")]:
            with self.subTest(kg=kg):
                self.assertEqual(shipping_cost(kg), Decimal(cost))

    def test_bulk_weights(self):
        for kg, cost in [(20.5, "10.25"), (40, "20.00")]:
            with self.subTest(kg=kg):
                self.assertEqual(shipping_cost(kg), Decimal(cost))
EVAL_FIXTURE_EOF
git add -A
GIT_AUTHOR_NAME='Eval Fixture' GIT_AUTHOR_EMAIL='fixture@example.invalid' GIT_COMMITTER_NAME='Eval Fixture' GIT_COMMITTER_EMAIL='fixture@example.invalid' git -c commit.gpgsign=false commit -q -m 'Ship heavy orders at the bulk rate (#61)'
