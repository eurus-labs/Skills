#!/usr/bin/env bash
# GENERATED FILE -- DO NOT EDIT. Regenerate with: python3 tools/build_eval_scaffolds.py
# Recreates fixtures/02-wrong-test in the eval's empty workspace.
set -euo pipefail
cat > 'pricing.py' <<'EVAL_FIXTURE_EOF'
"""Order pricing.

FIXTURE -- the code in this file is CORRECT. The failing test is the defect.

Pricing rules, in order:
  1. Sum the line items.
  2. Apply the percentage discount to that subtotal.
  3. Apply tax to the discounted amount.
  4. Add shipping, which is never taxed and never discounted.

Tax applies *after* the discount. A customer does not pay tax on money they did not
spend. This ordering is deliberate and is what the tests must assert.
"""

from decimal import Decimal, ROUND_HALF_UP

TAX_RATE = Decimal("0.10")


def _money(value):
    """Round to cents, half away from zero, the way an invoice does."""
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def subtotal(items):
    """Sum `items`, each a (unit_price, quantity) pair."""
    total = sum(Decimal(str(price)) * quantity for price, quantity in items)
    return _money(total)


def total(items, discount_percent=0, shipping=0):
    """Return the amount payable.

    Discount is applied to the subtotal, tax to the discounted amount, and shipping is
    added last, untaxed.

    Raises:
        ValueError: if `discount_percent` is outside 0-100.
    """
    if not 0 <= discount_percent <= 100:
        raise ValueError("discount_percent must be between 0 and 100")

    base = subtotal(items)
    discounted = base * (Decimal(100 - discount_percent) / Decimal(100))
    taxed = discounted * (Decimal(1) + TAX_RATE)
    return _money(taxed + Decimal(str(shipping)))
EVAL_FIXTURE_EOF
cat > 'pyproject.toml' <<'EVAL_FIXTURE_EOF'
[project]
name = "fixture-pricing"
version = "0.0.0"
description = "Fixture for the debug-failing-test skill: correct code, one wrong test."

[dependency-groups]
dev = ["pytest"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
EVAL_FIXTURE_EOF
mkdir -p 'tests'
cat > 'tests/test_pricing.py' <<'EVAL_FIXTURE_EOF'
"""FIXTURE -- one of these tests asserts the wrong thing. The code is correct."""

from decimal import Decimal

import pytest

from pricing import subtotal, total


def test_subtotal_sums_line_items():
    assert subtotal([("10.00", 2), ("5.50", 1)]) == Decimal("25.50")


def test_total_adds_tax():
    # 100.00 + 10% tax
    assert total([("100.00", 1)]) == Decimal("110.00")


def test_total_applies_discount():
    # 100.00 - 20% = 80.00, + 10% tax = 88.00
    assert total([("100.00", 1)], discount_percent=20) == Decimal("88.00")


def test_discounted_order_with_shipping():
    # 100.00 - 20% = 80.00, + 7.99 shipping = 87.99, + 10% tax = 96.79
    assert total(
        [("100.00", 1)], discount_percent=20, shipping="7.99"
    ) == Decimal("96.79")


def test_rejects_discount_over_100():
    with pytest.raises(ValueError):
        total([("10.00", 1)], discount_percent=101)
EVAL_FIXTURE_EOF
