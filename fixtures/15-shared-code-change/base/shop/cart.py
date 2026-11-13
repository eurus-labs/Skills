"""The shopping cart."""

from shop.money import format_amount


class Cart:
    def __init__(self):
        self.lines = []

    def add(self, sku, price_cents, quantity=1):
        """Add `quantity` of `sku` at `price_cents` each."""
        if quantity < 1:
            raise ValueError("quantity must be at least 1")
        self.lines.append((sku, price_cents, quantity))

    def total_cents(self):
        return sum(price * quantity for _, price, quantity in self.lines)

    def display_total(self):
        """The total as shown to the customer in the cart."""
        return format_amount(self.total_cents())
