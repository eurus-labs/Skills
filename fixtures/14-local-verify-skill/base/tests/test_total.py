import unittest
from decimal import Decimal

from orders.total import total


class TotalTest(unittest.TestCase):
    def test_sum(self):
        self.assertEqual(total([1, "2.50"]), Decimal("3.50"))
