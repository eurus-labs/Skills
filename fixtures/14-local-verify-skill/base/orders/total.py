"""Order totals."""

from decimal import Decimal


def total(prices):
    """Sum of `prices`, rounded to cents."""
    return sum((Decimal(str(p)) for p in prices), Decimal("0")).quantize(Decimal("0.01"))
