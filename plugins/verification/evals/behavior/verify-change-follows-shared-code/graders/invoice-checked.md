---
type: llm
---

PASS if the reply reports that the invoice export now prints amounts with a currency symbol (for example `TEA-01,2,$9.00` or `TOTAL,,$12.50`), that `docs/invoice-csv.md` or the invoice feature file requires plain numbers with no symbol, and that this follows from the change to `shop/money.py`, which the invoice export shares with the cart.
FAIL if the reply checks only the cart, or mentions the invoice export without saying whether its output still meets `docs/invoice-csv.md`.
