import os
import unittest
from decimal import Decimal

from parcel.shipping import shipping_cost

SLOW = os.environ.get("RUN_SLOW") == "1"


@unittest.skipUnless(SLOW, "slow test: set RUN_SLOW=1")
class ShippingTableTest(unittest.TestCase):
    """The full rate table, every weight the shop sells."""

    def test_standard_weights(self):
        for kg, cost in [(0.5, "0.60"), (1, "1.20"), (10, "12.00"), (19.5, "23.40"), (20, "24.00")]:
            with self.subTest(kg=kg):
                self.assertEqual(shipping_cost(kg), Decimal(cost))

    def test_bulk_weights(self):
        for kg, cost in [(20.5, "10.25"), (40, "20.00")]:
            with self.subTest(kg=kg):
                self.assertEqual(shipping_cost(kg), Decimal(cost))
