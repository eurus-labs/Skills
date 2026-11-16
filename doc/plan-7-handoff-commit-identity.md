# Plan 7 — check the commit identity before every push in a hand-off

Status: implemented
Date: 2026-11-16
Branch: `fix/reasoning-handoff-commit-identity`
Baseline: `origin/main` at `493e2fb91460849e0fb3ed99adbee8c40427ce69`
Target: `plugins/reasoning` (`coder-handoff`, `design-solution`); `plugins/development` (`implement`)

## Goal

During plan 6's fix-up run, the coder subagent pushed one commit without setting the commit identity. Git then
used the identity the environment had preset: the author's private email, and an AI committer. The subagent
noticed only after pushing, and rewrote the commit. The branch is clean now, but GitHub had already recorded
the pushed commit, and CI ran on it.

Make the hand-off prevent this:

- the coder sets the identity explicitly on every commit;
- the coder checks the identity of every commit it is about to push, before the push, not only at the end.

Also fix the leftover routing text in `design-solution` that still sends hand-offs to `write-plan`.

## Decisions

1. **`implement` gets a commit-identity rule** that applies to every use, not only to handed-off plans:
   - The identity comes from the repository's instructions or from the user, never from the environment's
     defaults, and never an AI identity.
   - Set it explicitly on every command that writes a commit (for example the four `GIT_AUTHOR_*` and
     `GIT_COMMITTER_*` variables inline).
   - Never change `git config`.
   - Before every push, list the author and committer of every commit about to be pushed. If any commit
     differs from the expected identity, do not push: recommit it with the right identity first.
   - Rejected: a check only at the end of the run, because that is the check that came too late in plan 6.
2. **`coder-handoff`'s dispatch prompt carries the identity.**
   - The planner states the exact author and committer identity in the subagent prompt, taken from the
     repository's rules or from the user. It tells the subagent to set it on every commit and to check it
     before every push.
   - The planner's review checks the identity of every commit on the branch, and sends any mismatch back as a
     gap.
   - Rejected: relying on the subagent to find the identity itself, because a subagent starts without the
     conversation and can miss it.
3. **If a commit with the wrong identity was already pushed**, the coder recommits it with the right identity
   and replaces it on its own unmerged branch with `--force-with-lease`. It then reports that the old commit
   was public. The planner tells the user that GitHub may keep the old commit reachable by its sha, and that
   GitHub's "Block command line pushes that expose my email" setting prevents this at the server.
4. **`design-solution` routes hand-offs to `coder-handoff`.** In its description and its "When not to use"
   section:
   - writing or saving a plan stays with `write-plan`;
   - handing a plan to a coder goes to `coder-handoff`.
   Its line saying `write-plan` "owns … the hand-off" changes to say `coder-handoff` owns it. This changes
   when `design-solution` defers, so the root catalog row is updated in the same commit.
5. **Patch versions:** `reasoning` `0.2.0` → `0.2.1` and `development` `0.5.0` → `0.5.1`. These are fixes to
   existing skills, with no new skill.

## Scope

In:

- `plugins/development/skills/implement/SKILL.md`: Decisions 1 and 3.
- `plugins/reasoning/skills/coder-handoff/SKILL.md`: Decision 2 in the hard rules, the Output format's
  subagent prompt, and the review step; Decision 3's report to the user.
- `plugins/reasoning/skills/design-solution/SKILL.md`: Decision 4.
- Both `plugin.json` copies of each plugin, both `marketplace.json` copies, the root `README.md` catalog row
  for `reasoning` if its wording changes, and `CHANGELOG.md` `[Unreleased]`.

Out:

- `AGENTS.md`, whose commit rules already cover this repository.
- Any script or hook that blocks pushes; the GitHub setting is the user's to turn on.
- Removing the already-pushed commit from GitHub.

## Baseline

| Existing (at `493e2fb`) | Keep, change, or remove |
| --- | --- |
| `implement/SKILL.md`: no rule about commit identity | Add Decision 1's rule as a hard rule, and use it in the commit and push steps |
| `coder-handoff/SKILL.md` rule 7: "commit identity comes from the user, never an AI identity"; Output format subagent prompt with no identity | Keep rule 7; add the identity to the prompt and the review |
| `design-solution/SKILL.md` line 3: "hand it to another session, use write-plan"; lines 33–34: "owns the plan document, its branch, and the hand-off" | Route the hand-off to `coder-handoff` |

## Tech stack and constraints

Default per `AGENTS.md`: Markdown skills, no new dependencies. Keep each `SKILL.md` under ~500 lines.

## Acceptance criteria

- [ ] `implement` has a hard rule that sets the identity explicitly on every commit, never uses `git config`,
      and checks every commit's author and committer before every push. Checked by reading it, and by
      `grep -n "before every push" plugins/development/skills/implement/SKILL.md`.
- [ ] Failure case: `implement` says what to do when the check finds a mismatch before a push (recommit
      first, do not push) and when a bad commit was already pushed (Decision 3). Checked by reading it.
- [ ] `coder-handoff`'s Output format prompt contains an identity placeholder and the check-before-every-push
      instruction, and its review step checks every commit's identity. Checked by reading it.
- [ ] `design-solution` sends hand-offs to `coder-handoff`, and no line says `write-plan` owns the hand-off.
      Checked by `grep -n "coder-handoff" plugins/reasoning/skills/design-solution/SKILL.md`, and by
      `grep -n "owns.*hand-off" plugins/reasoning/skills/design-solution/SKILL.md` showing only the new wording.
- [ ] No personal email, no-reply address, or session id appears in any skill. Checked by grepping
      `plugins/reasoning` and `plugins/development` for `@users.noreply`, `gmail`, and `session_`.
- [ ] Versions are `reasoning` 0.2.1 and `development` 0.5.1, matching across both `plugin.json` and both
      `marketplace.json` copies. Checked by `python3 tools/validate.py`.
- [ ] `python3 tools/validate.py` passes, and `for t in tools/test_*.py; do python3 "$t" || break; done` passes.

## Risks

| Risk | How it is handled |
| --- | --- |
| A skill hardcodes this repository's identity | Decisions 1–2 say the identity comes from the repository or the user; acceptance greps for addresses |
| The check-before-push rule is ignored like the end-of-run check was | It sits at the push step itself, and the planner's review re-checks every commit (Decision 2) |
| `design-solution` and `coder-handoff` now overlap on "hand off" | `design-solution` only defers; `coder-handoff`'s description already owns the phrases |
| The coder of this plan repeats the mistake | The dispatch prompt states the identity and the check, and the planner re-checks before marking ready |

## Open questions

None.
