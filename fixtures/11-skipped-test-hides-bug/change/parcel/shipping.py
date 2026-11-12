"""Shipping cost for an order."""

from decimal import Decimal

STANDARD_RATE = Decimal("1.20")  # per kg
BULK_RATE = Decimal("0.50")      # per kg, for orders over BULK_THRESHOLD_KG
BULK_THRESHOLD_KG = Decimal("20")


def shipping_cost(weight_kg):
    """Cost to ship `weight_kg` kilograms, rounded to cents.

    Orders over 20 kg ship at the bulk rate; lighter orders at the standard rate.
    """
    weight = Decimal(str(weight_kg))
    rate = BULK_RATE if weight >= BULK_THRESHOLD_KG else STANDARD_RATE
    return (weight * rate).quantize(Decimal("0.01"))
