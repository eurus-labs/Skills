# 14 — a repository that already has its own verify skill → triggering

The question: **which skill answers a request to verify a branch, when the repository carries its own verification skill?**

`base/` is the first commit on `main`; `change/` holds the files the branch adds or replaces. Build the repository once
and open only the copy, never this folder:

```bash
cp -r base /tmp/orders && cd /tmp/orders
git init -q && git checkout -q -b main && git add -A && git commit -qm "Add order totals and their verify skill"
git checkout -q -b fix-rounding
cp -r <this folder>/change/. . && git add -A && git commit -qm "Round totals half up (#31)"
# then ask: "verify my branch fix-rounding against issue #31"
```

The eval case `plugins/verification/evals/trigger/verify-change-with-local-verify-skill` builds the same repository from these two folders.
