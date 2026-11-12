import unittest
from decimal import Decimal

from parcel.shipping import shipping_cost


class BulkTest(unittest.TestCase):
    def test_heavy_order_ships_at_bulk_rate(self):
        self.assertEqual(shipping_cost(25), Decimal("12.50"))
