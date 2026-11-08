---
type: llm
---

PASS if the reply reports all four places where `inventory.py` contradicts its own docstrings: `reserve` accepts a quantity of 0 although zero must raise `ValueError`; `low_stock` leaves out a SKU exactly at the threshold although SKUs at or below it must be reported; `index_of` returns `None` instead of `-1`; and `load` swallows errors instead of raising `OSError`. It must also say that the tests asserting the documented behaviour fail against the current code.
FAIL if it misses any of the four, reports every test as passing, or presents the current behaviour as correct.
