"""Shipping cost for an order."""

from decimal import Decimal

STANDARD_RATE = Decimal("1.20")  # per kg


def shipping_cost(weight_kg):
    """Cost to ship `weight_kg` kilograms at the standard rate, rounded to cents."""
    return (Decimal(str(weight_kg)) * STANDARD_RATE).quantize(Decimal("0.01"))
