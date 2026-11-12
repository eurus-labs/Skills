# Contributing

A change is ready to merge when both of these pass. CI runs both on every pull request.

- `make test` — the unit tests.
- `make contract` — the payments contract tests. They run against the payments sandbox and need
  `PAYMENTS_SANDBOX_KEY`. CI has the key; the payments team issues keys to people who need one locally.
