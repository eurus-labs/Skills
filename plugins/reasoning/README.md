# reasoning

Plan a change before anyone codes it. One skill answers design questions in the conversation; one writes a
plan to a file on its own branch; one hands the approved plan to a coder and reviews the result. None changes
application code.

Meant for planning sessions on a high-tier model (Opus, Fable, GPT "astra" on Copilot). Building the plan is
`implement`, in the `development` plugin.

## Install

```bash
copilot plugin marketplace add eurus-labs/Skills
copilot plugin install reasoning@eurus-labs
```

Install `development@eurus-labs` in the session that implements. `implement` works from a plan without
`reasoning` installed.

## Skills

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
  to the branch), then dispatches the plan to a subagent on the implementing model (in Claude Code, the Agent
  tool with `model: sonnet` and `isolation: worktree`). When the subagent's report returns, it reviews the
  branch against the plan's acceptance criteria and opens the pull request only if every one is met; otherwise
  it sends the gaps to a new subagent run. It merges only when you ask. A host that cannot start a subagent
  gets a stop and the instruction to run the plan with `implement`. Fires on "approved, hand it to the coder",
  "giao plan này cho coder", "the coder is done, review the branch", "open the PR for plan 6".

| You ask for | Skill |
| ----------- | ----- |
| Advice, a comparison, or "how would you…", answered in chat | `design-solution` |
| A plan saved to a file | `write-plan` |
| An approved plan given to a coder subagent, then reviewed | `coder-handoff` |
| The change made, or an approved plan built | `implement`, in the `development` plugin |

## How the hand-off works

1. `write-plan` writes the plan with `Status: draft` on its own branch, committed and pushed (after you
   confirm the push), and revises it with you.
2. You approve. `coder-handoff` sets `Status: approved` (only you decide this), pushes it, and stops pushing to
   that branch.
3. It dispatches the plan to a subagent on the implementing model. The planner does not touch the branch while
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

- **Side effects:** `write-plan` creates a local branch, writes one file, and commits it. It pushes only
  after you confirm, unless you already asked it to push. `coder-handoff` pushes the approval commit, starts a
  subagent, and opens the pull request after a passing review; it merges only when you ask. Neither installs anything or runs scripts.
  `design-solution` writes nothing except a design file you ask for.
- `design-solution` was part of `development` before `development` 0.4.0. Install `reasoning@eurus-labs` to
  keep it.
- The plan template is `skills/write-plan/references/plan-template.md`. It is generic: its constraints
  section defaults to the repository's own documented constraints.
