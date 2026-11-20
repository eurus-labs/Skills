# Plan 17 — run `document-codebase` end to end on two real codebases (plan 4, W6 part 2)

Status: draft
Date: 2026-11-20
Branch: `test/docs-end-to-end-run`
Baseline: `origin/main` at `48371e031b17e39a9c27c2a7177ebea09f76c101`. Rebase onto `main` after plan 15 merges
(Decision 2).
Target: a new `doc/e2e-evaluation.md`, and the W6 row of `doc/plan-4-documentation-review-workflow.md`. No code
changes.

## Goal

The `document-codebase` workflow has so far been tested only by scripts on fixtures:

- the review loop (plans 9 and 12);
- the product scope (plan 14);
- resume (plan 13);
- the reader and audit editions (plan 14).

The one behavior eval runs a 75-line repository up to P4. Plan 4 asks for two runs, judged on the
documentation rather than on green scripts:

- one small end-to-end repository;
- one multi-component scope with a low-fan-in feature.

It says (`doc/plan-4-documentation-review-workflow.md`, "Verification and completion criteria"):

> A reader should be able to explain the product's purpose, trace a key operation, configure it and
> understand a failure from the draft.

When this is done:

- both runs have been carried out by following `SKILL.md` as a user's agent would;
- `doc/e2e-evaluation.md` records what each run did, what it produced, every problem it hit, and where the
  drafts are;
- the planner has graded each draft against reader questions kept out of this plan.

Problems found are recorded, not fixed. Each becomes a candidate for its own plan.

## Decisions

1. **The two codebases are in this repository** (the user's choice, 2026-11-20).
   - **Small:** `tests/contracts/layered-repo`, 10 Python files.
   - **Multi-component:** `shared/scripts/`, 48 Python files and about 21,800 lines, in components
     `survey`, `analyze`, `check`, `document`, `render`, `review` and `publish`, with low-fan-in modules such as
     `detect_stack.py` and `publish/editions.py`.

   Each is copied to its own directory outside the repository, and that copy is made a git repository with one
   commit, using the commit identity of `AGENTS.md`. The run never writes inside this checkout.

   Rejected: a public open-source repository, which needs network access this session may not have and has no
   answer key.
2. **Plan 15 merges first.** `layered-repo` has four empty `__init__.py` files, and before plan 15 they leave
   every run `partial`.
   - The coder rebases onto `main` once plan 15 is merged and checks that `docs` is 1.7.1 or later.
   - If plan 15 is not merged, the coder stops and reports. It does not run on the old code.
3. **How the skill is run.** The coder follows `plugins/docs/skills/document-codebase/SKILL.md` and the
   references it points to, from this checkout. It calls `scripts/pipeline.py` by its path in the plugin
   folder, from the copied codebase as the working directory.
   - The run is **explicitly unattended**: the coder may record P1–P3 itself, with notes of at least five
     words, as `SKILL.md` rule 6 allows.
   - It **stops at P4**. It never answers P4 and never runs `publish`.
   - It uses the default `--top`, which reads every product file. Where the multi-component run cannot finish
     in one session, it stops the way `references/workflow.md` says: it writes `.docs-build/continuation.md`,
     then continues with `pipeline.py resume`. Doing so is part of what is evaluated.
   - Where the host offers no subagents, it uses the sequential path and records `self_review`.

   Rejected: answering P4 on the user's behalf, which `SKILL.md` forbids. Publishing is already covered by
   tests.
4. **What the coder records in `doc/e2e-evaluation.md`**, one section per run:
   - the exact copy and commit commands, and the `docs` version and `main` commit used;
   - every `pipeline.py` command run, in order, with its exit code and the one line of output that matters;
   - the checkpoint notes it recorded at P1–P3;
   - `scope.json` counts by disposition, and the unread count at the end;
   - the gate outcome from `generation-report.json`: `analysis_mode`, the quality verdict, and each failed
     check with its message;
   - the revision numbers, the review rounds, and the open findings at P4, from `pipeline.py resume`;
   - whether `continuation.md` and `resume` were used, and whether `resume` named the right next step;
   - the review mode, `independent` or `self_review`;
   - wall time and turns where the host reports them, marked as estimates otherwise;
   - **every problem**, each with the command, the message or symptom, the file and line where the cause is
     when found, and whether the run worked around it. A workaround is described, never hidden.
   - the absolute paths of both build directories, left in place for grading.
5. **No code or instruction changes.** The coder edits only `doc/e2e-evaluation.md` and the W6 row of plan 4.
   - A bug that blocks the run is recorded, and the run stops there.
   - The coder never patches a script to get past one, and never edits the copied codebases' source.
   - It never deletes the build directories.
6. **Grading is the planner's, after the coder finishes.** The planner reads both drafts in their build
   directories and grades them against reader questions it writes after the coder's report, so the run never
   sees them. Plan 4 keeps semantic evaluation separate from reviewer inputs. The questions cover:
   - purpose;
   - a key operation traced through the code;
   - configuration;
   - a failure case;
   - for `shared/scripts`, the low-fan-in feature.

   Each answer is checked against the source. The planner adds a "Grading" section to `doc/e2e-evaluation.md`
   in the same pull request, before opening it.
7. **Plan 4's W6 row**, by the coder's last commit: "Migration by plan 16; end-to-end runs recorded in
   `doc/e2e-evaluation.md` (plan 17)". If plan 16 has not merged, say "migration pending (plan 16)". Plan 4's
   own `Status` changes only when the user says W6 is accepted.

## Scope

In:

- `doc/e2e-evaluation.md` (new).
- The W6 row of `doc/plan-4-documentation-review-workflow.md`.
- Copies of the two codebases and their build directories, outside the repository.

Out:

- **Any change** under `shared/`, `plugins/`, `tools/`, `fixtures/` or `tests/`, and any version bump.
- **Answering P4, and running `publish`** (Decision 3).
- **Fixing what the runs find.** Each problem is a follow-up for the user to plan.
- **A run on GitHub Copilot CLI.** It is not available to this session.
- **Plan 16's migration.** A fresh run has no legacy artifacts.

## Baseline

| Existing | Keep, change, or remove |
| --- | --- |
| `plugins/docs/skills/document-codebase/SKILL.md` and `references/` | Read and follow; do not change |
| `plugins/docs/skills/document-codebase/scripts/pipeline.py` | Run; do not change |
| `tests/contracts/layered-repo/` (10 files; 4 empty `__init__.py`) | Copy only |
| `shared/scripts/` (48 `.py` files, about 21,800 lines) | Copy only |
| `doc/eval-results.md`: the 2026-11-20 behavior run on `layered-repo` stopped at P4 with a draft, after 22–36 turns | Context; this plan goes further, judging content and covering a large scope |
| `doc/plan-4-documentation-review-workflow.md` W6 row | Update per Decision 7 |

## Tech stack and constraints

Default. The runs need `python3` 3.9 or later and `git`. PlantUML and Sphinx are used when present and
reported as `skipped` when absent; record which were present. Nothing is installed.

## Acceptance criteria

- [ ] **Plan 15 is in.** The branch is rebased onto a `main` with plan 15 merged, and the `docs` version
      recorded is 1.7.1 or later. Checked by `git log --oneline -1 origin/main` and the recorded version.
- [ ] **Both runs reached P4, or the report says exactly where and why they stopped.** For each run, the
      report has every item of Decision 4. Checked by reading `doc/e2e-evaluation.md`.
- [ ] **`layered-repo`:** `scope.json` has 6 `product` and 4 `empty` rows, and the run ends with 0 unread
      product files. Checked by the counts in the report, and by running this in the build directory named
      there:

      ```bash
      python3 -c 'import json,collections;s=json.load(open("scope.json"));print(collections.Counter(r["disposition"] for r in s["files"]))'
      ```
- [ ] **`shared/scripts`:** every product file is read, or the report names the unread ones and why. The
      low-fan-in modules `detect_stack.py` and `publish/editions.py` appear in `units.txt` or in the
      `analyzed` rows of `scope.json`.
- [ ] **Failure case, a stop and resume.** If a run stopped mid-way, `continuation.md` exists and
      `pipeline.py resume` was run, and the report says whether its suggested next step was correct. If
      neither run needed to stop, the report says so, and a deliberate stop is tested on `layered-repo` after
      `check`: write the note, run `resume`, then continue.
- [ ] **No change outside the report.** Running
      `git diff --stat origin/main...HEAD -- . ':!doc/e2e-evaluation.md' ':!doc/plan-4-documentation-review-workflow.md' ':!doc/plan-17-docs-end-to-end-run.md'`
      prints nothing.
- [ ] **The build directories still exist** at the paths the report gives. The planner checks this before
      grading (Decision 6).
- [ ] **Required checks pass:** `python3 tools/validate.py` and
      `for t in tools/test_*.py; do python3 "$t" || break; done`.

## Risks

| Risk | How it is handled |
| --- | --- |
| The `shared/scripts` run exhausts the coder's context | Decision 3: stop with `continuation.md` and continue with `resume`. That exercises plan 13 for real, and the report records it |
| The coder knows this codebase and writes from memory, not from reading | `validate_analysis.py` requires evidence per statement, and the planner's grading checks claims against the source. The report states that the coder had seen the code before |
| A blocking bug ends a run early | It is recorded with its cause and the run stops (Decision 5); a partial evaluation is still a result |
| The coder answers P4 or publishes to get a "complete" run | Forbidden by Decision 3 and `SKILL.md`. The planner checks that no `docs/` directory exists in either copy |
| The build directories are cleaned before grading | Decision 5, and the planner checks them first |
| The coder run is cut off | Push the report after each run |

## Open questions

None.
