# Roles and the draft-review workflow

How the model's work is split between a Coordinator, Analysts, Writers and Reviewers, what each hands to the
next, and when to stop. The roles are instructions in this skill, not separate skills or installed agents.
Commands, flags and exit codes are in [`pipeline.md`](pipeline.md); this file does not repeat them.

## Contents

- [Roles](#roles)
- [Discover what the host can do](#discover-what-the-host-can-do)
- [The task contract](#the-task-contract)
- [Artifacts and who writes them](#artifacts-and-who-writes-them)
- [Transitions](#transitions)
- [Independent review and self-review](#independent-review-and-self-review)
- [Routing findings](#routing-findings)
- [Budget and the stop rule](#budget-and-the-stop-rule)
- [Not yet implemented](#not-yet-implemented)

## Roles

| Role | Does | Task file |
| --- | --- | --- |
| Coordinator | Owns scope, dispatch, merging, conflicts, revisions and the final report. You are the Coordinator. | this file |
| Analyst | Reads product source and returns what each component does, with evidence, and what it could not determine | [`analyst.md`](analyst.md) |
| Writer | Composes reader-facing pages from reconciled analysis | [`writer.md`](writer.md) |
| Reviewer | Checks the exact rendered draft against source and returns findings or a verdict | [`reviewer.md`](reviewer.md) |

One context may play several roles in sequence. What matters is that the record of review independence
stays true (see below).

## Discover what the host can do

Before dispatching, find out whether the host can start subagents. Use only what it exposes; naming a tool
in this skill grants no permission, and you never ask for new ones.

- **Subagents available.** Independent component analyses, and reviews of separate pages, may run in
  parallel within the budget.
- **Not available.** Run the same tasks as explicit sequential passes in your own context.

The dependencies hold either way. Writing waits for reconciled analysis, and review waits for a rendered
draft. Parallelism removes neither.

## The task contract

Every dispatched task, to a subagent or to yourself, states:

- task ID, role, and scope: a component or a user journey, not one file per task;
- the source and index identity (`index_hash`, copied verbatim from the survey);
- input artifacts and the expected output;
- acceptance criteria and a budget;
- read and write boundaries.

A subagent does not inherit this skill or the conversation. Put the role file's instructions, and the
rules the task needs, in its prompt.

## Artifacts and who writes them

Only the Coordinator writes the shared files: `module-analysis.jsonl`, `fragments.jsonl`, the claim and
review JSONL files, `manual-analysis.json` and the three analyses. This is the append rule in
[`analyze.md`](analyze.md) and [`context-policy.md`](context-policy.md): each parallel task returns its
results to you, because two writers on one JSONL file interleave into corrupt lines.

A worker may instead write isolated artifacts under `.docs-build/tasks/<task-id>/`. You merge them into the
shared files and resolve conflicting readings of the same source yourself, by reading it.

A task that times out stays pending. It never counts as done, and its scope stays unread until a task
covers it.

## Transitions

| From | To | Gate before the hand-off |
| --- | --- | --- |
| Survey and template | Analyst | Scope agreed at P1; template recorded |
| Analyst | Writer | Analyses reconciled by you, conflicts resolved, gaps listed; P2 and P3 decided |
| Writer | Render | Draft composed; the Writer set no review status |
| Render | Reviewer | The rendered draft exists and mechanical checks have run |
| Reviewer | Coordinator | Findings returned, or a verdict bound to the reviewed content |
| Coordinator | Analyst or Writer | Each finding routed to the role that caused it |

The revision loop with what exists today: `render`, then `review`, repair, `render` again. Each review row
records the `draft_revision` that `review` printed in its queue; copy it, as
[`prose-rules.md`](prose-rules.md) says. A repair that changes content needs a fresh review of the changed
sections, and P4 as `SKILL.md` describes.

## Independent review and self-review

Record how the review was done, truthfully, using the `review_mode` field of the review row defined in
[`schemas.md`](schemas.md#prose-reviewjsonl--review_version-2):

- A review run in a context separate from the Writer's records `independent`. A subagent of the same model
  family counts; a different provider is not needed.
- A sequential pass by the same context that wrote the draft records `self_review`. Never claim
  independence that did not happen.

Both modes apply the same rubric in
[`prose-rules.md`](prose-rules.md#content-review-criteria-for-manual-sections). The final report states
which mode each review used.

## Routing findings

- A wrong interpretation goes back to the Analyst, who corrects `module-analysis.jsonl` or the three
  analyses before any prose is rewritten. Rewording around a faulty reading hides it.
- Weak wording, a missing facet the analysis already covers, or poor order goes to the Writer.
- The Writer never sets `content_review` and never writes a `confirmed` row about its own draft.

## Budget and the stop rule

Track the iteration number, budget remaining, draft revision, findings open and next actions as you go.

Stop when the budget is spent, or after two consecutive revision rounds that leave the same blocking
findings open with no substantive progress. Then:

1. Keep the readable draft.
2. Write a continuation report: findings still open, the next actions, and the budget used.
3. Report the run as unfinished. A stop is never turned into `confirmed`.

The two-attempt retry for structural claims in `check` is a separate loop.

## Not yet implemented

Immutable `rev-NNNN` revision snapshots and a resume command are planned (plan 4, W5) and **do not exist
yet**. Do not look for a snapshot directory or run a resume command. Today, keep the draft in the staging
and rendered output the driver already writes, record `draft_revision` on each review row, and carry the
continuation report in your own reply and in `.docs-build/`. `pipeline.py status` shows where a run stands.
