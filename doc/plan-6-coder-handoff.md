# Plan 6 — split hand-off and review out of `write-plan` into `coder-handoff`

Status: approved
Date: 2026-11-16
Branch: `feat/reasoning-coder-handoff`
Baseline: `origin/main` at `8edc1d230139d9d799bb0d401859e970e1f23dba`
Target: `plugins/reasoning` (new skill `coder-handoff`, `write-plan` narrowed); `plugins/development`
(`implement`'s finish step)

## Goal

`write-plan` (plan 5) does two jobs at two different times: it writes a plan before approval, and after
approval it hands the plan to a coder session, reviews the returned branch, and opens the pull request. Split
the second job into its own skill, `coder-handoff`, so each skill fires on its own requests.

Plan 5's first real run also showed that the coder session could not message the planning session back
(`send_message` was not among its tools), so the user had to tell the planner the work was done. Make the
planner find out without the user:

- open a draft pull request at hand-off;
- let the host's pull-request events (CI finishing on each push) wake the planner;
- have the coder mark completion in git.

## Decisions

1. **New skill `coder-handoff` in `reasoning`** (name chosen by the user). It starts when the user approves a
   plan, and it covers:
   - setting `Status: approved` and making the planner's last push;
   - opening a draft pull request;
   - dispatching the plan to the coder;
   - waiting for the coder, then reviewing its branch;
   - marking the pull request ready;
   - merging only when the user asks.

   Rejected: keeping all of this in `write-plan`, because writing and handing off happen at different times
   and fire on different requests.
2. **`write-plan` ends at the draft.** It writes the plan, creates the branch, pushes `Status: draft`, and
   revises until the user approves. Then it names `coder-handoff` as the next step. Move its rules 3, 10 and
   11, steps 9–12, and the hand-off and review blocks of its Output format to `coder-handoff`.
3. **Trigger boundary.** `coder-handoff` takes:
   - "approved, hand it to the coder" and "giao plan này cho coder/Sonnet";
   - "the coder pushed / is done, review the branch";
   - "open the PR for plan N".

   `write-plan` keeps writing and saving a plan, including "write a plan so another session can implement
   it". Remove "hand this off" and the review and pull-request wording from `write-plan`'s description. Each
   description names the other skill.
4. **Draft pull request at hand-off** (decided by the user). Right after the approval push, `coder-handoff`
   opens a draft pull request from the plan's branch to the default branch. Its title and body come from the
   plan and follow the repository's rules, with no session ids. When the review passes, it marks the pull
   request ready for review. Rejected: opening the pull request only after review (plan 5), because without
   an open pull request the planner gets no events.
5. **How the planner is woken, in order of preference:**
   1. The host's pull-request activity subscription, for example `subscribe_pr_activity` in Claude Code cloud
      sessions. CI finishing on a push wakes the planner. This was observed on eurus-labs/Skills#69 and #70.
   2. A message from the coder through a cross-session messaging tool, if the coder's host has one.
   3. A scheduled check-in, for example `send_later`, as a safety net when the repository runs no CI on pull
      requests or an event is lost.
   4. The user telling the planner.

   `coder-handoff` says which of these it set up.
6. **The coder marks completion in git: its last commit sets the plan's `Status: implemented`** (approved by
   the user). Only that line changes, and Decisions are never edited. Then `implement` tells the planning session the branch is
   ready, by messaging tool where available, otherwise by telling the user, as in plan 5.

   On each wake, `coder-handoff` reads `Status` at the branch head:
   - `approved`: the coder is still working, so wait;
   - `implemented`: review the branch.

   Rejected: treating any push as done, because a coder may push several times.
7. **Review result goes to the user; gaps go to the coder.**
   - If every acceptance criterion is met: mark the pull request ready and report to the user.
   - If any criterion is not met: keep it a draft, and send the gaps to the coder (or give them to the user to
     paste). The coder sets `Status: implemented` again when it has fixed them.
   - The planner never pushes to the branch after the approval push.
8. **Unchanged from plan 5:**
   - Authority comes from the approved plan in git.
   - The coder never opens or merges a pull request.
   - Session ids are never committed.
   - The repository's rules win over the skill's defaults.
   - Pushing, opening a pull request, and messaging are outward actions the skill names.

## Scope

In:

- `plugins/reasoning/skills/coder-handoff/SKILL.md` (from the template, about 150 lines; no references or
  scripts), and `write-plan/SKILL.md` narrowed per Decision 2.
- `plugins/development/skills/implement/SKILL.md`: the finish step for a handed-off plan sets
  `Status: implemented` as its last commit (Decision 6).
- `reasoning` `0.1.0` → `0.2.0` and `development` `0.4.0` → `0.5.0`: both `plugin.json` copies, both
  `marketplace.json` copies, the plugin READMEs, the root catalog row, and `CHANGELOG.md` `[Unreleased]`.
- `AGENTS.md`'s hand-off bullet: a draft pull request at hand-off, the `Status: implemented` signal, and the
  name `coder-handoff`.
- `plan-template.md`: the `Status` line says who sets each value (the user sets `approved`; the coder sets
  `implemented`).
- Trigger eval cases under `plugins/reasoning/evals/trigger/`:
  - two that must fire `coder-handoff` ("approved, giao cho coder"; "the coder is done, review the branch");
  - one that must stay quiet for `coder-handoff` ("write the plan to a file").

  Check that the existing `write-plan-*` cases still hold.

Out:

- Scripts, behavior evals, other plugins.
- Any change to how `design-solution` works.

## Baseline

| Existing (after eurus-labs/Skills#70) | Keep, change, or remove |
| --- | --- |
| `plugins/reasoning/skills/write-plan/SKILL.md` rules 3, 10, 11; steps 9–12; Output format hand-off and review blocks | Move to `coder-handoff` |
| `write-plan` description: "hand this off", "review the branch it returns and open the pull request" | Remove; name `coder-handoff` instead |
| `plugins/development/skills/implement/SKILL.md` "Tell the planning session when the branch is ready" | Keep; add the `Status: implemented` last commit before it |
| `AGENTS.md` hand-off bullet and its PR exception line | Update for the draft pull request at hand-off |
| `plugins/reasoning/evals/trigger/write-plan-*` | Keep; re-check them against the narrowed description |

## Tech stack and constraints

Default per `AGENTS.md`: Markdown skills, no new dependencies. Keep each `SKILL.md` under ~500 lines.

## Acceptance criteria

- [ ] `reasoning` lists `design-solution`, `write-plan` and `coder-handoff` in both `plugin.json` copies, at
      `0.2.0`, and `development` is `0.5.0`, all matching `marketplace.json`. Checked by
      `python3 tools/validate.py`.
- [ ] `write-plan` no longer describes dispatching, reviewing, or opening a pull request, and names
      `coder-handoff`. Checked by grepping its `SKILL.md` for `send_message` and `pull request`, and by
      reading it.
- [ ] `coder-handoff` states Decisions 4–8 itself, including the wake order and its fallbacks. Checked by
      reading it.
- [ ] Failure case: `coder-handoff`, woken while the branch's plan still says `Status: approved`, does not
      review and keeps waiting. Checked by reading its steps.
- [ ] Failure case: when a criterion is not met, the pull request stays a draft and the gaps go to the coder.
      Checked by reading its steps and Output format.
- [ ] Failure case: on a host with no pull-request subscription and no CI, `coder-handoff` sets a scheduled
      check-in or tells the user how it will learn the work is done. Checked by reading it.
- [ ] `implement`'s last commit on a handed-off plan changes only the `Status` line to `implemented`. Checked
      by reading its finish step.
- [ ] No session ids or personal identifiers in committed files. Checked by grepping `plugins/reasoning` and
      `plugins/development` for `session_` and the author's no-reply address.
- [ ] The new trigger cases exist; whether they were run is reported, not claimed.
- [ ] `python3 tools/validate.py` passes, and `for t in tools/test_*.py; do python3 "$t" || break; done` passes.

## Risks

| Risk | How it is handled |
| --- | --- |
| `write-plan` and `coder-handoff` fire on each other's requests | Decision 3's split; descriptions name each other; trigger cases on both sides |
| A repository runs no CI on pull requests, so no event wakes the planner | Decision 5's scheduled check-in and user fallback |
| The planner reviews a half-done branch after an intermediate push | Decision 6: review only at `Status: implemented` |
| A draft pull request is mistaken for ready work | It stays a draft until the review passes; the body says it is a draft awaiting the coder |
| The coder edits more than the `Status` line in the plan | Acceptance check on `implement`'s finish step; the planner's review compares the plan with the approved version |
| Opening a pull request at hand-off conflicts with a repository's "no PR unless asked" rule | The user's approval of the plan is the ask; the skill says so, and a repository rule that forbids it wins (Decision 8) |

## Open questions

None.
