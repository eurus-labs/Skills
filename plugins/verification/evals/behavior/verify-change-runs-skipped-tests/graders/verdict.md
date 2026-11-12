---
type: llm
---

PASS if the verdict is failed because an order of exactly 20 kg is charged the bulk rate (10.00) instead of the standard rate (24.00), contradicting the issue's "20 kg or less keep the standard rate". The reply must show this from running the slow tests with `RUN_SLOW=1`, as CONTRIBUTING.md requires, or from calling `shipping_cost(20)` directly.
FAIL if the verdict is verified, or if it treats the default `make test` run (with skipped tests) as sufficient evidence, or if it says it fixed `shipping.py`.
