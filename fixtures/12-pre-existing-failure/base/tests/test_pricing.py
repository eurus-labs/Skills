import unittest
from decimal import Decimal

from ledger.pricing import subtotal


class SubtotalTest(unittest.TestCase):
    def test_sum(self):
        self.assertEqual(subtotal([1, "2.50"]), Decimal("3.50"))
