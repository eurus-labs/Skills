import unittest

from shop.cart import Cart


class CartTest(unittest.TestCase):
    def test_total(self):
        cart = Cart()
        cart.add("TEA-01", 450, 2)
        cart.add("MUG-02", 350)
        self.assertEqual(cart.total_cents(), 1250)

    def test_display_total(self):
        cart = Cart()
        cart.add("TEA-01", 450, 2)
        self.assertEqual(cart.display_total(), "$9.00")

    def test_rejects_zero_quantity(self):
        with self.assertRaises(ValueError):
            Cart().add("TEA-01", 450, 0)


if __name__ == "__main__":
    unittest.main()
