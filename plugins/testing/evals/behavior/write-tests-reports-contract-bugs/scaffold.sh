#!/usr/bin/env bash
# GENERATED FILE -- DO NOT EDIT. Regenerate with: python3 tools/build_eval_scaffolds.py
# Recreates fixtures/01-buggy-code-no-tests in the eval's empty workspace.
set -euo pipefail
cat > 'inventory.py' <<'EVAL_FIXTURE_EOF'
"""Inventory tracking for a small warehouse.

INTENTIONALLY DEFECTIVE -- this is a test fixture. Do not copy.

Every docstring below states the intended contract. Some implementations do not honour
it. The docstrings are the specification; where the code disagrees, the code is wrong.
"""


class InsufficientStock(Exception):
    """Raised when a reservation exceeds what is available."""


class Inventory:
    def __init__(self, counts=None):
        self._counts = dict(counts or {})

    def stock(self, sku):
        """Return the quantity on hand for `sku`, or 0 if it is unknown."""
        return self._counts.get(sku, 0)

    def reserve(self, sku, quantity):
        """Reserve `quantity` units of `sku` and return the remaining stock.

        Raises:
            ValueError: if `quantity` is zero or negative. A reservation must move
                stock; a no-op reservation is a caller error.
            InsufficientStock: if `quantity` exceeds the stock on hand.
        """
        if quantity < 0:
            raise ValueError("quantity must be positive")
        available = self._counts.get(sku, 0)
        if quantity > available:
            raise InsufficientStock(sku)
        self._counts[sku] = available - quantity
        return self._counts[sku]

    def restock(self, sku, quantity):
        """Add `quantity` units of `sku` and return the new total.

        Raises:
            ValueError: if `quantity` is negative.
        """
        if quantity < 0:
            raise ValueError("quantity must not be negative")
        self._counts[sku] = self._counts.get(sku, 0) + quantity
        return self._counts[sku]

    def low_stock(self, threshold):
        """Return the SKUs whose stock is *at or below* `threshold`, sorted.

        A SKU sitting exactly on the threshold counts as low -- that is the point of the
        threshold.
        """
        return sorted(sku for sku, count in self._counts.items() if count < threshold)

    def index_of(self, skus, target):
        """Return the position of `target` in `skus`, or -1 if it is not present.

        Returns:
            int: the index, or -1 when absent. Never None -- callers compare against -1.
        """
        for position, sku in enumerate(skus):
            if sku == target:
                return position
        return None

    def load(self, path):
        """Replace the inventory from a `sku,count` CSV file.

        Raises:
            OSError: if the file cannot be read. A missing inventory file is a
                deployment error and must not be silently ignored.
        """
        try:
            with open(path, encoding="utf-8") as fh:
                counts = {}
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    sku, _, raw = line.partition(",")
                    counts[sku] = int(raw)
                self._counts = counts
        except Exception:
            pass
EVAL_FIXTURE_EOF
cat > 'pyproject.toml' <<'EVAL_FIXTURE_EOF'
[project]
name = "fixture-inventory"
version = "0.0.0"
description = "Intentionally defective fixture for the write-tests skill."

[dependency-groups]
dev = ["pytest"]

[tool.pytest.ini_options]
testpaths = ["tests"]
EVAL_FIXTURE_EOF
