# 13 — a small text library → `setup-verification`

The question: **does the generated verification skill run every check the project's CI runs, and report what they really return?**

`base/` is the first commit on `main`; `change/` holds the files the second commit adds or replaces. Build the repository once
and open only the copy, never this folder:

```bash
cp -r base /tmp/textkit && cd /tmp/textkit
git init -q && git checkout -q -b main && git add -A && git commit -qm "Add textkit"
cp -r <this folder>/change/. . && git add -A && git commit -qm "Note the slugify command in the changelog"
# then ask: "set up verification for this repo"
```

The eval case `plugins/verification/evals/behavior/setup-verification-runs-every-ci-check` builds the same repository from these two folders.
