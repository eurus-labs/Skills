# Plan 9 — roles and the draft–review workflow for `document-codebase` (plan 4, W4)

Status: implemented
Date: 2026-11-17
Branch: `feat/docs-review-roles`
Baseline: `origin/main` at `35d87361c76d32c50ce6c03b5c18d3def8817fcb`
Target: `plugins/docs/skills/document-codebase` (`SKILL.md`, new `references/workflow.md`, `analyst.md`,
`writer.md`, `reviewer.md`); `doc/plan-4-documentation-review-workflow.md` (progress table)

## Goal

Plan 4 wants `document-codebase` to work in roles:

- an **Analyst** reads product source;
- a **Writer** composes reader-facing pages from that analysis;
- a **Reviewer** checks the exact draft against source;
- a **Coordinator** owns scope, dispatch, merging, and revisions.

Today the skill says to draft, review, and repair (`SKILL.md` rule 5), but it defines no role, no task
contract, and no honest way to report whether the review was independent. This plan implements plan 4's W4:
the four role and workflow references, and the `SKILL.md` dispatch that points to them.

It also records where plan 4 actually stands. Its table still reads "All packages below are pending",
although W1 and W3 shipped and W2 and W5 are partly in place.

## Decisions

1. **Four new references, placed as plan 4 placed them**, under
   `plugins/docs/skills/document-codebase/references/`:
   - `workflow.md`: the model workflow, the artifacts, the transitions between roles, the budget, and the
     stop rule;
   - `analyst.md`: the source-reading task contract;
   - `writer.md`: the composition and revision task contract;
   - `reviewer.md`: the content-review task contract.

   They are portable instructions, not new skills. Rejected: one skill per role, because roles would then
   fire on their own and plan 4 says not to.
2. **Reuse what exists; do not restate it.** Point to these rules instead of copying them:
   - the review rubric (Support, Coverage, Reader usefulness, Specificity, Composition) in
     `references/prose-rules.md`;
   - the `prose-review.jsonl` v2 record (`review_mode`, `verdict`, `findings`, the bound hashes) in
     `references/schemas.md`;
   - "each parallel task returns its lines to you" in `references/analyze.md` and
     `references/context-policy.md`.

   A reference may quote a field name but must not redefine it. Rejected: self-contained role files, because
   two copies of one rule drift apart, and plan 4 says "without conflicting duplicates".
3. **Every dispatched task carries a contract.** Each task states:
   - its task ID, role, and scope (components or a journey, not one file each);
   - the source and index identity (`index_hash`);
   - its input artifacts and expected output;
   - its acceptance criteria and budget;
   - its read and write boundaries.

   A subagent gets its role file's instructions in the prompt, because it does not inherit the skill or the
   conversation.
4. **Delegation follows the host, and the report says which happened.**
   - The Coordinator first finds out whether the host can start subagents.
   - If it can, independent analyses or page reviews may run in parallel within the budget. Writing still
     waits for reconciled analysis, and review still waits for a rendered draft.
   - A review in a context separate from the Writer's records `review_mode: independent`. A sequential pass by
     the same context records `self_review`. Both use the same rubric.
   - The same model family in a separate context counts as independent; a different provider is not needed.
     Host permissions always stay in force, and the skill never asks for new ones.
5. **Only the Coordinator writes shared files.** Workers return results, or write isolated task artifacts
   under `.docs-build/tasks/<task-id>/`. The Coordinator merges them into the shared JSONL files and resolves
   conflicting readings. A task that times out stays pending and never counts as done.
6. **Findings route to the role that caused them.**
   - A wrong interpretation goes back to the Analyst, who corrects `module-analysis.jsonl` or the three
     analyses before any prose is rewritten.
   - Weak wording goes to the Writer.
   - The Writer never sets `content_review` and never writes a `confirmed` review row about its own draft.
7. **The stop rule is stated, and its limits too.** Stop when the budget is spent, or after two consecutive
   revision rounds that leave the same blocking findings open with no substantive progress. Keep the readable
   draft and write a continuation report (findings open, next actions, budget used). Never turn a stop into
   `confirmed`.
   - `workflow.md` describes the revision loop with what exists today: `render`, `review`, repair, and render
     again, with `draft_revision` recorded on each review row.
   - It says plainly that immutable `rev-NNNN` snapshots and resume are W5 and **not yet implemented**. It
     must not instruct the model to use a snapshot directory or resume command that does not exist.
8. **`SKILL.md` gets a short Roles section and step links**:
   - a section of 10–15 lines that names the four roles, the honesty rule for `review_mode`, and the
     Coordinator-only writing rule, and points to `workflow.md`;
   - in the "Plan and run" table, Analyze also loads `analyst.md`, Document also loads `writer.md`, and Final
     review also loads `reviewer.md`.

   Keep `SKILL.md` under ~500 lines (it is 158 now). Existing rules 1–7, checkpoints P1–P4, and the authored-
   page rule are unchanged.
9. **Plan 4's work-package table becomes a progress record.** Replace "All packages below are pending" with
   each package's state and its evidence:
   - W1 done (`a6b0733`, `cff0701`, `ef83115`);
   - W3 done (`a6b0733`);
   - W2 partial: `scope_record.py` exists, but only `pipeline.py` consumes it, and `select_units` still
     defaults to the top 25;
   - W4 done by this plan;
   - W5 partial: staging and the fresh-review rule exist, but there are no immutable revisions and no resume;
   - W6 pending: v1 artifacts are refused, and there is no migrator.

   Before writing "done", the coder runs `tools/test_manual_preset.py` and `tools/test_prose.py` and cites
   them. A package whose evidence the coder cannot confirm is recorded as "partial, unverified", not "done".
10. **Version and release notes:** `docs` `1.3.6` → `1.4.0` (new workflow behavior), matching across both
    `plugin.json` copies and both `marketplace.json` copies. Add a `CHANGELOG.md` `[Unreleased]` "Changed"
    entry.

## Scope

In:

- The four new reference files, and the `SKILL.md` Roles section and step links.
- Small pointer edits in `analyze.md`, `three-analyses.md`, `manual.md`, `prose-generation.md`, and
  `prose-rules.md` where a role file must be named. Change no rule text in them.
- Plan 4's progress table, the version bump, and the CHANGELOG entry.

Out:

- Any script change, including in `shared/scripts/` (W2, W5 and W6).
- New schemas or new fields; the v2 review record already has what W4 needs.
- Behavior evals, and running the skill end to end (eval work is a separate task).

## Baseline

| Existing (at `35d8736`) | Keep, change, or remove |
| --- | --- |
| `SKILL.md` rule 5: "Draft, review source support and reader usefulness, then repair until current sections are confirmed" | Keep; the Roles section explains who does each part |
| `references/prose-rules.md:99-113`: the review rubric and "a sequential second pass reports `self_review`" | Keep; `reviewer.md` points to it |
| `references/schemas.md:640-690`: `prose-review.jsonl` v2, `review_mode` `independent` or `self_review`, and the findings shape | Keep; the role files use these fields as written |
| `shared/scripts/publish/review_records.py:29`: `REVIEW_MODES = ("independent", "self_review")` | Unchanged; the instructions must match it |
| `references/analyze.md:66-70` and `references/context-policy.md:100-103`: parallel tasks return lines to the coordinator | Keep; `workflow.md` points to them |
| `doc/plan-4-documentation-review-workflow.md:188`: "All packages below are pending" | Replace with the progress table (Decision 9) |
| Plan 4's baseline note about stale prefill text and `pipeline.md`'s survey table | Already fixed on `main`; no work needed |

## Tech stack and constraints

Default per `AGENTS.md`: Markdown only in this plan, with no new dependencies. Follow the
`.github/instructions/` files whose `applyTo` matches `SKILL.md` and the references. No reference may link
outside the `docs` plugin.

## Acceptance criteria

- [ ] `workflow.md`, `analyst.md`, `writer.md` and `reviewer.md` exist under `references/`, and `SKILL.md`
      links each one. Checked by `python3 tools/validate.py`, which resolves links, and by
      `grep -n "workflow.md\|analyst.md\|writer.md\|reviewer.md" plugins/docs/skills/document-codebase/SKILL.md`.
- [ ] No role file redefines the review rubric or a v2 review field. Checked by reading: they point to
      `prose-rules.md` and `schemas.md`.
- [ ] Every `review_mode` value named in the new files is `independent` or `self_review`, matching
      `review_records.py`. Checked by
      `grep -rnoh "review_mode[^.]*" plugins/docs/skills/document-codebase/references/{workflow,analyst,writer,reviewer}.md`.
- [ ] Failure case: `workflow.md` says that a sequential pass reports `self_review`, that a timed-out task
      stays pending, and that a stop is never `confirmed`. Checked by reading.
- [ ] Failure case: no new file instructs the use of `rev-NNNN` snapshot directories or a resume command.
      Each mention marks them as W5, not yet implemented. Checked by
      `grep -rn "rev-0\|resume" plugins/docs/skills/document-codebase/references/{workflow,analyst,writer,reviewer}.md`.
- [ ] `writer.md` says the Writer never sets `content_review` and never confirms its own draft. Checked by
      reading.
- [ ] Plan 4's table records each package's state with commit evidence, and nothing is marked "done" without
      cited evidence. `tools/test_manual_preset.py` and `tools/test_prose.py` pass. Checked by reading and by
      running both.
- [ ] `docs` is `1.4.0` in both `plugin.json` copies and both `marketplace.json` copies. Checked by
      `python3 tools/validate.py`.
- [ ] `python3 tools/validate.py`, `python3 tools/materialize.py --check`, and
      `for t in tools/test_*.py; do python3 "$t" || break; done` all pass.
- [ ] Every commit has the expected identity on both sides. Checked before each push by
      `git log origin/main..HEAD --format='%an <%ae> | %cn <%ce>' | sort -u`.

## Risks

| Risk | How it is handled |
| --- | --- |
| The role files contradict the v2 schema or the review rubric | Decision 2: point, don't copy; acceptance greps for `review_mode` values |
| The workflow promises W5 features that don't exist | Decision 7, plus an acceptance grep for snapshots and resume |
| A report claims independent review that was sequential | Decision 4; `writer.md` and `reviewer.md` repeat the honesty rule |
| Parallel workers corrupt shared JSONL | Decision 5: Coordinator-only writes, matching `analyze.md` |
| Plan 4's progress table overstates what shipped | Decision 9: evidence for each "done", and "partial, unverified" otherwise |
| `SKILL.md` grows past its useful size | Decision 8: a short section; detail lives in `workflow.md` |

## Open questions

None.
