# 15 — a change to shared code → `verify-change`

`shop` has a cart and an invoice export; both format amounts through `shop/money.py`. The branch
`currency-symbol` claims to close issue #7:

> Show the currency symbol in cart totals, for example `$12.50`.

The question: **when a change touches shared code, does the agent check every area that depends on it, or
only the one the issue names?** The repository carries its own `verify-shop` skill, whose feature map lists
the shared code each area uses.

`base/` is the project on `main`; `change/` holds the files the branch replaces. Build the repository once
and open only the copy, never this folder:

```bash
cp -r base /tmp/shop && cd /tmp/shop
git init -q && git checkout -q -b main && git add -A && git commit -qm "Add the cart and invoice export"
git checkout -q -b currency-symbol && cp -r <this folder>/change/. . && git add -A
git commit -qm "Show the currency symbol in cart totals (#7)"
# then ask: "verify my branch currency-symbol against issue #7"
```

The eval case `plugins/verification/evals/behavior/verify-change-follows-shared-code` builds the same
repository from these two folders.
