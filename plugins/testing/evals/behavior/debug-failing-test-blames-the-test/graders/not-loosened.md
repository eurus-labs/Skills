---
type: regex
target: { source: file, path: tests/test_pricing.py }
pattern: 'approx|skip|xfail'
match: not_contains
---
