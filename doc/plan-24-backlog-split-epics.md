# Plan 24 — move the epic split into a new `backlog` plugin as `split-epics`

Status: implemented
Date: 2026-11-26
Branch: `feat/backlog-split-epics`
Baseline: `origin/main` at `c24e3eb106ec68015b519fc78e883466d6813cdd` (marketplace 0.5.0)
Target: a new plugin `plugins/backlog/` with the skill `split-epics`; `analyze-requirements` in `reasoning`;
`shared/`; the marketplaces, catalog, `CHANGELOG.md`, fixtures and evals

## Goal

`analyze-requirements` (`reasoning` 0.4.0, released in marketplace 0.5.0) does three jobs:

1. it compares requirement versions;
2. it updates the analysis from each DoU;
3. it splits the result into epics.

The user wants the third job moved out for two reasons (2026-11-26):

- **The skill does too much.** One skill per job triggers more precisely. Today "tách epic" and "compare this
  requirement" fire the same skill.
- **The epic work will grow** into stories, estimation and a Jira export, which is backlog management rather
  than requirement analysis.

When this is done:

- a new plugin, **`backlog`**, holds a skill **`split-epics`**. It reads a topic folder's `analysis.md`, written
  by `analyze-requirements` or by hand in the same format, and writes `epics.md` under the same rules as today;
- `analyze-requirements` no longer writes epics. When the open points are settled it says so and names
  `split-epics` in the `backlog` plugin;
- both skills validate their files with the same `requirements.py`, authored once in `shared/` and copied into
  each.

## Decisions

1. **A new plugin, `backlog`** (the user's choice of a new plugin, 2026-11-26; the name `backlog` is proposed
   here and can change at approval).
   - It is version `0.1.0`, with both `plugin.json` copies, a README, entries in both marketplace copies, and
     a root catalog row.
   - Its description says it turns settled requirements into a delivery backlog, epics for now.
   - Rejected: a skill inside `reasoning`. That would not give the growing backlog work its own install, and
     the user picked a plugin.
2. **`split-epics` must work standalone.** Plugins install separately, so its `SKILL.md` states the rules
   itself and links nothing outside its own folder.
   - **Input:** a topic folder (`requirements/<topic>/` by default) holding `analysis.md` in the documented
     format. The format is described in its own `references/analysis-format.md`, with the tables and columns
     it reads.
   - **No `analysis.md`:** the skill says so, and names `analyze-requirements` in the `reasoning` plugin as the
     usual way to make one. It does not write an analysis itself.
   - **Other inputs** (a PRD, a spec, a plan) are out of scope for this plan, because the user did not choose
     that reason. They may come later.
3. **The epic rules move unchanged** from `analyze-requirements` (its hard rules 3 and 7, its Split epics steps,
   and `references/epics-template.md`):
   - epics only when no blocking open point is `open`;
   - otherwise list the blocking points and stop, unless the user explicitly asks, in which case the file is
     headed `Provisional` and each dependent epic names its open point;
   - every in-scope requirement is in exactly one epic, or in "Not in any epic" with a reason;
   - each epic has a goal, R- IDs, acceptance criteria (with a negative case), dependencies, risks and code
     areas;
   - a traceability table;
   - never edit `analysis.md` or a DoU. A requirement that looks wrong while splitting becomes a note for the
     user to take back to `analyze-requirements`;
   - run `check` after writing.
4. **`analyze-requirements` drops the step** (`reasoning` 0.4.0 → **0.5.0**).
   - Remove from it:
     - the Split epics step and hard rules 3 and 7;
     - `references/epics-template.md`;
     - "split this into epics" and "tách epic" from its description and "When to use".
   - Add to "When not to use" and to the description: "To split the analysis into epics, use `split-epics`
     from the `backlog` plugin."
   - At the end of Update from a DoU, when no blocking point is open, its report says the analysis is ready
     for `split-epics`.
   - It never writes `epics.md`. This is a **breaking change** for `reasoning` users, and it goes under
     `### Breaking changes` in `CHANGELOG.md`: install `backlog` to keep splitting epics.
   - Update the `reasoning` README and description, and its root catalog row.
5. **One script, authored in `shared/`.**
   - Move `requirements.py` to `shared/scripts/requirements/requirements.py`, unchanged in behavior.
   - Copy it with `tools/materialize.py` into `plugins/reasoning/skills/analyze-requirements/scripts/` and
     `plugins/backlog/skills/split-epics/scripts/`, through each plugin's `shared.manifest`. This follows the
     pattern of `plugins/docs/shared.manifest`.
   - `check` keeps every rule. The epics rules apply only when `epics.md` exists, which is what they do
     today.
   - `references/diff-output.md` is split: the `diff` part stays with `analyze-requirements`, and the `check`
     messages that concern epics go to `split-epics`.
   - Point `tools/test_requirements_script.py` at the shared source.
6. **Evals.**
   - **`backlog` trigger cases.** Two must fire: "Split this requirement analysis into epics" and "Tách epic
     từ requirement analysis này". One must stay quiet: "Compare this requirement with the previous
     version", which belongs to `analyze-requirements`.
   - **`reasoning` trigger cases.**
     - Add a quiet case: "Split the requirement analysis into epics" must not fire `analyze-requirements`.
     - The existing fire case `analyze-requirements-compare-versions` stays.
     - Check the existing `analyze-requirements-update-from-dou` case still fires.
   - **Two `backlog` behavior cases on a new fixture 18, `fixtures/18-settled-analysis/`.** The fixture holds
     `requirements/export/analysis.md` and `dou-001.md` in the documented format, plus the code it cites.
     - **`split-epics-from-settled-analysis`:** every blocking point is resolved, and one non-blocking point
       stays open. Graders:
       - `used-skill` (with-only);
       - `epics.md` is written;
       - an `llm` grader on `epics.md`, which requires every in-scope R- ID in exactly one epic, the
         out-of-scope one in "Not in any epic", acceptance criteria per epic, and no edit to `analysis.md`.
     - **`split-epics-refuses-while-blocked`:** the same fixture with one blocking point left `open`, as a
       second scaffold from a variant of `analysis.md`. Graders:
       - `used-skill`;
       - `epics.md` is not written;
       - an `llm` grader on the last message, which requires the blocking point to be named and no epics to
         be produced.
   - Add `EXPECTED.md` §18 and a `fixtures/README.md` row.
   - The existing `analyze-requirements-flags-planted-changes` case keeps its `no-epics` grader, and must
     still pass.
   - The planner runs everything during review, with a cost ceiling the user agrees to. The coder records the
     results in `doc/eval-results.md`.
7. **Release.** No marketplace release in this plan. The next release PR will carry `backlog` 0.1.0 and
   `reasoning` 0.5.0.

## Scope

In:

- `plugins/backlog/`: both manifests, the README, `shared.manifest`, and `skills/split-epics/`, which holds
  `SKILL.md`, `references/epics-template.md`, `references/analysis-format.md` and the materialized
  `scripts/requirements.py`.
- `plugins/reasoning/`: the `analyze-requirements` edits, its `shared.manifest`, the version, the README and
  the description.
- `shared/scripts/requirements/requirements.py`, moved there, and `tools/test_requirements_script.py`.
- Both marketplace copies, the root catalog, and `CHANGELOG.md` (`[Unreleased]`: Breaking changes and Added).
- Fixture 18, `EXPECTED.md` §18, the `fixtures/README.md` row, the eval cases and the scaffolds.

Out:

- **Stories, estimation, a Jira or CSV export**, and inputs other than `analysis.md`. These are later plans.
- **Any change to how `analyze-requirements` analyses or handles a DoU.**
- **A marketplace release.**

## Baseline

| Existing | Keep, change, or remove |
| --- | --- |
| `analyze-requirements/SKILL.md`: hard rules 3 and 7, the Split epics steps, the "tách epic" triggers | Move to `split-epics`, and remove here |
| `analyze-requirements/references/epics-template.md` | Move to `split-epics` |
| `analyze-requirements/scripts/requirements.py` | Move to `shared/` and materialize into both skills |
| `analyze-requirements/references/diff-output.md` | Split by topic (Decision 5) |
| `plugins/docs/shared.manifest` and `tools/materialize.py` | The pattern for the new manifests |
| `tools/test_requirements_script.py` | Repoint at the shared source; all tests still pass |
| `plugins/reasoning/evals/behavior/analyze-requirements-flags-planted-changes` (`no-epics` grader) | Keep; it must still pass |
| `fixtures/17-requirement-change/` | Keep; fixture 18 is new |

## Tech stack and constraints

Default. `requirements.py` stays stdlib-only Python 3.9 or later, with no network call and no writes. A
generated copy is never hand-edited.

## Acceptance criteria

- [ ] **The plugin installs.** `python3 tools/validate.py` passes with 9 plugins. `backlog` is 0.1.0 and
      `reasoning` is 0.5.0 in all their version files.
- [ ] **One script source.** `python3 tools/materialize.py --check` passes, and both skills' copies of
      `requirements.py` are generated from `shared/`. `tools/test_requirements_script.py` passes unchanged in
      what it asserts.
- [ ] **`analyze-requirements` no longer splits epics.**
      `grep -n "epics.md\|tách epic\|Split epics" plugins/reasoning/skills/analyze-requirements/SKILL.md`
      shows only the hand-off lines to `split-epics`.
- [ ] **`split-epics` is self-contained.** Its `SKILL.md` links nothing outside `plugins/backlog/`, and it
      states every rule of Decision 3. Checked by reading, and by `validate.py`.
- [ ] **The breaking change is recorded** under `### Breaking changes` in `[Unreleased]`.
- [ ] **Failure case, `split-epics-refuses-while-blocked`.** With the plugin, no run writes `epics.md`, and
      each run names the blocking point. Checked by the planner's run.
- [ ] **Triggers separate.**
  - Run the `backlog` trigger cases and the `reasoning` trigger suite: `split-epics` fires on the epic
    requests, and `analyze-requirements` stays quiet on them.
  - `analyze-requirements-flags-planted-changes` still passes.

  Checked by the planner's run.
- [ ] **Required checks pass:** `python3 tools/validate.py`, `python3 tools/materialize.py --check`,
      `python3 tools/build_eval_scaffolds.py --check`, and
      `for t in tools/test_*.py; do python3 "$t" || break; done`.

## Risks

| Risk | How it is handled |
| --- | --- |
| A `reasoning` user loses epic splitting after updating | Recorded as a breaking change. `analyze-requirements` names `split-epics` and its plugin whenever epics are asked for |
| The two skills drift apart on the file format | One script in `shared/`, and `split-epics` documents the format it reads in its own reference |
| Both skills fire on "tách epic" | Removed from `analyze-requirements`'s description, plus a quiet case in each suite |
| `split-epics` is used on an analysis written by hand in the wrong shape | `check` names the line, and the skill stops and reports instead of guessing |

## Open questions

None.
