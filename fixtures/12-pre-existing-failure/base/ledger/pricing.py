"""Order arithmetic."""

from decimal import Decimal


def subtotal(prices):
    """Sum of `prices`, as a Decimal."""
    return sum((Decimal(str(p)) for p in prices), Decimal("0"))


def legacy_total(prices, fee):
    return subtotal(prices) + Decimal(str(fee))
