---
name: verify-shop
description: How to verify shop — its test check with command and pass criterion, a feature map, and a CLI
  to map a diff to areas, run the checks, and capture evidence. Read by verify-change and implement when they
  verify a change. Use it directly only to run shop's checks or a regression sweep; to verify a change
  against its goal, use verify-change.
---

# Verify shop

This skill holds shop's checks, feature map, and CLI. To verify a change against its goal, use
`verify-change`: it runs these checks, then fixes the criteria, compares with the base, and gives the verdict.

The CLI runs `make test` and the commands below, and writes evidence to `.verify/`. It starts no server and
reaches no network.

## Rules
- Change no code, tests, or configuration while verifying. Never stash, reset, or check out over the working
  tree; run the base in a temporary `git worktree` and remove it afterwards.
- A missing tool makes a check `not run`, never `passed`. Required comes from CI or a written rule, not from
  what can run here.
- A known failure is not pre-existing for a change until the same check fails the same way on that change's
  base.
- Always run `$V stop`, also after a failed step, so no server outlives its run.

## Checks
| Check | Kind | Command | Applies when | Required | Passes when |
| ----- | ---- | ------- | ------------ | -------- | ----------- |
| build | build | — | always | no | not applicable: pure Python, nothing to build |
| lint | lint | — | always | no | not applicable: the project configures no linter |
| analysis | static analysis | — | always | no | not applicable: the project configures no analyzer |
| unit | tests | `make test` | always | yes (CI gate) | exit 0, at least one test collected; skipped tests listed |

## Known failures
None on `main`.

## Isolation
shop has no server and keeps no data, so runs of different changes may overlap.

## Running the checks
Run everything from the repository root, with `V="python3 .github/skills/verify-shop/scripts/verify"`.
1. `$V doctor` — stop on any failure.
2. `$V affected <base>` — read every listed feature file, including areas marked `via` shared code. Report
   `unmapped:` paths as a map gap: no feature file supplies criteria for them.
3. `$V check --affected <base>` — every applicable check, each ending `passed`, `failed`,
   `not applicable` (with the reason) or `not run` (with the blocker).
4. `$V start` — nothing to start; it says so.
5. For each affected area, drive every entry point the change can affect as its feature file says, wrapping
   each in `$V capture <label> -- …`.
6. `$V stop`, then `$V report`. To remove old runs, show the user what `$V clean` lists and run
   `$V clean --yes` only after they agree.

## Driving it
- Cart: `python3 -c 'from shop.cart import Cart; …'` — there is no cart UI in this repository.
- Invoice: `python3 -m shop.invoice` prints the CSV the accounting system imports.

## Verifying a change
Use `verify-change`. It runs the steps above for the change's base, then adds the goal and its criteria, the
`[confirmed: …]` entries of the affected feature files, the comparison with the base, and one verdict.

## Feature map
references/features/README.md is the index, the owned paths, and the full-sweep order.
