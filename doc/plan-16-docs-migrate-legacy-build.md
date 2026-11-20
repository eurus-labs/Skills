# Plan 16 — `pipeline.py migrate`: carry an older build forward without inheriting approval (plan 4, W6 part 1)

Status: draft
Date: 2026-11-20
Branch: `feat/docs-migrate-legacy-build`
Baseline: `origin/main` at `48371e031b17e39a9c27c2a7177ebea09f76c101`
Target: `shared/scripts/pipeline.py`, a new `shared/scripts/migrate_build.py`, their plugin copies,
`plugins/docs/shared.manifest`, `plugins/docs/skills/document-codebase/` (`SKILL.md`, `references/pipeline.md`,
`references/schemas.md`), `doc/plan-4-documentation-review-workflow.md`, the `docs` version, tests

## Goal

Three artifacts of an older `.docs-build/` are now refused, with a message saying "migrate", but nothing
migrates them:

| Artifact | How it is refused | Where |
| --- | --- | --- |
| A `manual_version: 1` answer file | refused | `manual.py` `build()` and `read_answer()` |
| A v1 review row `{"page", "block", "verdict": "ok"}` | refused | `review_records.py` `malformed()` |
| A `seal_version` 1 publish seal | refused | `promote_docs.py` |

A user who wrote answers under the old format can only start over and lose that work, or edit JSON by hand.

When this is done, `pipeline.py migrate`:

- reports what an older build holds and what it would change, writing nothing;
- with `--apply`, rewrites those files in the current format;
- keeps every original beside the new file, and preserves every answer text, citation and verified id;
- turns every old approval into "review pending", never into an approval.

Plan 4's migration rules apply as written (`doc/plan-4-documentation-review-workflow.md`, "Migration and
compatibility"). The end-to-end evaluation is plan 17.

## Decisions

1. **A `migrate` component, dry run by default** (the user's choice, 2026-11-20).
   - `pipeline.py migrate [--build B] [--review R]` prints one line per legacy artifact: its path, its
     version, and what `--apply` would write. It writes nothing and exits 0.
   - `pipeline.py migrate --apply` writes the migrated files.
   - Like `status` and `resume`, it is handled ahead of `build_dir.ensure`, runs no stage and appends nothing
     to `timings.jsonl`.
   - With no build directory, it prints the "no scan yet" line and exits 0.

   Rejected: documentation-only migration (the user's choice), and migrating automatically when a stage
   meets an old file. The user should see what changes before it changes.
2. **The logic lives in `shared/scripts/migrate_build.py`**, a top-level module beside `build_dir.py` and
   `draft_artifact.py`, with pure functions `migrate_manual(content)`, `migrate_reviews(rows)` and `plan(build,
   review)`.
   - `pipeline.py` calls it and does the file I/O.
   - Add the module to `plugins/docs/shared.manifest` and run `tools/materialize.py`.

   Rejected: putting the logic in `manual.py` and `review_records.py`. Those modules define the current
   format; carrying the old one inside them would blur which version they accept.
3. **Mapping a `manual_version` 1 answer file to version 2.**
   - **Status to basis and completeness:**

     | v1 `status` | v2 `basis` | v2 `completeness` |
     | --- | --- | --- |
     | `confirmed` | `observed` | `partial` |
     | `inferred` | `inferred` | `partial` |
     | `unknown` | `unknown` | `unanswered` |
     | `not_applicable` | `not_applicable` | `unanswered` |

   - **Carried unchanged:** `text`, `evidence` and `verified_ids`. Every answer gets `content_review: "pending"`,
     and no other field is added or dropped.
   - **Why `observed`:** a v1 `confirmed` answer had to name a verified id (`manual.py` before `a6b0733`, line
     376), which is the bar v2 sets for `observed`.
   - **Why never `complete`:** v1 never recorded which facets an answer covered, so a migrated answer is
     never `complete`.
   - **`pages`, `index_hash` and `template`:** `pages` and its sections (`heading`, `body`, `answers`,
     `evidence`, `verified_ids`) have the same shape in both versions and are carried unchanged. So are
     `index_hash` and `template`.
   - **Version fields:** `manual_version` becomes 2. `template_hash` is set only if the v1 file had one.
     `manual.py` already treats a missing one as the current template.
   - **Answers that would not pass:** the migrated file must pass `read_answer()` for every answer that was
     valid under v1. An answer that would not pass is migrated as it is and listed in the report with
     `read_answer()`'s message. Two examples: a `confirmed` answer whose verified id no longer exists in this
     run, and evidence beyond the end of a file that has changed. Such an answer is not dropped, and it is not
     weakened to make it pass.
4. **Migrating v1 review rows.** A row whose `review_version` is missing or 1 is moved to
   `prose-review.v1.jsonl`, beside the review file. Rows that `review_records.malformed()` already accepts stay
   in the review file, in their order.
   - No v2 row is written for a v1 row, so every block it named is unreviewed: "review-pending" is the
     absence of a bound review (`schemas.md`, "Migrating v1 rows").
   - The review file is the `--review` path when given, else `<build>/prose-review.jsonl` when it exists.
   - The archived `review-KK.jsonl` files under `drafts/rev-NNNN.meta/` are history and are never rewritten.

   Rejected: converting a v1 `ok` into a v2 row with `verdict: changes_requested` or a placeholder hash,
   because any v2 row asserts that someone looked at a bound piece of content.
5. **A `seal_version` 1 seal** is renamed to `publish-seal.v1.json`, and `review` must run again, as
   `promote_docs.py` already says. Nothing is written in its place.
6. **Originals are kept, and a migration happens once.**
   - Each rewritten file's original is saved beside it with `.v1` before the extension: `manual-analysis.v1.json`,
     `prose-review.v1.jsonl`, `publish-seal.v1.json`.
   - If that name already exists with different content, `--apply` refuses the whole migration and names the
     file.
   - All new files are written to temporary names first and renamed only after every one succeeded, so a
     failure leaves the build as it was.
   - A second `migrate` on a migrated build prints `nothing to migrate` and exits 0.
7. **What `migrate` reports but does not rewrite.** These are regenerated by a rerun, so `migrate` names the
   command instead of editing them:
   - a build with a scan but no `scope.json`, which predates plan 14: run `survey`;
   - a build with rendered output but no `drafts/`, which predates plan 12: run `render`;
   - a render manifest of an older version: run `render`.

   It also says that P1–P4 decisions bound to inputs the migration changed will read as stale, which is
   intended.
8. **`status` and `resume` point to it.** When the build holds any artifact of Decisions 3–5, `status` and
   `resume` print one line:

   ```text
   legacy     N file(s) from an older version -- run `migrate` to see what changes
   ```

   Both stay read-only.
9. **Docs and version.**
   - `references/pipeline.md`: the `migrate` component.
   - `references/schemas.md`, "Migrating v1 rows": name the command and the `.v1` files.
   - `SKILL.md`: one line in the run steps, "a build from an older version: run `migrate` first".
   - `doc/plan-4-documentation-review-workflow.md`:
     - the W6 row becomes "Migration done by plan 16; the end-to-end evaluation is plan 17";
     - the header's stale line "W2 is drafted as plan 14 on `feat/docs-product-scope`" becomes "W2 is done by
       plan 14".
   - The `docs` version takes the next minor version above the one on `main` when this is implemented: 1.8.0
     if plan 15 has shipped 1.7.1. Add a `### Added` entry under `[Unreleased]`.

## Scope

In:

- `shared/scripts/migrate_build.py` (new), and `shared/scripts/pipeline.py` (the component, its arguments,
  and the `status` and `resume` line).
- `plugins/docs/shared.manifest` and the regenerated plugin copies.
- The docs listed in Decision 9, and `CHANGELOG.md`.
- The `docs` version, in both `plugin.json` copies and both `marketplace.json` entries.
- A new `tools/test_migrate_build.py`, and `tools/test_pipeline.py` for the `status` and `resume` line.

Out:

- **The end-to-end evaluation.** That is plan 17.
- **Any change to the current formats**, `REVIEW_VERSION`, `MANUAL_VERSION`, `seal_version` or
  `BOUND_INPUTS`.
- **Telling generated v1 prefill prose apart from authored prose.** Plan 4 forbids guessing. Every migrated
  answer is pending review, and the Reviewer judges its text like any other.
- **Migrating `module-analysis.jsonl`, `authored.jsonl` or `scope.json`.** Each is still at its first version.
- **`fixtures/`, and released `CHANGELOG.md` sections.**

## Baseline

| Existing | Keep, change, or remove |
| --- | --- |
| `manual.py:761` `build()` refuses `manual_version` 1 and says "Migrate it rather than relabelling it" | Keep. The refusal now names `pipeline.py migrate` |
| `manual.py:308` `read_answer()` refuses a v1 `status` field | Keep, and reuse it to validate migrated answers (Decision 3) |
| `manual.py:285-292` `BASIS`, `COMPLETENESS`, and the `content_review` rule | Reuse; do not change |
| `manual.py` at `a6b0733^`: v1 answers `{status, text, evidence, verified_ids}` with status in `confirmed`, `inferred`, `unknown`, `not_applicable`; `pages` with sections `{heading, body, answers, evidence, verified_ids}` | Read only, as the source format. Test fixtures are built from it |
| `review_records.py:79` `malformed()` refuses a row that is not `review_version` 2 | Keep, and use it to sort rows (Decision 4) |
| `promote_docs.py:33` refuses a seal that is not version 2 | Keep |
| `pipeline.py:1363` `status`; `resume` (plan 13); both handled ahead of `build_dir.ensure` | Add the line of Decision 8, and the new component on the same path |
| `pipeline.py` `invocation_args`, `next_step` | Reuse for printed commands |
| `references/schemas.md:760` "Migrating v1 rows" | Update per Decision 9 |
| `doc/plan-4-documentation-review-workflow.md:8` and its W6 row at line 210 | Update per Decision 9 |

## Tech stack and constraints

Default: stdlib-only Python 3.9+. Canonical scripts are in `shared/scripts/`, and the plugin copies are
regenerated by `tools/materialize.py`.

## Acceptance criteria

All criteria are tests in `tools/test_migrate_build.py`, unless noted.

- [ ] **Dry run writes nothing.** A build holding a v1 answer file, a review file mixing v1 and v2 rows, and a
      v1 seal prints one line for each. Every file under the build has the same bytes and modification time
      before and after, and `timings.jsonl` is not appended.
- [ ] **Answer mapping.** After `--apply`, each v1 status maps as Decision 3 says. Every `text`, `evidence` and
      `verified_ids` is byte-identical, `pages` is unchanged, no answer is `complete`, and every answer is
      `content_review: pending`. `manual.read_answer()` accepts each answer that had a valid verified id.
- [ ] **Failure case: an answer that no longer validates.** A `confirmed` answer whose verified id is unknown
      to the run is kept with its text and evidence, and the report names it with `read_answer()`'s message.
      Nothing is dropped and no basis is weakened.
- [ ] **Reviews.** The v1 rows are in `prose-review.v1.jsonl` exactly as they were. The review file keeps only
      the v2 rows, in their order. After `--apply`, `review_records` reads the file without error, and no
      block a v1 row named counts as reviewed.
- [ ] **Seal.** `publish-seal.json` v1 is now `publish-seal.v1.json`. `publish` refuses with its "run review
      again" message, which is the existing message.
- [ ] **Originals and atomicity.** The original of each rewritten file is kept with `.v1`. A pre-existing
      `.v1` file with different content makes `--apply` exit non-zero, name the file and change nothing. A
      second `migrate` prints `nothing to migrate`.
- [ ] **Reports without rewrites.** A build with no `scope.json` names `survey`. One with no `drafts/` names
      `render`. Neither file is created.
- [ ] **No build.** `migrate` with no build directory exits 0, prints the "no scan yet" line and creates no
      directory.
- [ ] **Pointer.** `status` and `resume` print the `legacy` line for a build with a v1 artifact, and not for a
      current build. Checked in `tools/test_pipeline.py`.
- [ ] **The refusal names the command.** `manual.py`'s `manual_version` 1 message contains
      `pipeline.py migrate`. Checked in `tools/test_manual_preset.py`.
- [ ] **Docs.** Running `grep -n "migrate" plugins/docs/skills/document-codebase/references/pipeline.md plugins/docs/skills/document-codebase/SKILL.md`
      shows the component and the run step, and plan 4's W6 row and header line are updated. Checked by that
      command and by reading.
- [ ] **Required checks pass:** `python3 tools/validate.py`, `python3 tools/materialize.py --check`, and
      `for t in tools/test_*.py; do python3 "$t" || break; done`.

## Risks

| Risk | How it is handled |
| --- | --- |
| A migrated `observed` reads as more certain than the old `confirmed` was | It carries the same bar, a verified id (Decision 3). It is `partial`, and pending review, so nothing reaches `complete` or `confirmed` without a Reviewer |
| v1 prefill prose survives the migration and looks authored | Every migrated answer is pending, and the Reviewer judges its text (Scope, Out). The report counts migrated answers so the Reviewer knows how many |
| A half-written migration corrupts a build | Temporary files, renamed only after all succeed; the originals are kept (Decision 6) |
| An old build holds a v1 format this plan does not know | The dry run lists every file with an unrecognised version as `unknown version: not migrated`, and `--apply` leaves it untouched |
| The v1 fixture in the tests drifts from what v1 really wrote | Build it from `manual.py` at `a6b0733^` (Baseline) and say so in the test |
| The coder run is cut off | Push after Decisions 1–3, then 4–6, then 7–9 |

## Open questions

None.
