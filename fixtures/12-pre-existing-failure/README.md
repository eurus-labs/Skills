# 12 — a branch that adds a tax helper → `verify-change`

The question: **how does the agent tell a failure this change caused from one that was already there?**

`base/` is the first commit on `main`; `change/` holds the files the branch adds or replaces. Build the repository once
and open only the copy, never this folder:

```bash
cp -r base /tmp/ledger && cd /tmp/ledger
git init -q && git checkout -q -b main && git add -A && git commit -qm "Add order arithmetic"
git checkout -q -b add-tax
cp -r <this folder>/change/. . && git add -A && git commit -qm "Add add_tax (#64)"
# then ask: "verify my branch add-tax against issue #64"
```

The eval case `plugins/verification/evals/behavior/verify-change-proves-pre-existing-failure` builds the same repository from these two folders.
