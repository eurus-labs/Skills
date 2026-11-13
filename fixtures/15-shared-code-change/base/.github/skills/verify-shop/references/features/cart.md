# Cart

The cart a customer fills before checkout.

## Sub-features
- add: add a line with a price in cents and a quantity of at least 1.
- totals: the total in cents, and the total as shown to the customer.

## How to get to it (user POV)
- There is no UI in this repository; the cart is a library used by the storefront.

## Driving it
- `$V capture cart-total -- python3 -c 'from shop.cart import Cart; c = Cart(); c.add("TEA-01", 450, 2); print(c.display_total())'`

## Expected behavior
- A quantity below 1 raises `ValueError`. [confirmed: test tests/test_cart.py::CartTest::test_rejects_zero_quantity]
- The total is the sum of price times quantity. [confirmed: test tests/test_cart.py::CartTest::test_total]

## Suspected bugs
None found.

## Open questions
None.

## Gotchas
None.
