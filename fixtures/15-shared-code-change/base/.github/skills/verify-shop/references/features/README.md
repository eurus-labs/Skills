# shop feature map

## Index
- [cart](cart.md) — owns: `shop/cart.py`, `tests/test_cart.py` — uses: `shop/money.py` — add lines, totals,
  the total shown to the customer.
- [invoice](invoice.md) — owns: `shop/invoice.py`, `docs/invoice-csv.md` — uses: `shop/money.py`,
  `shop/cart.py` — the CSV the accounting system imports.

## Baseline preconditions
None: no server, no data.

## Full-sweep order
cart, then invoice.

## Entry contract
Each feature file has exactly these sections: Sub-features; How to get to it (user POV); Driving it;
Expected behavior; Suspected bugs; Open questions; Gotchas.
