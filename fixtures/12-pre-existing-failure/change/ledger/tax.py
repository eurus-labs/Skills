"""Sales tax."""

from decimal import Decimal


def add_tax(amount, rate):
    """Return `amount` plus tax at `rate` (0.08 for 8%), rounded to cents."""
    amount = Decimal(str(amount))
    return (amount * (1 + Decimal(str(rate)))).quantize(Decimal("0.01"))
