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
