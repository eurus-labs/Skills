"""Money helpers shared by the cart and the invoice export."""


def format_amount(cents):
    """Return `cents` as a decimal amount with two places, such as ``"12.50"`` for 1250."""
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return "%s%d.%02d" % (sign, cents // 100, cents % 100)
