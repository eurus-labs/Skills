# verification

Prove that a change does what it was meant to do. One skill sets up how a specific repository is verified;
the other verifies a change against its goal. Testing is one part of verification; this plugin covers the
rest too: the build, lint, static analysis, and the evidence that ties each result to a requirement.

## Install

```bash
copilot plugin marketplace add eurus-labs/Skills
copilot plugin install verification@eurus-labs
```

## Start here

Run `setup-verification` once per repository:

> *"Set up verification for this repo"*

Then verify any change, whoever made it:

> *"Verify this branch against issue #212"*

## Skills

- **`setup-verification`** — surveys the codebase and writes a project-local `verify-<app>` skill into it:
  - **checks:** the build, lint, static analysis, and test checks that apply, each with its command, when it
    applies, whether it is required, and its pass criterion;
  - **a feature map:** one file per area, with the source paths it owns;
  - **a small CLI:** `doctor`, `start`, `stop`, `affected`, `check`, `capture` and `report`, wrapping the
    commands your repository already has;
  - **a review against the goal:** one verdict per criterion.

  It asks you for the business rules the code cannot settle, then trial-runs every command. Generic itself;
  what it writes adapts to each repository. Fires on "set up verification for this repo", "make a verify
  skill", "create a feature map".
- **`verify-change`** — verifies a change that already exists: the working tree, a branch, a commit range, or
  a pull request. It fixes the goal and acceptance criteria first, runs every check that applies, attaches
  evidence to each criterion, separates this change's failures from pre-existing ones, and reports one
  verdict. Changes no code. Fires on "verify this change", "does this PR do what the issue asks", "run all
  the checks on this".

| You ask for | Skill |
| ----------- | ----- |
| A repository's verification set up or refreshed | `setup-verification` |
| An existing change verified, without changing it | `verify-change` |
| A change made and verified | `implement`, in the `development` plugin |
| A change's code judged | `review-code`, in the `code-review` plugin |

## What "verified" means

Not "every kind of check was run", but **every required check that applies, and every acceptance criterion,
has passing evidence tied to the code under test**. Each check ends in one of four results:

| Result | Meaning |
| ------ | ------- |
| `passed` | It ran against a fresh build, and its output shows success. |
| `failed` | It ran and failed. It counts against the change unless the same failure happens on the base. |
| `not applicable` | The project has no such check, or the change touches nothing it covers. The reason is stated. |
| `not run` | It could not run: a missing tool, credential, or platform. Never counted as passed. |

## Observed is not correct

Code and a running app show what the system does, not what it should do. Every expected behavior in a
generated feature map carries its source — `[confirmed: spec …]`, `[confirmed: user, <date>]`,
`[confirmed: test …]`, or `[observed]` — and only confirmed entries are pass criteria. Each behavior is
checked against its target — what the function is for, from its spec, docstring, docs, name, and callers.
Code or a passing test that contradicts the target is recorded as a suspected bug, with both sides cited;
a test written to match the bug counts as evidence for it, not as confirmation.

## Notes

- **Side effects:** `setup-verification` writes only the verification skill folder (including an executable
  `scripts/verify`). It runs your project's own build, start, and test commands during its survey and trial
  run, and installs nothing. It proposes — never makes — an `AGENTS.md` pointer to the new skill and a
  `.gitignore` entry for the `.verify/` evidence directory.
- `verify-change` runs your project's own checks and writes no file of yours. To show that a failure is
  pre-existing, and only with your agreement, it runs the base in a temporary `git worktree` that it removes
  afterwards.
- No bundled scripts or reference files: every required rule is in each skill's `SKILL.md`.

## Evals

`evals/` holds a [`claude plugin eval`](https://code.claude.com/docs/en/plugin-evals) suite for both skills:

- **`trigger/`:** 10 cases. Each skill has three requests it must fire on while the other stays quiet. Four
  near-misses — make a change, review code, debug one failing test, write tests — belong to sibling plugins
  and must fire neither.
- **`behavior/`:** 2 cases, graded against `fixtures/EXPECTED.md`:
  - `verify-change` on `fixtures/07`, a branch whose checks are green but which does not meet its issue;
  - `setup-verification` on `fixtures/08`, a CLI whose passing test asserts what the code does rather than
    what it is documented to do.

  Each `scaffold.sh` builds a git repository from the fixture's `base/` and `change/` snapshots, with its own
  fixed commit identity.

Run from the repository root, with Claude Code 2.1.269 or later:

```bash
claude plugin eval plugins/verification --tag trigger --ablation none --no-publish --max-cost-usd 3
claude plugin eval plugins/verification --tag behavior --no-publish --max-cost-usd 10 \
  --scaffold --allow-tools Bash Write Edit
```

Each case runs three times with the plugin and three without, and every run is a model call on your account.
The `setup-verification` case is tagged `expensive`: it surveys the repository, writes a skill and trial-runs
it. The graders state the planted defects, so like `fixtures/EXPECTED.md` they are an answer key: keep this
directory out of a fixture demo session.
