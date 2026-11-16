# Plan 5 — a `write-plan` skill that hands a plan to another session

Status: draft
Date: 2026-11-16
Branch: `feat/development-plan-handoff`
Baseline: `origin/main` at `6c545ea51bdb3476b43d232cb40e09a26ab016c6`
Target: `plugins/development` (new skill `write-plan`; edits to `implement` and `design-solution`)

## Goal

The repository already works this way: one session plans, writes the plan to `doc/`, and pushes it on its own
branch; a second session implements on that branch once the user approves (`AGENTS.md`, Start Each Task step 2
and Plan and Implement). That only works here, because the rules live in this repository's `AGENTS.md`. Package
the workflow as a skill so it works in any repository where the `development` plugin is installed. Then a
plan's decisions reach the implementing session intact, and two sessions never push to the same branch at once.

## Decisions

1. **A new skill `write-plan` in the `development` plugin** — rejected: extending `design-solution`, because
   the user treats advising on a design and handing off a durable plan as separate jobs. The name is a
   proposal; renaming after release changes the install name.
2. **Split the trigger boundary explicitly.** `write-plan` takes requests to write, save, or hand off a plan
   ("write the plan to a file", "plan this for another session", "lên plan để giao cho session khác").
   `design-solution` keeps advice, comparisons and "how would you…" questions, answered in the conversation.
   Today `design-solution`'s description claims "prepare an implementation plan", "plan the implementation"
   and "asks for a plan to hand to someone else"; remove the hand-off and durable-plan phrases from it. Each
   description names the other skill. Rejected: leaving both descriptions as they are, because the overlap
   would make each fire on the other's requests.
3. **Plan location: the repository's existing plan folder.** Detect it as a folder that already holds plan
   documents (for example `doc/plan-*.md`, `docs/plans/`, `plans/`). If none exists, see Open questions.
4. **The template is bundled in the skill** at `skills/write-plan/references/plan-template.md`, because a
   `SKILL.md` may not link outside its plugin. It becomes the only copy: delete `doc/_plan-template.md` and
   point `AGENTS.md` at the bundled file. Rejected: keeping two copies, because they would drift. Rejected:
   `shared/` with `tools/materialize.py`, because only one plugin uses the template.
5. **The template is generic.** Its "Tech stack and constraints" default reads "the repository's documented
   constraints; list only deviations", not this repository's stdlib rule.
6. **`write-plan` restates the hand-off rules itself**, because other repositories have no such `AGENTS.md`:
   - Status starts at `draft`; only the user moves it to `approved`.
   - The planning session creates the branch from the latest default branch, commits and pushes the plan, and
     after approval stops pushing to it.
   - Plan changes after hand-off go through the user.
   - It ends by giving the user the hand-off message: the branch, the plan path, and the baseline sha.
7. **Repository rules win over the skill's defaults.** Branch naming, commit identity, commit format and the
   default branch come from the target repository's instructions (`AGENTS.md`, `CONTRIBUTING.md`, similar).
   Fallbacks: branch `<type>/<area>-<outcome>`; commit identity from the user; never an AI identity. Never
   hardcode this repository's values.
8. **Creating a branch and pushing are outward actions.** `SKILL.md` says it does both and confirms before the
   first push unless the user already asked to push.
9. **`implement` follows a supplied plan with a two-level rule** (agreed with the user):
   - small factual drift, such as a moved file or a renamed function: follow the code and record the departure;
   - a conflict with a numbered Decision, or with Scope: stop and ask; never re-decide.
10. **`implement` honors plan metadata.** It fetches and switches to the plan's `Branch` and commits there, not
    on its own branch. It starts only when `Status` is `approved`, and reports and stops otherwise. If the
    default branch moved past `Baseline`, it re-checks the Baseline section before coding.

## Scope

In:

- `plugins/development/skills/write-plan/SKILL.md` (from `plugins/_template/skills/example-skill/SKILL.md`) and
  `skills/write-plan/references/plan-template.md` (moved and generalized from `doc/_plan-template.md`).
- `plugins/development/skills/implement/SKILL.md`: Decisions 9 and 10 (the "Supplied design" bullet in step 4
  and the "Supplied design or plan" row of the workflow table).
- `plugins/development/skills/design-solution/SKILL.md`: description and "When to use / not to use" per
  Decision 2; its closing convention points to `write-plan` for a plan to hand off.
- Both `plugin.json` copies (`skills` array, minor version `0.3.3` → `0.4.0`, `description`), both
  `marketplace.json` copies, `plugins/development/README.md`, the root `README.md` catalog row, and
  `CHANGELOG.md` `[Unreleased]`.
- `AGENTS.md`: the hand-off bullet points to the bundled template; delete `doc/_plan-template.md`.
- Trigger eval cases under `plugins/development/evals/trigger/`, modeled on `plugins/docs/evals/trigger/`:
  at least two that must fire `write-plan`, one "how would you fix this bug?" that must stay with
  `design-solution`, and one "implement this plan" that must go to `implement`.

Out:

- Any script. The skill is instructions only; git is run by the agent.
- Behavior evals.
- Changes to other plugins, and how `design-solution` writes its own design file (see Open questions).

## Baseline

| Existing | Keep, change, or remove |
| --- | --- |
| `plugins/development/skills/design-solution/SKILL.md` (141 lines) | Keep the design method; narrow the description and the hand-off use case |
| `plugins/development/skills/implement/SKILL.md` (278 lines), step 4 "Supplied design" | Change "follow the code, record the departure" to the two-level rule |
| `doc/_plan-template.md` | Move into the skill, generalize, then delete |
| `AGENTS.md` "Plan and Implement" hand-off bullet | Keep the rule; change the template path |
| `plugins/docs/evals/trigger/<case>/prompt.md` + `graders/` | Precedent for the new trigger cases |

## Tech stack and constraints

Default per `AGENTS.md`: Markdown skills, no new dependencies. Keep `SKILL.md` under ~500 lines.

## Acceptance criteria

- [ ] `write-plan/SKILL.md` exists, its frontmatter `name` is `write-plan`, and it is listed in both
      `plugin.json` copies — checked by `python3 tools/validate.py`.
- [ ] `development` is version `0.4.0` in both `plugin.json` copies and both `marketplace.json` copies, with
      matching descriptions — checked by `python3 tools/validate.py`.
- [ ] `write-plan/SKILL.md` states each rule in Decisions 6–8 itself and links nothing outside the plugin —
      checked by reading it, and by `grep -n '\.\./\.\./\.\.' plugins/development/skills/write-plan/SKILL.md`
      returning nothing.
- [ ] Failure case: `implement` told to build a `draft` plan reports that it is not approved and changes no
      file — checked by reading the new rule, and by the trigger or a manual run if one is feasible.
- [ ] Failure case: `implement` given a plan whose Decision contradicts the code stops and asks — checked by
      reading the step 4 text.
- [ ] Neither `design-solution` nor `write-plan` claims the other's phrases — checked by comparing both
      descriptions. The trigger cases exist; whether they were run is reported, not claimed.
- [ ] `doc/_plan-template.md` is gone and `AGENTS.md` points at the bundled template — checked by
      `grep -rn '_plan-template' .` returning nothing.
- [ ] `python3 tools/validate.py` passes and `for t in tools/test_*.py; do python3 "$t" || break; done` passes.

## Risks

| Risk | How it is handled |
| --- | --- |
| The two skills still fire on each other's requests | Decision 2's split, descriptions naming each other, and trigger cases on both sides |
| The skill hardcodes this repository's branch or identity rules | Decision 7; review `SKILL.md` for `Eurus`, `doc/`, or `claude/` |
| A planning session keeps pushing after hand-off and overwrites work | Decision 6 stated in `write-plan` and Decision 10 in `implement` |
| An implementing session started before this lands has the old rules | The hand-off message names the branch; the user types the instruction into that session |
| The trigger evals can't run without credentials | Report them as not run; don't claim a result |

## Open questions

1. If the repository has no plan folder, should `write-plan` create one, and what is it called? Assumed:
   create `docs/plans/` and say so.
2. Should `design-solution`, when asked to save a design, also use the plan folder instead of
   `docs/design/<topic>.md`? Assumed: no change in this plan; revisit after `write-plan` is in use.
