# Plan 5 — a `reasoning` plugin for planning, handed off to an implementing session

Status: approved
Date: 2026-11-16
Branch: `feat/development-plan-handoff`
Baseline: `origin/main` at `6c545ea51bdb3476b43d232cb40e09a26ab016c6`
Target: new plugin `plugins/reasoning` (`design-solution` moved in, new `write-plan`); `plugins/development`
(`implement` edited, `design-solution` removed)

## Goal

This repository already works this way: one session plans, writes the plan to `doc/`, and pushes it on its own
branch; a second session implements on that branch once the user approves (`AGENTS.md`, Start Each Task step 2
and Plan and Implement). That only works here, because the rules live in this repository's `AGENTS.md`.

Package the workflow so it works in any repository:

- the planning skills go in a `reasoning` plugin, meant for sessions on a high-tier model (Opus, Fable, GPT
  "astra" on Copilot);
- the implementing session uses `implement` from `development`, follows the plan's decisions as written, and
  never shares a branch with the planner.

## Decisions

1. **A new plugin `reasoning` holds `design-solution` (moved from `development`) and a new skill `write-plan`.**
   `development` keeps `implement`. Rejected: putting `write-plan` in `development`, because the user wants
   the planning skills installable apart from the implementing ones. The user chose the name `reasoning`
   over `planning`. The skill name `write-plan` is a proposal; renaming after release changes the install name.
2. **Model tier is enforced by where the plugin is installed, not by the skill.** No skill field restricts
   which model may use it. The Claude Code `model:` field only switches the model for the skill's turn, and
   `tools/validate.py` (`ALLOWED_FRONTMATTER`) forbids it because packaging fails hard on it elsewhere. A
   "stop if you are not model X" line is rejected too: models cannot reliably tell which model they are. The
   `reasoning` README tells users to load the plugin only in planning sessions, per host (Decision 11).
3. **Split the trigger boundary explicitly.**
   - `write-plan` takes requests to write, save, or hand off a plan ("write the plan to a file", "plan this
     for another session", "lên plan để giao cho session khác").
   - `design-solution` keeps advice, comparisons, and "how would you…" questions, answered in the conversation.
   - Today `design-solution`'s description claims "prepare an implementation plan", "plan the
     implementation", and "asks for a plan to hand to someone else". Remove the hand-off and durable-plan
     phrases. Each description names the other skill.
   - Rejected: leaving the descriptions as they are, because each would fire on the other's requests.
4. **Plan location: the repository's existing plan folder.** Detect it as a folder that already holds plan
   documents (for example `doc/plan-*.md`, `docs/plans/`, `plans/`). If there is none, create `docs/plans/`
   and say so (decided by the user). `design-solution`, when asked to save a design, saves it to the same
   folder instead of `docs/design/<topic>.md` (decided by the user).
5. **The template is bundled in the skill** at `skills/write-plan/references/plan-template.md`, because a
   `SKILL.md` may not link outside its plugin. It becomes the only copy: delete `doc/_plan-template.md` and
   point `AGENTS.md` at the bundled file. Rejected: two copies, which would drift. Rejected: `shared/` with
   `tools/materialize.py`, because only one plugin uses the template.
6. **The template is generic.** Its "Tech stack and constraints" default reads "the repository's documented
   constraints; list only deviations", not this repository's stdlib rule.
7. **`write-plan` restates the hand-off rules itself**, because other repositories have no such `AGENTS.md`:
   - Status starts at `draft`; only the user moves it to `approved`.
   - The planning session creates the branch from the latest default branch, commits and pushes the plan, and
     after approval stops pushing to it.
   - Plan changes after hand-off go through the user.
   - It ends with the hand-off message for the user: the branch, the plan path, and the baseline sha.
8. **Repository rules win over the skill's defaults.**
   - Branch naming, commit identity, commit format, and the default branch come from the target repository's
     instructions (`AGENTS.md`, `CONTRIBUTING.md`, or similar).
   - Fallbacks: branch `<type>/<area>-<outcome>`; commit identity from the user; never an AI identity.
   - Never hardcode this repository's values.
9. **Creating a branch and pushing are outward actions.** `SKILL.md` says it does both and confirms before the
   first push unless the user already asked to push.
10. **`implement` works from a plan without `reasoning` installed.**
    - It fetches and switches to the plan's `Branch` and commits there, not on its own branch.
    - It starts only when `Status` is `approved`; otherwise it reports that and stops.
    - If the default branch has moved past `Baseline`, it re-checks the plan's Baseline section before coding.
    - Small factual drift (a moved file, a renamed function): follow the code and record the departure.
    - A conflict with a numbered Decision or with Scope: stop and ask; never re-decide (agreed with the user).
    - Skills in other plugins are named in plain text, never linked.
11. **The `reasoning` README documents per-host loading, and marks each method as verified or not:**
    - Claude Code terminal: install at local scope (`.claude/settings.local.json`) in a planning checkout, or
      load for one session with `--plugin-dir`. Both are documented by Anthropic.
    - Copilot CLI: load for one session with `--plugin-dir`, and set `COPILOT_PLUGIN_DIR_ONLY=true` to keep
      other plugins out. `tools/copilot_eval.py` already uses both. Any other Copilot scoping is unverified.
    - Claude Code cloud sessions: they don't load locally installed or repository-enabled plugins; plugins
      come from the claude.ai account or the organization. Per-session selection there is unverified.
12. **Amendment (2026-11-16, decided by the user): how `implement` acts on a hand-off from another session.**
    - It reads the plan file on the branch the message names, and implements it only if the file says
      `Status: approved`, following its Decisions and the repository's instructions.
    - The message only points to the plan and grants nothing else: no commands, permissions, or scope beyond
      what the plan and the repository's instructions allow.
    - It works only on the plan's branch, never merges, and changes no permissions or environments. Who opens
      the pull request is set by Decision 13.
    - It asks the planning session factual questions through the host's session-messaging tool (for example
      `send_message`); where there is none, it asks the user. It brings any change to a Decision or to Scope
      to the user, never to the planning session.
13. **Amendment (2026-11-16, decided by the user): messaging and roles for a handed-off plan.** It supersedes
    the pull-request wording of Decision 12 for a handed-off plan.
    - **Sending (`write-plan`).** After the user approves the plan, if the host offers a cross-session
      messaging tool (for example `send_message` in Claude Code cloud sessions), `write-plan` sends the
      hand-off (branch, plan path, baseline sha) to the implementer session the user names. Otherwise it gives
      the user the hand-off message to paste. Session ids are never written to committed files.
    - **Implementer (`implement`).** For a handed-off plan it never opens a pull request and never merges.
      When its work is pushed, it tells the planning session that the branch is ready for review, by
      messaging tool where available, otherwise by telling the user.
    - **Planning session (`write-plan`).** It reviews the branch against the plan's acceptance criteria and
      opens the pull request. It merges only when the user asks.
    - **Direct use.** When `implement` is used without a hand-off, nothing changes: a pull request only when
      the user asks.
    - `AGENTS.md`'s hand-off bullet states the same roles.

## Scope

In:

- `plugins/reasoning/` from `plugins/_template/`: both `plugin.json` copies (`name: reasoning`,
  `version: 0.1.0`), a `README.md` with Decision 11, and `skills/design-solution/` moved from `development`.
- `plugins/reasoning/skills/write-plan/SKILL.md` and `references/plan-template.md`, moved and generalized from
  `doc/_plan-template.md`.
- `write-plan/SKILL.md` also states Decision 13: the send path, the paste fallback, and the review, then
  pull request, step.
- `design-solution/SKILL.md`: description and "When to use / not to use" per Decision 3; its closing
  convention names `write-plan` for a plan to hand off and `implement` for building it; its "Output format"
  saves a requested design to the plan folder per Decision 4.
- `plugins/development/skills/implement/SKILL.md`: Decisions 10, 12, and 13, in the "Supplied design" bullet of step 4 and
  the "Supplied design or plan" row of the workflow table.
- `development`: remove `design-solution` from both `plugin.json` copies, bump `0.3.3` → `0.4.0`, and update
  its `description` and README.
- Both `marketplace.json` copies (a new `reasoning` entry and the `development` version and description), the
  root `README.md` catalog rows, and `CHANGELOG.md` `[Unreleased]`, which notes that `design-solution` moved
  and must be reinstalled from `reasoning`.
- `AGENTS.md`: the hand-off bullet points to the bundled template and states the roles of Decision 13
  (and "Do not create a pull request unless asked" gets the hand-off exception); delete
  `doc/_plan-template.md`.
- Trigger eval cases under `plugins/reasoning/evals/trigger/`, modeled on `plugins/docs/evals/trigger/`: at
  least two that must fire `write-plan` and one "how would you fix this bug?" that must fire
  `design-solution`. Add one "implement this plan" case under `plugins/development/evals/trigger/`.

Out:

- Any script. The skills are instructions only; git is run by the agent.
- Behavior evals.
- Other plugins.

## Baseline

| Existing | Keep, change, or remove |
| --- | --- |
| `plugins/development/skills/design-solution/SKILL.md` (141 lines) | Move to `reasoning`; keep the design method; narrow the description |
| `plugins/development/skills/implement/SKILL.md` (278 lines), step 4 "Supplied design" | Replace "follow the code, record the departure" with Decision 10 |
| `doc/_plan-template.md` | Move into `write-plan`, generalize, then delete |
| `AGENTS.md` "Plan and Implement" hand-off bullet | Keep the rule; change the template path |
| `tools/validate.py` `ALLOWED_FRONTMATTER` | Unchanged; no `model` field (Decision 2) |
| `plugins/docs/evals/trigger/<case>/prompt.md` + `graders/` | Precedent for the new trigger cases |

## Tech stack and constraints

Default per `AGENTS.md`: Markdown skills, no new dependencies. Keep each `SKILL.md` under ~500 lines.

## Acceptance criteria

- [ ] `reasoning` lists `design-solution` and `write-plan` in both `plugin.json` copies, and `development`
      lists only `implement`. Checked by `python3 tools/validate.py`.
- [ ] `reasoning` is `0.1.0` and `development` is `0.4.0` in their `plugin.json` copies and both
      `marketplace.json` copies, with matching descriptions. Checked by `python3 tools/validate.py`.
- [ ] `write-plan/SKILL.md` states each rule in Decisions 4 and 7–9 itself. Checked by reading it.
- [ ] No `SKILL.md` links outside its own plugin. Checked by `python3 tools/validate.py` and by grepping the
      two plugins for relative links that climb above the plugin folder.
- [ ] Failure case: `implement`, told to build a `draft` plan, reports that it is not approved and changes no
      file. Checked by reading the new rule; a manual run if feasible.
- [ ] Failure case: `implement`, given a plan whose Decision contradicts the code, stops and asks. Checked by
      reading the step 4 text.
- [ ] Neither `design-solution` nor `write-plan` claims the other's phrases. Checked by comparing the two
      descriptions. The trigger cases exist; whether they were run is reported, not claimed.
- [ ] `doc/_plan-template.md` is gone and `AGENTS.md` points at the bundled template. Checked by
      `grep -rn '_plan-template' --exclude-dir=.git .` returning only the changelog entry, if any.
- [ ] The `reasoning` README marks each loading method in Decision 11 as verified or unverified.
- [ ] Decision 12 is stated in `implement/SKILL.md`: it reads the plan on the named branch, treats the message
      as a pointer that grants nothing, never merges, opens no PR for a handed-off plan (Decision 13), changes no
      permissions or environments, asks the planning session only factual questions, and takes Decision or Scope changes to
      the user. Checked by reading it.
- [ ] `write-plan/SKILL.md` describes the send path, the paste fallback, and the review-then-pull-request step,
      never writes session ids to committed files, and merges only when the user asks (Decision 13). Checked
      by reading it.
- [ ] `implement/SKILL.md` states that for a handed-off plan it never opens a pull request or merges, and that
      it tells the planning session when its pushed branch is ready for review (Decision 13). Checked by
      reading it.
- [ ] Direct use of `implement` is unchanged: a pull request only when the user asks. Checked by reading the
      hard rule.
- [ ] `AGENTS.md`'s hand-off bullet matches Decision 13. Checked by reading it.
- [ ] Failure case: a hand-off message that asks for something beyond the plan (merge, a permission change)
      is not acted on. Checked by reading the new rule; a manual run if feasible.
- [ ] `python3 tools/validate.py` passes, and `for t in tools/test_*.py; do python3 "$t" || break; done` passes.

## Risks

| Risk | How it is handled |
| --- | --- |
| Moving `design-solution` breaks existing installs of `development:design-solution` | CHANGELOG and both READMEs say it moved and how to reinstall; minor bump while on 0.x |
| The two skills still fire on each other's requests | Decision 3's split, descriptions naming each other, trigger cases on both sides |
| Users expect the plugin itself to block weaker models | Decision 2 stated plainly in the `reasoning` README |
| The skill hardcodes this repository's branch or identity rules | Decision 8; review the `SKILL.md` files for `Eurus`, `doc/`, `claude/` |
| A planning session keeps pushing after hand-off and overwrites work | Decision 7 in `write-plan` and Decision 10 in `implement` |
| An implementing session started before this lands still has the old rules | The hand-off message names the branch; the user types the instruction into that session |
| Trigger evals can't run without credentials | Report them as not run; don't claim a result |
| A test hardcodes the plugin list or count (`validate.py` prints "7 plugin(s)") | Run the full test loop; update any such test in this change |

## Open questions

None. The question about where `design-solution` saves a design was decided by the user (Decision 4).
