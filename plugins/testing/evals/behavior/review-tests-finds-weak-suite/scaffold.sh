#!/usr/bin/env bash
# GENERATED FILE -- DO NOT EDIT. Regenerate with: python3 tools/build_eval_scaffolds.py
# Recreates fixtures/03-weak-suite in the eval's empty workspace.
set -euo pipefail
cat > 'cart.py' <<'EVAL_FIXTURE_EOF'
"""Shopping cart.

FIXTURE -- this implementation is correct. The *test suite* is the defect.
"""


class Cart:
    def __init__(self):
        self._lines = {}

    def add(self, sku, quantity=1):
        """Add `quantity` of `sku`. Returns the new quantity for that SKU."""
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        self._lines[sku] = self._lines.get(sku, 0) + quantity
        return self._lines[sku]

    def remove(self, sku):
        """Remove `sku` entirely. Returns True if it was present, False otherwise."""
        return self._lines.pop(sku, None) is not None

    def count(self):
        """Total number of units across all lines."""
        return sum(self._lines.values())

    def apply_coupon(self, code, rates):
        """Return the discount rate for `code`, or 0.0 if it is unknown or expired.

        `rates` maps a coupon code to a (rate, active) pair.
        """
        rate, active = rates.get(code, (0.0, False))
        return rate if active else 0.0
EVAL_FIXTURE_EOF
cat > 'pyproject.toml' <<'EVAL_FIXTURE_EOF'
[project]
name = "fixture-cart"
version = "0.0.0"
description = "Fixture for the review-tests skill: a green suite that catches nothing."

[dependency-groups]
dev = ["pytest"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
EVAL_FIXTURE_EOF
mkdir -p 'tests'
cat > 'tests/test_cart.py' <<'EVAL_FIXTURE_EOF'
"""FIXTURE -- every test here passes. Almost none of them would catch a regression."""

from unittest.mock import patch

from cart import Cart

# Shared across tests. Whether a test passes depends on which tests ran before it.
CART = Cart()


def test_add():
    result = CART.add("widget")
    assert result is not None


def test_add_multiple():
    CART.add("widget", 3)
    assert CART.count() > 0


def test_remove_returns_something():
    CART.add("gadget")
    assert CART.remove("gadget") in (True, False)


def test_count_is_an_int():
    assert isinstance(CART.count(), int)


def test_apply_coupon():
    with patch.object(Cart, "apply_coupon", return_value=0.25):
        cart = Cart()
        assert cart.apply_coupon("SAVE25", {}) == 0.25


def test_add_calls_through():
    with patch.object(Cart, "add") as mocked:
        mocked.return_value = 1
        cart = Cart()
        cart.add("thing")
        assert mocked.call_count == 1


def test_cart_state_after_earlier_tests():
    # Depends on test_add and test_add_multiple having run first, in order.
    assert CART.count() == 4


def test_removing_absent_item():
    Cart().remove("never-added")
EVAL_FIXTURE_EOF
