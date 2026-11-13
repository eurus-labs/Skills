import unittest

from shop.money import format_amount


class FormatAmountTest(unittest.TestCase):
    def test_two_places(self):
        self.assertEqual(format_amount(1250), "12.50")

    def test_negative(self):
        self.assertEqual(format_amount(-5), "-0.05")


if __name__ == "__main__":
    unittest.main()
