# Plan 21 — `document-codebase`: an analysed file that no page cites makes the run partial

Status: draft
Date: 2026-11-25
Branch: `feat/docs-prose-coverage-gate`
Baseline: `origin/main` at `b26907b82c54ccb7b26ed1e9044003546e400f85`
Target: `shared/scripts/publish/quality_docs.py`, `shared/scripts/survey/build_scope.py`,
`shared/scripts/survey/scope_record.py`, the `document-codebase` references, the `docs` version, `CHANGELOG.md`

## Goal

The quality gate counts a product file as covered once it is `analyzed`. It never checks that any page cites
the file. "0 unread" therefore does not mean "documented".

The plan 17 run on `shared/scripts` shows the gap (`doc/e2e-evaluation.md`, "Candidates for follow-up plans",
item 1):

- All 48 product files were analysed, and the gate raised no coverage reason.
- Recomputed from that build directory on 2026-11-25, with the same citation rule the gate already uses for
  feature areas, **32 of the 48 files are cited by no block on any page**.
- On `layered-repo`, all 6 are cited.

When this is done:

- an analysed product file that no page block cites makes the run `partial`, with a reason that names the
  files;
- a person can mark a file as deliberately left undocumented, with a note. A marked file is reported, but
  does not make the run partial.

## Decisions

1. **"Covered" means cited** (the user's choice, 2026-11-25). A product file is covered when at least one
   block on any page of the document model cites it: through its own `evidence`, a `claim_refs` claim, or an
   `analysis_refs` statement.
   - This is the rule `block_paths` already applies to feature areas (`quality_docs.py:285-299`).
   - Rejected: searching the reader edition's text for the file or module name, which wording defeats.
2. **The files checked** are the rows with `disposition: product` and `reading: analyzed`, after
   `scope_record.sync_reading` (`quality_docs.py:337`).
   - Unread files are already reported as `incomplete`, so they are not listed twice.
   - `empty` files are not `product` and owe nothing (plan 15).
3. **An uncovered file makes the status `partial`**, the same effect as an uncovered feature area
   (`quality_docs.py:361-365`).
   - The reason has this form: `N analysed product file(s) are cited by no page: a.py, b.py, … and K more`,
     with the first 10 named.
   - `generation-report.json` gets `scope.prose_coverage`:
     `{"checked": bool, "analysed": n, "cited": n, "uncited": [paths], "undocumented": [{"path", "note"}]}`.
   - With no document model (`--doc` absent), `checked` is `false`, the lists are empty, and the status is
     unchanged.
   - Refactor the cited-path set into one helper that both this check and `feature_report` call. The
     feature-area behavior must not change.
4. **A person may mark a file as deliberately undocumented** (the user's choice, 2026-11-25).
   - The mark is a new optional field on the file's row in `scope.json`, `"undocumented": "<note>"`. Its note
     says who decided and why, and has at least five words, the same rule as checkpoint notes.
   - A marked, uncited file is listed under `undocumented` and in one non-status reason:
     `N file(s) left undocumented by a person: path (note), …`. It does not make the run partial.
   - A mark whose note is shorter than five words is ignored: the file counts as uncited, and the reason
     adds `(its undocumented note is too short)`.
   - A marked file that a page does cite is simply covered, and the mark is reported as unneeded in that
     same non-status reason.
   - `build_scope.py` keeps the field across a `survey` rerun, the way it keeps `override`
     (`build_scope.py:258-273`). The mark does not change the disposition or the reading. Adding one needs no
     `survey` rerun, because `quality_docs.py` reads `scope.json` directly.
   - **Only a person sets it.** The agent never writes `undocumented` on the user's behalf, even in an
     unattended run. There it leaves the files uncited, so the run stays `partial`, and lists them in its
     handoff.
   - Rejected: a separate exceptions file, which is one more artifact to keep in step with `scope.json`.
5. **Documentation.** Each item is short, in the file that already covers its topic:
   - `references/schemas.md`, the `scope.json` field table: a row for `undocumented`.
   - `references/survey.md`, after the paragraph on narrowing: how to mark a file, and that only a person
     does.
   - Where `SKILL.md` or `references/workflow.md` says what the gate checks: one line on prose coverage, and
     "never write `undocumented` yourself".
   - The skill stays under its size rules.
6. **Version.** `docs` 1.8.0 → **1.9.0**, because the gate now holds more runs at `partial`.
   - Update both `plugin.json` copies and both `marketplace.json` entries.
   - Run `python3 tools/materialize.py` after editing `shared/`.
   - Add a `### Changed` entry under `[Unreleased]` in `CHANGELOG.md`.

## Scope

In:

- `shared/scripts/publish/quality_docs.py`: the check, the helper and the report field.
- `shared/scripts/survey/build_scope.py`: keep `undocumented` across reruns.
- `shared/scripts/survey/scope_record.py`, only if the field needs a constant or a validator there.
- The generated plugin copies, the references and `SKILL.md` lines of Decision 5, the version files and
  `CHANGELOG.md`.
- Tests: `tools/test_product_scope.py` beside the feature-area tests, and `tools/test_quality_gate.py` if the
  report shape is checked there.

Out:

- **Reading depth** (`doc/e2e-evaluation.md` follow-up item 2), and **gap blocks** (item 3).
- **A `pipeline.py` command to set the mark.** It is edited by hand, like `override`.
- **`status` and `resume` output.**
- **The behavior eval case.** Its `layered-repo` run cites all six files, so it is unaffected.
- **Other plugins.**

## Baseline

| Existing | Keep, change, or remove |
| --- | --- |
| `quality_docs.py:285-299` `block_paths`; `:302-332` `feature_report` computes the cited set inline | Extract the cited set into a helper used by both |
| `quality_docs.py:335-371` `scope_report` | Add the prose-coverage check and its reasons |
| `quality_docs.py:759-765`: `scope_report` gets `load_doc(args.doc)` | Keep; it already passes the document model |
| `build_scope.py:258-273`: an `override` survives a rerun | Same for `undocumented` |
| `references/schemas.md` `scope.json` field table (`override` row) | Add the `undocumented` row |
| `references/survey.md` paragraph on narrowing with `override` | Add the marking paragraph after it |
| `tools/test_product_scope.py:700-730`, the feature-area gate tests and their `doc()` helper | Reuse the helper; add the tests below |
| `/root/e2e-runs/shared-scripts/.docs-build` and `/root/e2e-runs/layered-repo/.docs-build` (planner's container, from plan 17) | The planner reruns the gate on them during review |

## Tech stack and constraints

Default: standard-library Python 3.9 or later. Edit `shared/` and regenerate the plugin copies.

## Acceptance criteria

- [ ] **Uncited files make the run partial.** In a scope with three analysed product files and a doc citing
      two, `scope_report` returns `partial`, `uncited` is the third file, and a reason names it. Checked by
      a new test in `tools/test_product_scope.py`.
- [ ] **A citation through a claim or a statement counts**, as for feature areas. Checked by a new test.
- [ ] **A marked file is reported, not partial.** The same scope with the third file marked
      `undocumented` with a note of five or more words gives no partial from this check. That file is
      under `undocumented` with its note, and the non-status reason names it. Checked by a new test.
- [ ] **Failure case: a short note does not excuse a file.** A note of four words leaves the file uncited
      and the run partial, and the reason says the note is too short. Checked by a new test.
- [ ] **No document model, no claim.** With `doc` `None`, `prose_coverage.checked` is `false` and no
      coverage reason is added. Checked by a new test.
- [ ] **The mark survives a rerun.** `build_scope` with an earlier scope whose row carries `undocumented`
      keeps the field and leaves the disposition and reading unchanged. Checked by a new test.
- [ ] **Unread and empty files are not double-counted.** An unread product file appears under
      `incomplete` only, and an `empty` file is in neither list. Checked by a new test.
- [ ] **Feature-area behavior is unchanged.** The existing tests at `tools/test_product_scope.py:700-730`
      pass unchanged.
- [ ] **No existing test changes its expected status.** If a fixture's expected gate status changes
      because a file is uncited, the coder stops and reports. It does not edit the expectation.
- [ ] **On the plan 17 builds, by the planner during review.** Rerun `quality_docs.py` with the arguments
      recorded in each build. `shared-scripts` turns `partial` with 32 files listed as uncited, and
      `layered-repo` gets no prose-coverage reason.
- [ ] **Version and docs.** `docs` is 1.9.0 in all four files, the references carry Decision 5, and
      `[Unreleased]` has the entry. Checked by `python3 tools/validate.py` and by reading.
- [ ] **Required checks pass:** `python3 tools/validate.py`, `python3 tools/materialize.py --check`, and
      `for t in tools/test_*.py; do python3 "$t" || break; done`.

## Risks

| Risk | How it is handled |
| --- | --- |
| Many real runs turn `partial`, as `shared/scripts` would | Intended: they are not fully documented. The reason names the files, and a person can mark the deliberate ones (Decision 4) |
| The agent marks files itself to get a clean run | Decision 4 forbids it, and the skill says so. The note is reported, so a mark is always visible to the user |
| A file cited only in an audit-only block counts as covered | Accepted for now: it is the same rule as feature areas. Reading depth and the reader edition are follow-up item 2 |
| Existing end-to-end fixtures turn `partial` | The coder stops and reports (Acceptance), so the planner decides with the user instead of a test being bent |

## Open questions

None.
