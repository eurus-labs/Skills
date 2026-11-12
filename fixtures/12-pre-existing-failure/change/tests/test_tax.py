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
