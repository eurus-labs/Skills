---
name: implement
description: Implement features, fix bugs, or refactor code when the user requests code changes — inspecting the project, making the necessary design decisions, making focused changes, and verifying the result against the original request with tests, builds, and checks; builds from an existing design or plan when one is provided, and fixes review findings. Use when the user says "implement this", "add X", "build this feature", "fix this bug", "refactor X into Y", "make this change", "design and implement", "implement this plan", "fix these review comments", or hands over an issue or ticket to be coded. When the user wants only a design or plan with no code, use design-solution instead; to review changes, use review-code instead; for one failing or flaky test, use debug-failing-test instead; to only add tests for existing code, use write-tests instead.
---

# Implement

## Overview

Make the requested code change in the user's repository and show, with evidence, that it does what was asked.
The skill owns the whole job: inspection, the design decisions the task needs, implementation, verification,
and repair. It does not depend on any other skill loading. When the user supplies a design, it is an input to
validate against the current code, not an order to follow blindly.

The deliverable is the edited files plus the handoff in [Output format](#output-format). Its status is earned
by verification evidence, not by the code compiling.

## When to use this skill

- New or changed behavior: a feature, an option, an endpoint, a command.
- A bug report, issue, or ticket to fix in code.
- A refactor with a stated goal.
- "Design and implement" — design happens inside this skill.
- A supplied design or plan to build, including one written by `design-solution`.
- Review findings to fix, including ones from `review-code`.

## When not to use this skill

- **Only a design or plan is wanted, no code** — use `design-solution`.
- **Changes need reviewing, not changing** — use `review-code` from the `code-review` plugin.
- **One test is failing or flaky** — use `debug-failing-test` from the `testing` plugin.
- **Only tests are wanted for code that already exists** — use `write-tests` from the `testing` plugin.
- **An exact mechanical edit the user dictated** (fix this typo, bump this version) — do it directly.
- **A question about how code works**, with no change requested — answer it directly.

## Hard rules

1. **Define acceptance criteria before editing any file**, in a task contract (Output format). Keep the
   user's request verbatim in it: verification is measured against those words.
2. **Never weaken a criterion to match what was built.** A revision is allowed only as an explicit entry under
   **Contract changes**, with the reason; one that changes requested behavior or scope needs the user's
   agreement first.
3. **Stay in scope.** No unrelated refactoring, renaming, reformatting, or dependency changes. Note what you
   noticed under **Limitations** instead.
4. **Follow project instructions and established conventions** — layering, naming, error handling, test
   layout. Introduce a new abstraction, design pattern, or dependency only for a concrete problem in this code,
   and record the simpler option it beat.
5. **Verification is mandatory and is yours.** Run it even when a review plugin exists; an independent review
   adds to it and never replaces it. Do not hand verification to a skill that may not load.
6. **Evidence must be able to fail.** A test that would also pass on the unchanged code, or that recomputes the
   expected value with the same logic as the implementation, does not establish the requested behavior.
7. **Never edit an existing test to make it pass** unless it is demonstrably wrong against the request — then
   record it under **Contract changes**.
8. **Report status honestly.** `implemented and verified` only with evidence for every criterion and every
   required check passing. A check not run is `not run`, never `passed`. Claim "independently reviewed" only
   when an independent review actually happened.
9. **Ask only when ambiguity materially changes behavior or scope.** Decide routine choices and record them.
10. **Preserve the user's work.** Run `git status` first. Never stash, reset, check out, or overwrite
    uncommitted changes you did not make. Do not commit or push unless asked.

## Output format

### Task contract — before coding

Write it in the conversation; persist it to a file only if the user asks. Scale it to the task — for a small
change, **Request**, **Acceptance criteria**, and **Verification plan** are enough.

```markdown
## Task contract
Workflow: small | feature/structural | bug, cause unknown | supplied design | review findings
Request (verbatim): "parse_config crashes on an empty file; it should return the defaults"
Expected behavior: an empty or whitespace-only file yields `Config()` defaults; no exception.
Scope: `config/parser.py`, `tests/test_parser.py`
Out of scope: error messages for malformed files
Constraints: Python 3.9 floor (pyproject.toml); no new dependencies
Acceptance criteria:
  AC1. Empty file returns defaults — check: new test; fails before the fix with `IndexError`
  AC2. Whitespace-only file returns defaults — check: new test
  AC3. Valid files parse as before — check: existing `tests/test_parser.py` passes unmodified
Verification plan: `pytest tests/test_parser.py`, then `pytest` and `ruff check .` (CONTRIBUTING.md)
```

### Handoff — at the end

```markdown
## Result
Status: implemented and verified | implemented, verification incomplete | implemented, checks failing | blocked

## Changes
- `config/parser.py` — return `Config()` when the stripped content is empty, before tokenizing
- `tests/test_parser.py` — tests for AC1, AC2

## Verification
| Criterion / check | Command or method | Result | Evidence |
| ----------------- | ----------------- | ------ | -------- |
| AC1 | `pytest tests/test_parser.py -k empty_file` | passed | failed before the fix (`IndexError`), `1 passed` after |
| AC2 | `pytest tests/test_parser.py -k whitespace` | passed | `1 passed` |
| AC3 | `pytest tests/test_parser.py` | passed | `18 passed`; no existing test edited |
| Full suite | `pytest` | failed (existing) | `test_network_fetch` fails identically on the unchanged code — needs network |
| Lint | `ruff check .` | not run | `ruff` is not installed; not installed by this skill |

## Contract changes
None.

## Design decisions and deviations
- Handled emptiness in `parse_config` rather than the tokenizer: the tokenizer is shared with `parse_rules`,
  where empty input is an error.

## Limitations
- Not tested: a file containing only a byte-order mark. Lint not run.
```

Pick exactly one status:

| Status | When |
| ------ | ---- |
| `implemented and verified` | Every criterion has passing evidence; every required check passed or failed only for a proven pre-existing reason. |
| `implemented, verification incomplete` | A required check or criterion could not be verified. Name it and the blocker. |
| `implemented, checks failing` | A check this change caused still fails after repair. Show the failing output. |
| `blocked` | Essential information or access is missing. Name it; nothing beyond the contract was changed. |

The handoff states what changed, how it was verified, and what remains unverified. Never claim that passing
tests prove every behavior correct.

## Steps

### 1. Inspect

1. Run `git status`; note uncommitted changes that are not yours.
2. Read the project's instructions: `AGENTS.md`, `CONTRIBUTING.md`, `.github/copilot-instructions.md`, and
   `.github/instructions/*.instructions.md` whose `applyTo` matches files you will touch. Note conventions,
   required checks, and forbidden actions.
3. Find how checks run here: the commands those instructions name, otherwise the CI workflow, `Makefile`,
   `package.json` scripts, `pyproject.toml`/`tox.ini`, or the ecosystem's standard runner.
4. Read the code the request touches, its callers, the interfaces it implements, and its existing tests. Find
   the nearest precedent for this kind of change and use it as the template.

### 2. Select the workflow

| Task | Workflow |
| ---- | -------- |
| Small, clear change with an obvious place and precedent | Inspect → Implement → Verify |
| Feature or structural change: new component, cross-module, public interface, schema, or several plausible designs | Inspect → Design internally → Implement → Verify |
| Bug with an unknown cause | Reproduce or gather evidence → Diagnose → Implement → Verify |
| Supplied design or plan | Read the design → Inspect and validate its assumptions → Implement → Verify |
| Review findings | Read the findings → Validate each against the current code → Fix the valid ones → Verify |
| Essential information missing | Ask one focused question, or report the specific blocker |

When unsure whether a change is small, decide by the cost of being wrong: changes to a public API, data
format, persistence, or concurrency get the design step.

### 3. Write the task contract

Derive criteria from the verbatim request, not from the solution you have in mind. Include a criterion for
behavior that must not change, and a negative or failure case where the request implies one.

### 4. Workflow-specific work before coding

- **Design internally.** Choose the simplest design that meets every criterion: extend in place, then follow
  the precedent, then extract, and only then introduce an abstraction or pattern — and only for a problem
  visible in this code. Check compatibility of public signatures, formats, config, and schema; data safety on
  partial failure; error reporting. Write the decision and the alternative it beat under **Design decisions**.
- **Diagnose.** Reproduce the failure before changing code — preferably as a failing test, otherwise a command
  showing the wrong output. Follow the data to the first wrong value; test one hypothesis at a time. State the
  cause as location plus mechanism. If it cannot be reproduced, report what was tried and ask for the missing
  condition; do not fix a guessed cause.
- **Supplied design.** Check each assumption it makes — file paths, signatures, callers, behavior — against the
  current code. Where the code contradicts the design, follow the code, and record the departure and its
  reason. If the contradiction changes requested behavior or scope, ask first.
- **Review findings.** For each finding, confirm it against the current code: reproduce it or trace the failure
  path. Fix the valid ones. For each one you do not fix, state why — already fixed, does not reproduce, out of
  scope — with the evidence.

### 5. Implement

1. Make the change, following the plan or the precedent. Match surrounding naming, error handling, logging,
   and comment density.
2. Handle the errors, edge cases, and compatibility requirements the criteria name.
3. Add or update tests where needed to verify behavior, in the framework and layout the repository already
   uses. When practical, run a new test before the implementation exists and see it fail for the right reason.
4. Update documentation the change makes wrong: README usage, help text, changelog if the repository keeps one.
5. Record material departures from the supplied design or your own plan, with the cause. If a departure
   invalidates a design assumption, revisit the design before continuing.

### 6. Verify — mandatory

1. **Compare the result with the original request and the acceptance criteria.** Re-read the verbatim request,
   then the diff. For each criterion, find what in the diff produces the behavior — not whether the diff
   matches the plan.
2. **Select checks by affected behavior, concrete regression risks, and project requirements**: the tests for
   each criterion, the tests covering every touched module, and the gates the project requires before a change
   is done (full suite, lint, type check, build). Add checks for callers of any changed signature or format.
3. **For bug fixes, reproduce the original failure and confirm the correction** when feasible: the
   reproduction fails before the fix and passes after.
4. **Check relevant negative cases and failure behavior**: invalid, empty, or boundary input; missing
   resources; the error the user should see.
5. **Run the checks using project conventions**, narrowest first, so a failure points at its cause. Confirm a
   passing run actually executed tests — a selector that collected nothing is not a pass.
6. **Inspect the final changes** with `git diff` and the list of new files: accidental edits, scope drift,
   changed signatures with unchanged callers, removed error handling, debug output, secrets.
7. **Repair failures caused by the change** and repeat the relevant checks — the failing check and those
   covering what the fix touched. Re-run broad gates once at the end, not after every edit. After two repair
   attempts on the same failure with no new evidence, stop and report `implemented, checks failing`.
8. **Distinguish change-related failures, existing failures, and environment blockers** using evidence: a
   failure that reproduces identically on the unchanged code is existing; a missing tool, service, credential,
   or platform is an environment blocker. Do not install tools to get past one.
9. **Report passed, failed, and not-run checks**, and name every acceptance criterion that remains unverified.
10. **Stop optional testing** once the relevant risks and the required gates are addressed.

### 7. Hand off

Write the handoff (Output format). Separate what passed, what failed, and what was not run. If the user wants
an independent review, `review-code` from the `code-review` plugin can be suggested by name; do not wait on it
or report it as done.

## Bundled resources

None. Everything this skill requires, including verification, is in this file.

## Conventions

- **Side effects.** This skill edits files in the user's repository and runs the project's own tests,
  linters, type checkers, and builds, which may write build output or reach the network themselves. It
  installs no packages and adds no dependencies; a check that needs a missing tool is reported `not run`.
  Ask before any command that acts outside the working tree — a migration against a database, a deploy, a
  publish, a call to a live service.
- No destructive git commands (`reset --hard`, `checkout -- <file>`, `clean`, force-push) without the user's
  explicit confirmation for that command.
- When asked to commit, follow the repository's commit conventions.
- Keep the contract and evidence in the conversation unless the user asks for a file.
