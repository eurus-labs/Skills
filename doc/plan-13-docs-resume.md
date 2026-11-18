# Plan 13 — resume a `document-codebase` run (plan 4, W5 part 2)

Status: implemented
Date: 2026-11-18
Branch: `feat/docs-resume-command`
Baseline: `origin/main` at `4b8f2f3e2bd3aa535416eaa0725c23978790876d` (plan 12 merged)
Target: `shared/scripts/pipeline.py`, its plugin copy, `plugins/docs/skills/document-codebase/` (`SKILL.md`,
`references/workflow.md`, `references/pipeline.md`), `doc/plan-4-documentation-review-workflow.md`, tests

## Goal

A documentation run often stops before it finishes. Common reasons are:

- the budget runs out;
- the session ends;
- the stop rule fires.

A new session then has to work out where the run stood, which is slow and easy to get wrong. Plan 12 left
the records needed to answer that:

- the `drafts/rev-NNNN/` snapshots;
- `revision.json`;
- the numbered `review-KK.jsonl` and `prose-report-KK.json` files in each `rev-NNNN.meta/`.

Nothing reads them back yet.

When this is done, `pipeline.py resume` prints, without changing anything:

- where the draft-review loop stands;
- every finding still open, and since which revision;
- whether the last two revisions left the same blocking findings open;
- the continuation note the previous session wrote;
- the next command to run.

As the user decided, the script **reports** a stalled loop. The Coordinator **decides** whether to stop.

## Decisions

1. **A read-only `resume` component.**
   - `pipeline.py resume` is handled ahead of `build_dir.ensure`, as `status` is (`pipeline.py`, the `status`
     branch in `main`).
   - It runs no stage and writes nothing, including `timings.jsonl`. It exits 0 whatever state it finds.
   - With no scan, it prints the same "no scan yet … start with survey" line as `status`.

   Rejected: folding this into `status`. `status` answers "where is the whole run" (scan, template,
   checkpoints, analysis); `resume` answers "how do I continue the draft-review loop". Mixing the two makes
   both harder to read.
2. **What `resume` prints, in this order:**
   1. **Revision:** the latest `rev-NNNN`, its `created_at` and `previous`, and whether the staging tree
      still equals it (`tree_hash` against `revision.json`).
   2. **Sealed revision:** the revision named in `publish-seal.json`, if any, and whether it is the latest.
   3. **Review state:** from the latest `prose-report-KK.json` of the latest revision, the counts of queued,
      unreviewed and stale blocks, and the stale block IDs.
   4. **Open findings:** every finding whose `state` is `open` in the latest review file of the latest
      revision, grouped by severity. Each line shows its `finding_id`, `location` and `requested`, and the
      revision where that `finding_id` first appears. To find that revision, scan the `review-KK.jsonl` files
      of the kept revisions, oldest first.
   5. **The no-progress report** (Decision 3).
   6. **The continuation note** (Decision 4).
   7. **Next step:** one suggested command (Decision 5).
3. **The no-progress report.**
   - Take the last review file of each of the two newest revisions that have one.
   - Collect the open `blocking` finding IDs in each.
   - If both sets are non-empty and equal, print `no progress: the same N blocking finding(s) stayed open
     across rev-A and rev-B: <ids>`, followed by `the stop rule in workflow.md applies; the Coordinator
     decides whether to stop`.
   - Otherwise print nothing for this item.
   - It never blocks `render`, `review` or `publish`.

   Rejected: comparing two review rounds on the **same** revision. The workflow's stop rule is about
   revision rounds (`workflow.md`, "Budget and the stop rule"), and re-reviewing an unchanged draft is not a
   repair attempt.
4. **The continuation note is the model's, and the script only shows it.**
   - When the Coordinator stops a run, it writes `.docs-build/continuation.md` in plain prose: iteration,
     budget used, next actions, and anything the records do not hold.
   - `resume` prints that file under the heading `continuation note (written by the previous session, not
     checked)`, together with its modification time and the latest revision's `created_at`.
   - If the note is older than the latest revision, `resume` says so.
   - No script writes, parses or validates the note.

   Rejected: a structured `continuation.json` with budget fields, because the budget and the next actions
   are the model's judgement and a schema would pretend they are checked.
5. **The suggested next step** follows the first rule that applies:
   - no revision: `render`;
   - staging differs from the latest revision: `render`;
   - the latest revision has no review round: `review`;
   - open blocking findings or stale blocks: route the findings (`workflow.md`, "Routing findings"), then
     `render`;
   - P4 open: `decide --checkpoint P4 …`;
   - a seal on the latest revision with a passed generation report: `publish`.

   It prints the exact `python3 … pipeline.py <component>` line, built as `status` builds its suggestions
   (`invocation_args`).
6. **Builds from before plan 12 still work.** With no `drafts/` directory, `resume` says "no revisions:
   this build predates revision snapshots; run render", then prints the continuation note if there is one.
   With a revision whose `revision.json` is unreadable, it names that revision and goes on with the rest.
7. **`status` gets one pointer line.** When `drafts/` exists, `status` prints `drafts     rev-NNNN latest;
   N open blocking finding(s) -- `resume` for the loop`. Nothing else in `status` changes.
8. **Docs and version.**
   - `workflow.md`: replace the "Not yet implemented" section with how to stop (write
     `.docs-build/continuation.md`) and how to continue (`pipeline.py resume`). The stop rule says the
     no-progress line comes from `resume`, and the Coordinator decides.
   - `pipeline.md`: the `resume` component.
   - `SKILL.md`: one line in the run steps, "after a break, run `resume` first".
   - Plan 4's W5 row becomes "Done by plans 12 and 13".
   - `docs` 1.5.0 → 1.6.0, with a `### Changed` entry under `[Unreleased]`. Edit `shared/scripts/` only, and
     run `tools/materialize.py`.

## Scope

In:

- `shared/scripts/pipeline.py`:
  - the new `resume` component and its argument wiring;
  - the `status` pointer line;
  - small read helpers, which may live in `draft_artifact.py` if shared.
- The regenerated plugin copies.
- `SKILL.md`, `references/workflow.md`, `references/pipeline.md`, the `docs` version and `CHANGELOG.md`.
- `doc/plan-4-documentation-review-workflow.md`, the W5 row.
- Tests in `tools/test_pipeline.py`. Add `tools/test_checkpoint_input_binding.py` only if a real run is the
  cheapest setup, as in plan 12.

Out:

- Any automatic stop, or a block on `render`, `review` or `publish` (the user's choice: the script reports,
  the model decides).
- Writing or validating `continuation.md`.
- Budget tracking by script.
- W2 (plan 14) and W6.
- Changes to the review row schema, `BOUND_INPUTS`, or plan 12's revision files.

## Baseline

| Existing | Keep, change, or remove |
| --- | --- |
| `pipeline.py` `status(args, build)`: read-only, runs before `build_dir.ensure` | Keep; add the one line of Decision 7 |
| `pipeline.py` `drafts_of(args)` → `<build>/drafts` | Reuse |
| `pipeline.py` `record_review_history`: writes `rev-NNNN.meta/review-KK.jsonl` and `prose-report-KK.json`; a round without `--review` has a report but no review file | Read only. Decision 3 uses the last *review file* per revision |
| `draft_artifact.py` `read_revision`, `verify_revision`, `tree_hash` | Reuse |
| `render/snapshot_revision.py` `drafts/counter.json`, `revision.json` (`previous`, `created_at`) | Read only |
| `publish-seal.json` v2 `revision` | Read only |
| `review_records.py` `FINDING_STATES`, `SEVERITIES` | Reuse the constants; do not change them |
| `pipeline.py` `invocation_args`, `next_step` | Reuse for the suggested command |
| `references/workflow.md` "Not yet implemented" (resume missing) | Replace per Decision 8 |

## Tech stack and constraints

Default: stdlib-only Python 3.9+, canonical scripts in `shared/scripts/`, and plugin copies regenerated by
`tools/materialize.py`.

## Acceptance criteria

All criteria are tests in `tools/test_pipeline.py`, unless noted.

- [ ] **Read-only.** Run `resume` on a build with revisions, reviews, a seal and a continuation note. Every
      file under the build directory has the same bytes and modification time before and after, and
      `timings.jsonl` is not appended.
- [ ] **No scan.** `resume` with no build directory exits 0, prints the "no scan yet" line, and creates no
      directory.
- [ ] **Pre-plan-12 build.** A build with a scan but no `drafts/` exits 0 and prints the "predates revision
      snapshots" line.
- [ ] **Open findings.** A blocking finding `F1` first raised on `rev-0001` and still open on `rev-0002`
      prints with `since rev-0001`. A finding resolved on `rev-0002` is not listed.
- [ ] **No progress.** The same open blocking IDs `{F1, F2}` on the last review of `rev-0002` and `rev-0003`
      print the no-progress line. These do not print it:
      - `{F1}` against `{F1, F2}`;
      - two rounds on the same revision;
      - empty sets.

      `render` still runs afterwards. This is the failure case, and it must not block.
- [ ] **Continuation note.** `continuation.md` prints under the "not checked" heading. A note older than the
      latest revision gets the "older than" warning.
- [ ] **Next step.** One case each:
      - staging differs from the latest revision → `render`;
      - no review round → `review`;
      - sealed latest revision → `publish`.
- [ ] **Damaged revision.** An unreadable `revision.json` names that revision, and `resume` still exits 0.
- [ ] **`status` pointer.** `status` prints the `drafts` line when `drafts/` exists, and does not print it
      otherwise.
- [ ] **Docs.** `workflow.md` no longer says resume does not exist. Checked by
      `grep -n "do not exist\|Not yet implemented" plugins/docs/skills/document-codebase/references/workflow.md`
      printing nothing, and by reading.
- [ ] **Required checks pass:** `python3 tools/validate.py`, `python3 tools/materialize.py --check`, and
      `for t in tools/test_*.py; do python3 "$t" || break; done`.

## Risks

| Risk | How it is handled |
| --- | --- |
| A stale continuation note misleads the next session | It is labelled "not checked", shows its age, and warns when it predates the latest revision (Decision 4) |
| The no-progress line fires when a repair is half done | It only reports. The Coordinator decides (the user's choice), and nothing is blocked |
| Pruning removed the revision where a finding first appeared | "since" names the oldest kept revision that has it, and says `(or earlier; older revisions were pruned)` when the oldest kept revision is not `rev-0001` |
| `resume` reads files a concurrent run is writing | It is read-only and tolerant: an unreadable file is named and skipped, never fatal |
| The coder run is cut off | Push after each group (Decisions 1–3, 4–7, 8) |

## Open questions

None.
