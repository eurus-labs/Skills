import unittest
from decimal import Decimal

from shopcart.discount import order_total


class FreeShippingTest(unittest.TestCase):
    def test_freeship_waives_shipping(self):
        self.assertEqual(order_total("40.00", "5.00", "FREESHIP"), Decimal("40.00"))

    def test_freeship_keeps_subtotal(self):
        self.assertEqual(order_total("12.34", "0.00", "FREESHIP"), Decimal("12.34"))
