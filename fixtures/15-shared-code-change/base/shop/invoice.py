"""Invoice export for the accounting system. The format is specified in docs/invoice-csv.md.

    python3 -m shop.invoice     # prints the CSV for a sample order
"""

from shop.cart import Cart
from shop.money import format_amount


def export_csv(cart):
    """Return the cart as invoice CSV: a header, then one row per line with its line amount."""
    rows = ["sku,quantity,amount"]
    for sku, price, quantity in cart.lines:
        rows.append("%s,%d,%s" % (sku, quantity, format_amount(price * quantity)))
    rows.append("TOTAL,,%s" % format_amount(cart.total_cents()))
    return "\n".join(rows) + "\n"


def sample():
    cart = Cart()
    cart.add("TEA-01", 450, 2)
    cart.add("MUG-02", 350)
    return cart


if __name__ == "__main__":
    print(export_csv(sample()), end="")
