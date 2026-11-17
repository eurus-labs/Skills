# Plan 12 — immutable draft revisions for `document-codebase` (plan 4, W5 part 1)

Status: draft
Date: 2026-11-17
Branch: `feat/docs-draft-revisions`
Baseline: `origin/main` at `24169e440ba0e772d519a65d5762b14b05ec7922`
Target: `shared/scripts/` (`pipeline.py`, `render/`, `review/`, `publish/check_prose.py`,
`publish/promote_docs.py`), their plugin copies, `plugins/docs/skills/document-codebase/references/`, tests

## Goal

Plan 4's W5 asks that every rendered draft is kept as an immutable revision, so that:

- a reviewer's verdict says which revision it judged;
- the history of each review round survives the next round;
- only the revision that passed review can be delivered.

Today the driver keeps **one** draft:

- `render` deletes and rebuilds `.docs-build/rendered-docs/` (`render/prepare_stage.py`).
- `render-manifest.json` records only that tree's hash.
- The review queue's `draft_revision` is really the source revision or index hash
  (`publish/check_prose.py:434`), while the references show `rev-0001`.
- Each review round overwrites `prose-report.json`, so the findings of the round before are lost.

The user split W5 in two:

- **Plan 12 (this plan):** revision snapshots, review history, and binding delivery to a revision.
- **Plan 13 (later):** a read-only resume command, built on the records this plan writes. Plan 13 also covers
  the "same blocking findings two rounds running" report.

## Decisions

1. **A revision is minted by `render`, after `snapshot_draft.py`.** A new stage, `render/snapshot_revision.py`,
   runs as the last `render` stage.
   - It compares the staging tree's `tree_hash` with the latest revision's.
   - If they differ, or there is no revision yet, it copies the staging tree to
     `.docs-build/drafts/rev-NNNN/`, where `NNNN` is one more than the highest number ever used, zero-padded
     to 4.
   - If they are equal, it mints nothing and reuses the latest revision. A re-render that changes nothing is
     not a new revision.
   - It records the revision id in `render-manifest.json` (field `revision`; `render_manifest_version` 2).

   Rejected: minting at `review`, because a reviewer must be able to read the exact tree before reviewing it
   (plan 4, lifecycle step 4).
2. **Numbers are never reused**, including after a rescan or after pruning. The highest number ever used is
   kept in `.docs-build/drafts/counter.json`. Pruning (Decision 6) removes directories but never lowers the
   counter.
3. **Metadata sits beside the snapshot, never inside it.** The snapshot is `drafts/rev-NNNN/`, a copy of the
   rendered tree and nothing else. Its records go in `drafts/rev-NNNN.meta/`:
   - `revision.json`: `revision_version` 1, `revision`, `draft_hash`, `doc_hash`, `created_at`, and
     `previous` (the prior revision id or null);
   - the review history of Decision 5.

   Writing into `rev-NNNN/` would change its `tree_hash`. The tree hash excludes `_build`, as
   `draft_artifact.tree_hash` does today.
4. **Immutability is checked, not trusted.** A function `verify_revision(drafts, rev)` in
   `draft_artifact.py` recomputes the snapshot's `tree_hash` and compares it with `revision.json`'s
   `draft_hash`. Both `seal_draft.py` and `promote_docs.py` call it and fail on a mismatch, with a message
   that names the revision. No script writes into an existing `rev-NNNN/` directory.
5. **Review history is kept per revision.**
   - When `review` runs with `--review FILE`, the driver copies `FILE` to
     `drafts/rev-NNNN.meta/review-KK.jsonl`. `KK` counts the review rounds on that revision: 01, 02, and so on.
   - After `check_prose.py`, it copies `prose-report.json` to `drafts/rev-NNNN.meta/prose-report-KK.json`.
   - `KK` is the next free number, so nothing is overwritten.
   - The working files `prose-review.jsonl` and `prose-report.json` keep their current names and roles.
6. **Retention: keep the N most recent revisions** (the user's choice). `render` takes `--keep-revisions N`,
   default 5, minimum 3. Plan 13's no-progress report compares the last revisions, so 3 is the lowest number
   that keeps two rounds' findings.
   - After minting, `snapshot_revision.py` deletes the oldest `rev-NNNN/` and `rev-NNNN.meta/` pairs beyond N.
   - It never deletes the latest revision, or the revision named in `publish-seal.json`.
   - It prints what it removed.

   Rejected: keeping every revision. The user chose a cap, because each revision is a full copy of the docs
   tree.
7. **The review queue names the revision; freshness stays on hashes.**
   - `check_prose.py` takes `--draft-revision` and writes it as each queue entry's `draft_revision`. The
     driver passes the revision from `render-manifest.json`.
   - Without the flag, the old value (source revision, then index hash) remains as the fallback.
   - `draft_revision` stays **out** of `review_records.BOUND_INPUTS` and out of `content_hash`. An unchanged
     section therefore keeps its approval across revisions (plan 4, lifecycle step 7).
   - A review row carrying an old-style `draft_revision`, such as a source revision, is still valid.
8. **The P4 queue identity ignores the revision label.** `pipeline.review_queue_hash` hashes each queue
   entry without its `draft_revision`. Otherwise every re-render would re-open P4 for readings whose content
   did not change.
9. **Delivery is bound to one revision.**
   - `seal_draft.py` adds `revision` to the seal (`seal_version` 2), after checking:
     - the staging tree hash equals that revision's `draft_hash`;
     - `verify_revision` passes.
   - `promote_docs.py` refuses unless all of these hold:
     - the seal is version 2;
     - its revision exists and passes `verify_revision`;
     - the staging tree hash equals the revision's `draft_hash`.
   - A v1 seal is refused with "run review again".

   So a draft that was re-rendered after review cannot be published: it is a new revision with no seal.
   Plan 4 scenario 7: only the reviewed revision can be delivered.
10. **Documentation in the same change:**
    - `workflow.md`: the "Not yet implemented" section now says that snapshots exist (plan 12) and that only
      resume is still missing (plan 13).
    - `pipeline.md`: the `drafts/` layout and `--keep-revisions`.
    - `schemas.md`: `render_manifest_version` 2, `seal_version` 2 and `revision_version` 1.
    - `prose-rules.md` and `reviewer.md`: copy `draft_revision` from the queue, which now reads `rev-NNNN`.
    - Plan 4's W5 row becomes "Partial: snapshots, review history and delivery binding done by plan 12;
      resume pending (plan 13)".
11. **Version.** `docs` 1.4.0 → 1.5.0 in all manifests, with a `### Changed` entry under `[Unreleased]` in
    `CHANGELOG.md`. Edit canonical scripts in `shared/scripts/` only, register the new script in
    `plugins/docs/shared.manifest`, and regenerate the copies with `python3 tools/materialize.py`.

## Scope

In:

- New: `shared/scripts/render/snapshot_revision.py`.
- Changed:
  - `shared/scripts/draft_artifact.py` (`verify_revision`);
  - `shared/scripts/pipeline.py`:
    - `render` stages and `--keep-revisions`;
    - `review`, which passes `--draft-revision` and copies the history files;
    - `review_queue_hash`;
  - `shared/scripts/review/seal_draft.py`;
  - `shared/scripts/publish/check_prose.py`;
  - `shared/scripts/publish/promote_docs.py`.
- `plugins/docs/shared.manifest` and the regenerated plugin copies.
- The references in Decision 10, the `docs` version, and `CHANGELOG.md`.
- Tests: extend `tools/test_pipeline.py`, `tools/test_publish_workflow.py` and `tools/test_prose.py`. Do not
  start a new test framework.

Out:

- The resume command and the no-progress report: plan 13.
- W2 (scope wiring) and W6 (migration and the end-to-end run).
- Changes to `review_records.BOUND_INPUTS`, `content_hash`, or the review row schema (`review_version` 2).
- Promoting from the snapshot directory instead of staging. Staging stays the source for `promote_docs.py`;
  Decision 9 makes it provably equal to the sealed revision.
- `fixtures/`.

## Baseline

| Existing | Keep, change, or remove |
| --- | --- |
| `pipeline.py:571-593` `render`: `prepare_stage`, `render_docs`, `snapshot_draft` → `render-manifest.json` | Keep; add `snapshot_revision.py` last (Decision 1) |
| `render/prepare_stage.py` deletes and recreates staging | Keep; staging is the working tree, and revisions are the history |
| `render/snapshot_draft.py` writes `render_manifest_version` 1 `{draft_hash, doc_hash}` | Keep; `snapshot_revision.py` adds `revision` and sets version 2 |
| `draft_artifact.py` `file_hash`, `tree_hash` (skips `_build`) | Keep; add `verify_revision` |
| `pipeline.py:596-658` `review`: `validate_draft`, `check_prose`, `release_hygiene`, `quality_docs`, `seal_draft` | Keep the order; pass `--draft-revision`; copy history (Decision 5) |
| `check_prose.py:434` `draft_revision = source_revision or index_hash` | Change: `--draft-revision` wins; the old value stays as fallback (Decision 7) |
| `review_records.py:36` `BOUND_INPUTS` excludes `draft_revision` | Keep unchanged (Decision 7) |
| `pipeline.py:950` `review_queue_hash` hashes the whole queue | Change to drop `draft_revision` per entry (Decision 8) |
| `review/seal_draft.py` `seal_version` 1 | Change to version 2 with `revision` (Decision 9) |
| `publish/promote_docs.py` checks seal `draft_hash` and `doc_hash` against staging | Change per Decision 9 |
| `tools/test_prose.py:264` and `tools/test_review_scope_schema.py:26` use `"draft_revision": "rev-0001"` | Keep passing |
| `references/workflow.md:119-124` "Not yet implemented" | Change per Decision 10 |

## Tech stack and constraints

Default: stdlib-only Python 3.9+, canonical scripts in `shared/scripts/`, plugin copies regenerated by
`tools/materialize.py`, and `--dry-run` printing the new stage like the others.

## Acceptance criteria

Each criterion is checked by a test added to the named file. The test names below are suggestions.

- [ ] **Minting.**
      - Rendering twice with the same `doc.json` leaves one revision, `rev-0001`.
      - Changing one block and rendering again creates `rev-0002`, and `rev-0001`'s tree hash is unchanged.

      `tools/test_pipeline.py`.
- [ ] **Numbers and pruning.** With `--keep-revisions 3`, rendering five distinct drafts leaves `rev-0003`
      to `rev-0005`, and the next render mints `rev-0006`, not a reused number. A sealed `rev-0002` survives
      pruning. `tools/test_pipeline.py`.
- [ ] **Failure: tampering.** Editing one file inside `drafts/rev-0001/` makes `promote_docs.py` exit
      non-zero with a message naming `rev-0001`. `tools/test_publish_workflow.py`.
- [ ] **Failure: re-render after review.** Render, then review (seal `rev-0001`), then change a block and
      render again (`rev-0002`). `publish` refuses, and `docs/` is unchanged.
      `tools/test_publish_workflow.py`. This is plan 4 scenarios 7 and 9.
- [ ] **Failure: old seal.** A v1 seal is refused with a message saying to run review again.
      `tools/test_publish_workflow.py`.
- [ ] **Queue label.** After render and review, every `review_queue` entry has `draft_revision` equal to the
      revision in `render-manifest.json`. `review_queue_hash` is the same for two queues that differ only in
      `draft_revision`. `tools/test_prose.py` and `tools/test_pipeline.py`.
- [ ] **Freshness unchanged.** A `confirmed` row for an unchanged block, made on `rev-0001`, still applies on
      `rev-0002`. An edited block's row is stale (P008). A row with `draft_revision` set to a source revision
      string is still accepted. `tools/test_prose.py`. This is plan 4 scenario 6.
- [ ] **History.** Two review rounds on one revision leave `review-01.jsonl`, `review-02.jsonl`,
      `prose-report-01.json` and `prose-report-02.json` in `rev-NNNN.meta/`, and nothing inside `rev-NNNN/`.
      `tools/test_pipeline.py`.
- [ ] **Docs.** `grep -n "do not exist\|Not yet implemented" plugins/docs/skills/document-codebase/references/workflow.md`
      shows that only resume is still described as missing. Checked by reading.
- [ ] **Required checks pass:** `python3 tools/validate.py`, `python3 tools/materialize.py --check`, and
      `for t in tools/test_*.py; do python3 "$t" || break; done`.

## Risks

| Risk | How it is handled |
| --- | --- |
| Full copies fill the disk on a large docs tree | The cap from Decision 6 (default 5). The pipeline prints what each prune removed, and `.docs-build/` stays git-ignored |
| A new revision re-opens P4 for unchanged readings | Decision 8 drops the label from the P4 identity |
| Old review rows lose their approval | `draft_revision` is not a freshness input (Decision 7), and a test keeps an old-style row valid |
| An existing run has a v1 seal and is blocked at publish | Intended: the message says to run review again, which writes a v2 seal. W6 owns broader migration |
| The coder run is cut off with work unpushed, as happened twice on 2026-11-17 | The coder pushes after each group of Decisions (1–4, 5–8, 9–11), not only at the end |

## Open questions

None.
