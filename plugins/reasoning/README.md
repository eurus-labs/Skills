# reasoning

Plan a change before anyone codes it. One skill analyzes a new requirement against its previous version and
splits it into epics; one answers design questions in the conversation; one writes a plan to a file on its own
branch; one hands the approved plan to a coder and reviews the result. None changes application code.

Meant for planning sessions on a high-tier model (Opus, Fable, GPT "astra" on Copilot). Building the plan is
`implement`, in the `development` plugin.

## Install

```bash
copilot plugin marketplace add eurus-labs/Skills
copilot plugin install reasoning@eurus-labs
```

Install `development@eurus-labs` where the coder subagent runs, which is the planning host, or in the session
where you run a plan yourself. `implement` works from a plan without `reasoning` installed.

## Skills

- **`analyze-requirements`** — the requirement loop, on files that share one ID scheme. It compares the current
  requirement (`.md`, `.txt` or `.rst`, or pasted) with the previous version (another file, or the same file at
  an earlier git revision), checks each changed requirement against the repository's code with `path:line`, and
  writes `analysis.md`: the change table (`R-001…`), the findings, the open points for the Product Owner
  (`OP-001…`, each marked blocking or not), the assumptions and a revision history. From the user's notes of a
  PO discussion it drafts `dou-NNN.md` (or reads a DoU the user brings), records only what the PO said, and
  updates the analysis, keeping superseded rows. It writes `epics.md` only when no blocking open point is open,
  unless you explicitly ask for provisional epics. Fires on "compare this requirement with the previous
  version", "update the analysis from the DoU", "split into epics", "cập nhật requirement analysis từ DoU với PO".
- **`design-solution`** — an implementation-ready design, grounded in the current code, answered in the
  conversation: goal, scope, acceptance criteria, constraints, affected components, decisions with the
  alternatives they beat, steps, a verification plan, and open questions. Fires on "design this", "compare
  approaches", "which design pattern fits", "how would you fix this bug?". It writes a file only when you ask
  it to save the design, and then into the repository's plan folder.
- **`write-plan`** — a plan document for another session to implement: numbered Decisions, scope, acceptance
  criteria, risks, and open questions, from a bundled template. It creates the plan's branch from the latest
  default branch, commits the plan with `Status: draft`, confirms before the first push, and revises it until
  you approve. Fires on "write the plan to a file", "plan this for another session".
- **`coder-handoff`** — starts when you approve a plan. It sets `Status: approved` and pushes (its last push
  to the branch), then dispatches the plan to a subagent on a model at least one tier below the planner's, from
  Sonnet, Haiku, terra or luna (Opus or Fable hands off to Sonnet, Sonnet to Haiku, astra or sol to terra, terra
  to luna; the lowest tier hands off to itself). In Claude Code that is the Agent tool with `model: sonnet`
  and `isolation: worktree`. It asks you when it does not know the planner's model, and asks before using a
  coder you name that breaks the rule. When the subagent's report returns, it reviews the
  branch against the plan's acceptance criteria and opens the pull request only if every one is met; otherwise
  it sends the gaps to a new subagent run. It merges only when you ask. A host that cannot start a subagent
  gets a stop and the instruction to run the plan with `implement`. Fires on "approved, hand it to the coder",
  "giao plan này cho coder", "the coder is done, review the branch", "open the PR for plan 6".

| You ask for | Skill |
| ----------- | ----- |
| A requirement compared with its previous version, open points for the PO, a DoU, epics | `analyze-requirements` |
| Advice, a comparison, or "how would you…", answered in chat | `design-solution` |
| A plan saved to a file | `write-plan` |
| An approved plan given to a coder subagent, then reviewed | `coder-handoff` |
| The change made, or an approved plan built | `implement`, in the `development` plugin |

## How the requirement analysis works

1. Give it the current requirement and, if there is one, the previous version. It runs
   `scripts/requirements.py diff`, which lists every added, removed, changed and unchanged unit with its line
   range, then reads each change, checks the code, and writes `analysis.md` in `requirements/<topic>/`.
2. Take its open points to the PO. Bring back your notes, or a DoU file; it drafts or reads the DoU and updates
   the analysis. A point the notes leave unanswered stays open.
3. When no blocking open point remains, ask for epics. It writes `epics.md` with every in-scope requirement in
   exactly one epic, and a traceability table.
4. After every write it runs `scripts/requirements.py check`, which fails on a duplicated ID, an unknown ID, a
   resolved point with no DoU, a requirement in no epic, and non-provisional epics while a blocking point is open.

## How the hand-off works

1. `write-plan` writes the plan with `Status: draft` on its own branch, committed and pushed (after you
   confirm the push), and revises it with you.
2. You approve. `coder-handoff` sets `Status: approved` (only you decide this), pushes it, and stops pushing to
   that branch.
3. It dispatches the plan to a subagent on a lower-tier model than the planner's (Sonnet when the planner is
   Opus or Fable). The planner does not touch the branch while
   the subagent runs. If the host cannot start a subagent, it stops and tells you to run the plan with
   `implement`, with the branch, plan path, and baseline sha. It never writes session ids into committed files.
4. `implement` starts only when `Status` is `approved`, works and commits on the plan's branch, follows the
   numbered Decisions as written, and stops to ask on a conflict with a Decision or the Scope. It never opens
   or merges a pull request. Its last commit changes only `Status` to `implemented`, and its final report
   returns to the planner.
5. On the report, the planner reads `Status` at the branch head: `approved` means the coder did not finish, so
   it does not review; `implemented` means it reviews.
6. If every acceptance criterion is met, it opens the pull request and reports to you. If not, it opens
   nothing and sends the gaps to a new subagent run on the same branch. It merges only when you ask.
7. Changes to the plan after hand-off go through you.

Branch naming, commit identity, commit format, and the default branch come from the repository's own
instructions (`AGENTS.md`, `CONTRIBUTING.md`, and similar). When the repository says nothing, the branch is
`<type>/<area>-<outcome>` and the commit identity comes from you, never an AI identity. Plans go in the folder
that already holds plan documents; with none, `write-plan` creates `docs/plans/` and says so.

## Keeping this plugin to planning sessions

The plugin cannot enforce which model uses it. No skill field restricts the model, and a skill that tells a
model to stop "if you are not model X" cannot work, because a model cannot reliably tell which one it is.
Where you install the plugin decides who uses it. Each method below says whether it has been verified.

| Host | How to load it in planning sessions only | Status |
| ---- | ---------------------------------------- | ------ |
| Claude Code, terminal | Install at local scope (`.claude/settings.local.json`) in a checkout you use for planning, or load it for one session with `--plugin-dir` | **Unverified.** Both are documented by Anthropic; neither was tried here |
| Copilot CLI | Load it for one session with `--plugin-dir`, and set `COPILOT_PLUGIN_DIR_ONLY=true` to keep other plugins out | **Verified.** This repository's `tools/copilot_eval.py` runs Copilot with both. Any other Copilot scoping is unverified |
| Claude Code, cloud sessions | Cloud sessions do not load locally installed or repository-enabled plugins; plugins come from the claude.ai account or the organization | **Unverified.** Per-session selection there has not been checked |

## Notes

- **Side effects:** `analyze-requirements` writes `analysis.md`, `dou-NNN.md` and `epics.md` in its topic folder
  and never commits them unless you ask. Its bundled script, `requirements.py`, is standard library only, reads
  only the files it is given, makes no network call and writes nothing. `write-plan` creates a local branch, writes one file, and commits it. It pushes only
  after you confirm, unless you already asked it to push. `coder-handoff` pushes the approval commit, starts a
  subagent, and opens the pull request after a passing review; it merges only when you ask. Neither installs anything or runs scripts.
  `design-solution` writes nothing except a design file you ask for.
- `design-solution` was part of `development` before `development` 0.4.0. Install `reasoning@eurus-labs` to
  keep it.
- The plan template is `skills/write-plan/references/plan-template.md`. It is generic: its constraints
  section defaults to the repository's own documented constraints.
