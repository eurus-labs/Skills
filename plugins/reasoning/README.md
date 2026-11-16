# reasoning

Plan a change before anyone codes it. One skill answers design questions in the conversation; the other writes
a plan to a file on its own branch, so a separate session can build it. Neither changes application code.

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
  default branch, commits the plan, confirms before the first push, and ends with the hand-off message: the
  branch, the plan path, and the baseline sha. Fires on "write the plan to a file", "plan this for another
  session", "hand this off".

| You ask for | Skill |
| ----------- | ----- |
| Advice, a comparison, or "how would you…", answered in chat | `design-solution` |
| A plan saved to a file and handed to another session | `write-plan` |
| The change made, or an approved plan built | `implement`, in the `development` plugin |

## How the hand-off works

1. The planning session writes the plan with `Status: draft` on its own branch, committed and pushed (after
   you confirm the push).
2. You review and revise it with the planning session. Only you set `Status: approved`; on your word the
   planner makes one last commit and pushes it, then stops pushing to that branch.
3. The planning session hands the plan over: it sends the hand-off (branch, plan path, baseline sha) to the
   implementer session you name when the host has a cross-session messaging tool (for example `send_message`
   in Claude Code cloud sessions), otherwise it gives you the message to paste into that session. It never
   writes session ids into committed files.
4. `implement` starts only when `Status` is `approved`, works and commits on the plan's branch, follows the
   numbered Decisions as written, and stops to ask you when the code conflicts with a Decision or with the
   Scope. It never opens a pull request or merges. When its work is pushed, it tells the planning session the
   branch is ready for review, by messaging tool where available, otherwise by telling you.
5. The planning session reviews the branch against the plan's acceptance criteria and, when all are met, opens
   the pull request. It merges only when you ask.
6. Changes to the plan after hand-off go through you.

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
  after you confirm, unless you already asked it to push. It installs nothing and runs no scripts.
  `design-solution` writes nothing except a design file you ask for.
- `design-solution` was part of `development` before `development` 0.4.0. Install `reasoning@eurus-labs` to
  keep it.
- The plan template is `skills/write-plan/references/plan-template.md`. It is generic: its constraints
  section defaults to the repository's own documented constraints.
