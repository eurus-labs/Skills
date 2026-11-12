import unittest
from decimal import Decimal

from shopcart.discount import order_total


class OrderTotalTest(unittest.TestCase):
    def test_no_code(self):
        self.assertEqual(order_total("40.00", "5.00"), Decimal("45.00"))

    def test_percent_code_reduces_subtotal_only(self):
        self.assertEqual(order_total("40.00", "5.00", "SAVE10"), Decimal("41.00"))

    def test_unknown_code_is_rejected(self):
        with self.assertRaises(KeyError):
            order_total("40.00", "5.00", "NOPE")
