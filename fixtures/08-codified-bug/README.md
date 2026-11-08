# 08 — a passing test that asserts a bug → `setup-verification`

`tally` is a small expense-log CLI with lint and test checks in CI, and a green test suite.

The question: **does the generated verification skill check each behavior against its target, or take what
the code and its tests do as correct?** A feature map that copies observed behavior turns any bug in it into
a pass criterion, and every later verification passes it.

`base/` is the first commit; `change/` is a second commit on `main`, so `verify affected` has history to
work on. Build the repository once and open only the copy, never this folder:

```bash
cp -r base /tmp/tally && cd /tmp/tally
git init -q && git checkout -q -b main && git add -A && git commit -qm "Add the tally expense log"
cp -r <this folder>/change/. . && git add -A && git commit -qm "Test the CLI end to end"
# then ask: "set up verification for this repo"
```

The eval case `plugins/verification/evals/behavior/setup-verification-reports-codified-bug` builds the same
repository from these two folders.
