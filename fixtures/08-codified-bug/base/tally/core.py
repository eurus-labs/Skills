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
