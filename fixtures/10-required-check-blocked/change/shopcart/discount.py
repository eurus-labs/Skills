"""Discount codes for the shop's cart."""

from decimal import Decimal

PERCENT_CODES = {"SAVE10": Decimal("0.10")}
FREE_SHIPPING_CODES = {"FREESHIP"}


def order_total(subtotal, shipping, code=None):
    """Return `subtotal` plus `shipping` after applying the discount `code`, rounded to cents.

    A percentage code reduces the subtotal only; FREESHIP waives shipping. An unknown code raises KeyError.
    """
    subtotal, shipping = Decimal(subtotal), Decimal(shipping)
    if code in FREE_SHIPPING_CODES:
        shipping = Decimal("0")
    elif code is not None:
        subtotal = subtotal * (1 - PERCENT_CODES[code])
    return (subtotal + shipping).quantize(Decimal("0.01"))
