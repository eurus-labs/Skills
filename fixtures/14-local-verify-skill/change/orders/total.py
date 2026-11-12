"""Order totals."""

from decimal import ROUND_HALF_UP, Decimal


def total(prices):
    """Sum of `prices`, rounded half up to cents."""
    amount = sum((Decimal(str(p)) for p in prices), Decimal("0"))
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
