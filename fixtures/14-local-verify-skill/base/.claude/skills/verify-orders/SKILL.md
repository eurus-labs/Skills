---
name: verify-orders
description: Verify behavior of orders after a change or for a regression sweep — map the diff to feature
  areas, run a fresh build, run the unit tests, capture evidence, and review it against the goal. Use after
  implementing or fixing anything in orders.
---

# Verify orders

## Checks
| Check | Kind | Command | Applies when | Required | Passes when |
| ----- | ---- | ------- | ------------ | -------- | ----------- |
| unit | tests | `make test` | always | yes | exit 0 and at least one test collected |

## Procedure
1. Run `make test`.
2. Review the result against the goal.
