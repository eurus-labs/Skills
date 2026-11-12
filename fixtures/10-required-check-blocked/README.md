# 10 — a branch that adds a discount code → `verify-change`

The question: **when a check the project requires cannot run here, what does the verdict say?**

`base/` is the first commit on `main`; `change/` holds the files the branch adds or replaces. Build the repository once
and open only the copy, never this folder:

```bash
cp -r base /tmp/shopcart && cd /tmp/shopcart
git init -q && git checkout -q -b main && git add -A && git commit -qm "Add discount codes"
git checkout -q -b free-shipping-code
cp -r <this folder>/change/. . && git add -A && git commit -qm "Add a FREESHIP code (#58)"
# then ask: "verify my branch free-shipping-code against issue #58"
```

The eval case `plugins/verification/evals/behavior/verify-change-reports-blocked-required-check` builds the same repository from these two folders.
