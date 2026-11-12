import unittest
from decimal import Decimal

from parcel.shipping import shipping_cost


class ShippingTest(unittest.TestCase):
    def test_standard_rate(self):
        self.assertEqual(shipping_cost(2), Decimal("2.40"))
