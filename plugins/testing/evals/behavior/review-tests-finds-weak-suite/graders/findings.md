---
type: llm
---

PASS if the reply treats these as serious problems: `test_apply_coupon` and `test_add_calls_through` mock the very method they claim to test; and the tests share the module-level `CART`, so they depend on running in order. It must also name at least three assertions that cannot fail, such as `is not None`, `count() > 0`, `in (True, False)`, an `isinstance` check, or a test with no assertion.
FAIL if it calls the suite adequate, misses the mocked-subject tests or the order dependency, or rewrites the tests instead of reporting.
