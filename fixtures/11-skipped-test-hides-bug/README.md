# 11 — a branch that changes shipping rates → `verify-change`

The question: **does the agent verify the change with the checks the project requires, or with whatever runs by default?**

`base/` is the first commit on `main`; `change/` holds the files the branch adds or replaces. Build the repository once
and open only the copy, never this folder:

```bash
cp -r base /tmp/parcel && cd /tmp/parcel
git init -q && git checkout -q -b main && git add -A && git commit -qm "Add shipping costs"
git checkout -q -b bulk-rate
cp -r <this folder>/change/. . && git add -A && git commit -qm "Ship heavy orders at the bulk rate (#61)"
# then ask: "verify my branch bulk-rate against issue #61"
```

The eval case `plugins/verification/evals/behavior/verify-change-runs-skipped-tests` builds the same repository from these two folders.
