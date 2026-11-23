# Plan 19 — eval cases for `review-code`, `setup-review-rules` and `evaluate-skill`

Status: implemented
Date: 2026-11-20
Branch: `test/evals-review-and-skill-authoring`
Baseline: `origin/main` at `efc202530d5b934bc73a2a34f837af042fa7cecf`
Target: `plugins/review/evals/`, `plugins/skill-authoring/evals/` (new), `fixtures/16-flawed-skill/` (new),
`fixtures/EXPECTED.md`, `fixtures/README.md`, `tools/build_eval_scaffolds.py`, the two plugin READMEs,
`doc/eval-results.md`

## Goal

Three skills have no eval case at all (`doc/eval-results.md`, 2026-11-19/20):
- `review-code` and `setup-review-rules` in `review`, whose only cases test `review-ui`;
- `evaluate-skill` in `skill-authoring`, which has no `evals/` directory.

The 0.2.0 suites skipped these two plugins, and plan 8 added cases for `review-ui` only.

When this is done:
- each of the three skills has trigger cases in both directions;
- each has one behavior case graded against an answer key written before the run;
- the planner has run them on Claude Code and recorded the scores.

## Decisions

1. **Trigger cases: two that must fire, one that must stay quiet, per skill** (the user's choice, 2026-11-20).
   - The format is the existing `plugins/review/evals/trigger/review-ui-*` cases: `tags: [trigger]`,
     `max_turns: 6`, `allowed_tools: [Read, Glob, Grep, Skill]`, and one `tool_used: Skill` grader. A quiet
     case adds `min: 0`, `max: 0` and `arm: both`.
   - **No prompt names a file the workspace lacks.** Trigger cases run without a scaffold, and plan 10 found a
     case that only tested a missing file. Use these prompts or close equivalents:

     | Case | Prompt | Expect |
     | --- | --- | --- |
     | `review-code-before-merge` | "Review my changes before I merge them." | fires `review-code` |
     | `review-code-security-pass` | "Can you do a security and correctness pass over the code I just wrote?" | fires `review-code` |
     | `review-code-quiet-test-suite` | "Are the unit tests in this project any good?" | `review-code` quiet (its description sends a test suite to `review-tests`) |
     | `setup-review-rules-agents-md` | "Add an AGENTS.md and Copilot instructions for this repository." | fires `setup-review-rules` |
     | `setup-review-rules-checklist` | "We need coding standards and a review checklist for this project." | fires `setup-review-rules` |
     | `setup-review-rules-quiet-review` | "Review this pull request against the rules we already have in AGENTS.md." | `setup-review-rules` quiet (that is `review-code`) |
     | `evaluate-skill-will-it-trigger` | "Will my skill trigger on the right requests? Evaluate it." | fires `evaluate-skill` |
     | `evaluate-skill-write-evals` | "Write evals for this plugin." | fires `evaluate-skill` |
     | `evaluate-skill-quiet-verify` | "Check that my code change actually works before I merge it." | `evaluate-skill` quiet (that is `verify-change`) |

2. **`review-code` behavior case on `fixtures/04-security`.** Name the case
   `review-code-finds-planted-vulnerabilities`. The scaffold is generated from the fixture by
   `tools/build_eval_scaffolds.py`, leaving out `README.md`, as the other behavior cases do. The prompt is
   "Review app.py before I merge it."

   Graders:
   - `used-skill` (`tool_used`, with-only);
   - `code-untouched`: a `regex` on `app.py` matching one planted line, so an edit fails;
   - `findings`: an `llm` grader on the last message, written from `fixtures/EXPECTED.md` section 04. It
     passes when the reply finds all four blocking findings, each with its CWE and an exploit input:
     - both SQL injections (CWE-89);
     - the missing authorization check (CWE-862);
     - the path traversal (CWE-22).

     It also requires that these be ranked above the should-fix ones, and that `format_receipt` not be
     flagged. It fails on any item the answer key's "Fail" line names.
   - Amended 2026-11-23 by the user's choice: the first run showed `review-code` rating the hardcoded key, MD5
     and open redirect as Blocking, which its own severity ladder allows (`review-standard.md:28`). The
     grader now requires the four at the top severity and no longer fails other security findings ranked
     with them, or a non-security nit on `format_receipt`.
3. **`setup-review-rules` behavior case on `fixtures/05-mixed-monorepo`.** Name the case
   `setup-review-rules-scopes-per-package`. Scaffold as in Decision 2. The prompt is "Set up agent and review
   rules for this repository."

   Graders:
   - `used-skill`;
   - `wrote-rules`: a `file_exists` for `AGENTS.md`;
   - `scoped-commands`: an `llm` grader that reads `AGENTS.md` with `focus: { source: file, path: AGENTS.md }`,
     written from `EXPECTED.md` section 05. It passes when `python -m pytest` is scoped to `services/api` after
     its install command, and `npm test` to `apps/web`, with no repository-wide runner, invented lint command
     or mandatory convention drawn from one file.

   Do not use `focus: files`. It gives the judge only the list of paths written, not their contents
   (`doc/eval-results.md`, "Lessons from the redesign").
4. **A new fixture, `fixtures/16-flawed-skill/`** (the user's choice). It is a minimal plugin, not
   installable from any marketplace, with two skills and exactly four planted defects:

   | # | Defect | Where |
   | --- | --- | --- |
   | 1 | Frontmatter `name` differs from its folder name | the first skill's `SKILL.md` |
   | 2 | The second skill is missing from `plugin.json`'s `skills` array, so it would silently not install | both `plugin.json` copies |
   | 3 | The two skills' descriptions claim the same requests, and neither says when not to use it, so they compete to trigger | both `SKILL.md` |
   | 4 | A step tells the agent to run a bundled script that does not exist | the first skill's `SKILL.md` |

   - Give the fixture both `.claude-plugin/plugin.json` and `.github/plugin/plugin.json`, identical.
   - Its `README.md` states the question only, like the other fixtures, and the scaffold leaves it out.
   - Add section `## 16 — flawed-skill → evaluate-skill` to `fixtures/EXPECTED.md`, listing the four defects
     with Pass and Fail lines.
   - Add a row to the scenario table in `fixtures/README.md`.
   - The fixture must not make `tools/validate.py` fail. If `validate.py` scans `fixtures/`, stop and report
     rather than excluding it.
5. **`evaluate-skill` behavior case on fixture 16.** Name the case `evaluate-skill-finds-planted-defects`.
   - **Prompt:** "Evaluate the skills in this plugin. I won't be around to approve anything you would run,
     so note what you would run instead of running it."
   - **`allowed_tools`:** `[Read, Glob, Grep, Skill, Write, Edit, Bash]`.

   Graders:
   - `used-skill`;
   - `wrote-trigger-cases`: a `file_exists` for `evals/trigger/**/prompt.md`, because the skill writes the
     suite under the plugin's `evals/` directory;
   - `did-not-run`: a `tool_used` grader with `tool: Bash`, `input_match: 'plugin eval'`, `min: 0`, `max: 0`
     and `arm: both`, because the skill's hard rule 3 forbids running without agreement;
   - `defects`: an `llm` grader on the last message. It passes when the reply reports all four planted
     defects from `EXPECTED.md` section 16, and says the suite was written but not run. It fails when any
     defect is missing, a defect is invented, the skill is edited, or the suite is reported as having run.
6. **The cases are ordinary repository content.**
   - Add the three behavior cases to `SCAFFOLDS` in `tools/build_eval_scaffolds.py`, and generate their
     `scaffold.sh` files with it.
   - `tools/test_eval_scaffolds.py` and `tools/test_eval_frontmatter.py` must pass unchanged.
   - Add a short "Evals" section to `plugins/review/README.md` and `plugins/skill-authoring/README.md`. Give
     the case counts and the run commands, in the same form as `plugins/testing/README.md`.
   - No plugin version changes. Eval cases and READMEs are not skill behavior, as in plan 10 and
     eurus-labs/Skills#85.
7. **Running the cases is the planner's.** `claude plugin eval` needs `--trust-plugin` in this environment,
   and only the user grants it.
   - The coder writes the cases and checks their format with the repository's tests. It never runs
     `claude plugin eval`.
   - During review, the planner runs:
     - the two plugins' trigger suites with `--ablation none`;
     - the three behavior cases with both arms;
     - on `--model claude-sonnet-5-5 --judge-model haiku`, with a cost ceiling the user agrees to.
   - The results go into `doc/eval-results.md`, written by the coder from the planner's numbers, as with
     plan 18.
   - Add a line to `CHANGELOG.md` under `[Unreleased]` `### Changed`, extending the existing "Eval results"
     bullet. Do not add a new bullet.

## Scope

In:

- `plugins/review/evals/trigger/` (6 new cases) and `plugins/review/evals/behavior/` (2 new cases).
- `plugins/skill-authoring/evals/trigger/` (3 new cases) and `plugins/skill-authoring/evals/behavior/` (1 new
  case).
- `fixtures/16-flawed-skill/`, `fixtures/EXPECTED.md` section 16, and the scenario table in `fixtures/README.md`.
- `tools/build_eval_scaffolds.py`: the three new mappings.
- The two plugin READMEs' "Evals" sections.
- `doc/eval-results.md` and the `CHANGELOG.md` line (Decision 7).

Out:

- **Any `SKILL.md` or script.** If a case shows a skill problem, it is recorded, not fixed.
- **Existing fixtures 01–15 and their answer keys.**
- **The `review-ui` cases.**
- **Plugin versions.**
- **Running the evals by the coder.**

## Baseline

| Existing | Keep, change, or remove |
| --- | --- |
| `plugins/review/evals/trigger/review-ui-*` (3 cases) | Keep; the format for Decision 1 |
| `plugins/testing/evals/behavior/review-tests-finds-weak-suite` | Format for Decisions 2–3: prompt, regex "untouched" grader, llm findings grader |
| `fixtures/04-security/`, `fixtures/05-mixed-monorepo/` and their `EXPECTED.md` sections 04 and 05 | Read only; the answer keys for Decisions 2–3 |
| `tools/build_eval_scaffolds.py` `SCAFFOLDS` | Add three entries |
| `tools/test_eval_scaffolds.py`, `tools/test_eval_frontmatter.py` | Must pass unchanged |
| `plugins/skill-authoring/skills/evaluate-skill/SKILL.md`: hard rule 3 ("With no one to ask, write the suite and report it `not run`"); suite layout under `evals/` | Read only; source of Decision 5's graders |
| `doc/eval-results.md` "Lessons from the redesign": `focus: files` sends names only; `with-only` graders are not scored | Apply |

## Tech stack and constraints

Default. Case files are Markdown with YAML frontmatter, and scaffolds are generated shell. No new
dependency.

## Acceptance criteria

- [ ] **Twelve new case directories exist.** Six trigger and two behavior under `plugins/review/evals/`;
      three trigger and one behavior under `plugins/skill-authoring/evals/`. Prompts and graders follow
      Decisions 1–5. Checked by listing them, and by reading.
- [ ] **No trigger prompt names a file.** Running
      `grep -rln "\.py\|\.md\|\.json" plugins/review/evals/trigger plugins/skill-authoring/evals/trigger --include=prompt.md`
      lists no new case.
- [ ] **No grader uses `focus: files`.** Checked by `grep -rn "focus: files" plugins/*/evals`, which prints
      nothing.
- [ ] **Fixture 16.** It holds the four defects of Decision 4 and nothing else wrong. `EXPECTED.md` section 16
      lists them, and its `README.md` does not. Checked by reading, and by `python3 tools/validate.py`
      passing.
- [ ] **Scaffolds are generated.** `python3 tools/build_eval_scaffolds.py --check` exits 0, and
      `python3 tools/test_eval_scaffolds.py` passes.
- [ ] **Failure case: the answer key stays out of the workspace.** No `scaffold.sh` contains `EXPECTED` or the
      fixture's `README.md`. Checked by `grep -l "EXPECTED\|README" plugins/*/evals/behavior/*/scaffold.sh`
      listing none of the three new cases.
- [ ] **Planner's run, by the planner during review.** The trigger suites and the three behavior cases have
      been run, and their scores are recorded in `doc/eval-results.md`. A failing case is recorded with what
      its trace shows, not hidden.
- [ ] **Required checks pass:** `python3 tools/validate.py`, `python3 tools/materialize.py --check`, and
      `for t in tools/test_*.py; do python3 "$t" || break; done`.

## Risks

| Risk | How it is handled |
| --- | --- |
| A grader passes for the wrong reason, as `focus: files` did | Content graders read the reply or a named file (Decisions 2, 3 and 5). The planner reads each failing trace before recording a score |
| The `setup-review-rules` grader is too strict on wording | The criteria state the outcome (commands scoped per package, nothing invented), not exact text |
| Fixture 16 breaks repository validation, or is mistaken for a real plugin | It is not in any marketplace file. Decision 4 stops the coder if `validate.py` scans `fixtures/` |
| The `evaluate-skill` sandbox cannot run `claude` at all, so `did-not-run` passes trivially | The `defects` grader also needs the reply to say "not run", and the planner checks the trace |
| A sibling skill in another plugin is what should fire for a quiet case | Only "this skill stays quiet" is graded; the case does not require the sibling |
| Behavior runs cost more than expected | The planner proposes a ceiling to the user before running (Decision 7) |

## Open questions

None.
