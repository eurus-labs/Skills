# Plan 11 — `coder-handoff` always dispatches to a lower-tier model than the planner

Status: draft
Date: 2026-11-17
Branch: `feat/reasoning-handoff-lower-tier`
Baseline: `origin/main` at `e679abc4fe12215a6eee3cb71898946f65bfeedf`
Target: `plugins/reasoning/skills/coder-handoff/SKILL.md`, `plugins/reasoning/README.md`, `AGENTS.md`,
the `reasoning` version in its manifests, `CHANGELOG.md`

## Goal

The user wants `coder-handoff` to **always** hand the plan to a model of a **lower tier than the model running
the planning session**. Planning needs the strong model; building from a settled plan does not, and the
cheaper model is the point of the hand-off.

Today the skill only says "a subagent on the implementing model, for example the Agent tool with
`model: sonnet`" (`SKILL.md:118`). That gives no rule:

- a planner on Sonnet would hand off to Sonnet, the same tier;
- nothing tells the skill what to do when no lower model exists, or when it does not know its own model.

When this is done, the skill picks the coder model by a written rule and names it in its report. It never
dispatches to a model of the same or a higher tier than the planner, or to a model outside the allowed coder
set, unless the user explicitly confirms.

## Decisions

1. **New hard rule: the coder is at least one tier below the planner, and only from the allowed set.**
   Both conditions must hold:
   - **At least one tier lower:** two or more tiers lower is fine; the same tier or a higher one is not.
   - **The allowed coder set:** Claude **Sonnet**, or GPT **terra** or **luna**. No other model is a coder.
     Haiku is not a coder, because it is too weak to build a plan.

   The tiers, highest first, are:
   - Claude: Fable, Opus, Sonnet, Haiku;
   - GPT on Copilot: astra, terra, luna.

   This gives:

   | Planner | Coder |
   | --- | --- |
   | Claude Fable or Opus | Sonnet |
   | Claude Sonnet or Haiku | none allowed: stop (Decision 4) |
   | GPT astra | terra by default, luna if the user names it |
   | GPT terra | luna |
   | GPT luna | none allowed: stop (Decision 4) |

   The coder comes from the planner's own family, because each host runs one family's subagents. A planner
   on another family or model asks the user (Decision 3). For an astra planner, terra is the default because
   it is the stronger of the two allowed coders. Rejected:
   - always `model: sonnet`, because a Sonnet planner would then hand off to its own tier;
   - exactly one tier lower, because the user asked for "at least one tier lower", bounded by the allowed set.
2. **The planner learns its own model from the host, never by guessing.** Use what the host states about the
   session: the model named in its system prompt or session information, or a model the user named. If the
   host states nothing, ask the user which model the planning session runs on before dispatching. Rejected:
   inferring the model from the planner's own sense of its identity, because the plugin README already notes
   that a model cannot reliably tell which one it is. That note is about enforcing who may *use* the plugin.
   Reading a model name the host states is a different matter, and it is allowed.
3. **Other models.** If the planner's model is in neither tier list, ask the user which allowed coder to use.
   Do not guess a tier.
4. **No allowed coder: stop.** If no model in the allowed set is at least one tier below the planner (a
   Claude Sonnet or Haiku planner, or a GPT luna planner), or the host cannot run the allowed model, do not
   dispatch. Tell the user, the same way as rule 3 (no subagent): give the branch, the plan path and the
   baseline, and say that a planner on a higher tier, or `implement` run by the user, can build it.
5. **The user can override only explicitly.** Ask for confirmation before dispatching if the user names a
   coder that:
   - is not at least one tier below the planner; or
   - is outside the allowed set (for example Haiku).

   Say which rule the choice breaks, and dispatch only after they confirm. A user naming the other allowed
   coder (luna in place of terra) is followed without asking.
6. **The model is named where it matters:**
   - the dispatch step says to pass the chosen model to the subagent tool;
   - the report to the user names the planner's model and the coder's, for example
     `Coder: sonnet (planner: opus; one tier lower)`;
   - the "host cannot start a subagent" message (rule 3) names a lower-tier model to run `implement` with.
7. **Wording elsewhere follows the rule:**
   - The `description` frontmatter says "a coder subagent on a lower-tier model than the planner" in place of
     "on the implementing model". It keeps its trigger phrases, including "giao cho Sonnet implement", so it
     fires as before.
   - `plugins/reasoning/README.md` and `AGENTS.md` (the hand-off bullet) say the same. `AGENTS.md` keeps
     `model: sonnet` as this repository's case, because its planning sessions run on Opus or Fable.
8. **Version.** `reasoning` 0.2.2 → 0.3.0, a minor bump because the dispatch behavior changes. Update every
   manifest that carries the version, plus a `### Changed` entry under `[Unreleased]` in `CHANGELOG.md`.
   Released sections stay untouched.

## Scope

In:

- `plugins/reasoning/skills/coder-handoff/SKILL.md`:
  - the description (Decision 7);
  - a new hard rule for Decisions 1 to 5;
  - step 3 Dispatch (Decision 6);
  - the Output format: the report line and the no-subagent message (Decision 6).
- `plugins/reasoning/README.md`: the `coder-handoff` paragraph and the steps that say "implementing model".
- `AGENTS.md`: the Plan-and-Implement hand-off bullet. The file must stay under 120 lines.
- `reasoning` version in `plugins/reasoning/.github/plugin/plugin.json`, `.claude-plugin/plugin.json`, and
  both `marketplace.json` copies.
- `CHANGELOG.md` `[Unreleased]`.

Out:

- `write-plan`, `design-solution` and `implement`. None of them chooses a model.
- Enforcing the planner's tier, that is, who may use the plugin. The README's "Keeping this plugin to planning
  sessions" section stays as it is.
- New eval cases. The rule changes what happens after the skill fires, not when it fires. Behavior evals for
  `coder-handoff` do not exist yet.
- Plans 1 to 10. Their text records what was decided then.

## Baseline

| Existing | Keep, change, or remove |
| --- | --- |
| `coder-handoff/SKILL.md:3` description: "dispatch it to a coder subagent on the implementing model … (for example the Agent tool with model sonnet …)" | Change per Decision 7; keep every trigger phrase |
| `coder-handoff/SKILL.md:11` Overview: "dispatches the plan to a subagent on the implementing model" | Change to say a lower-tier model |
| `coder-handoff/SKILL.md:41-79` Hard rules 1–10 | Keep; add the new rule as 11, so other rules keep their numbers (step text cites rules 3, 4, 6, 7, 8, 9) |
| `coder-handoff/SKILL.md:118` step 3: "Start a subagent on the implementing model, for example the Agent tool with `model: sonnet`" | Change per Decisions 1, 6 |
| `coder-handoff/SKILL.md` Output format: the subagent prompt, the review report, and the "Cannot dispatch" message | Add the coder-model line to the review report and a model line to "Cannot dispatch"; the subagent prompt is unchanged |
| `plugins/reasoning/README.md:32-33, 52` "on the implementing model (in Claude Code, the Agent tool with `model: sonnet` …)" | Change per Decision 7 |
| `plugins/reasoning/README.md:70-80` "Keeping this plugin to planning sessions" | Keep unchanged |
| `AGENTS.md:63` "dispatches the plan to a subagent on the implementing model (in Claude Code, the Agent tool with `model: sonnet` and `isolation: worktree`)" | Change per Decision 7 |
| `reasoning` version 0.2.2 (`plugins/reasoning/.github/plugin/plugin.json:4`) | 0.3.0 everywhere it appears |

## Tech stack and constraints

Default. Skill text only; no script changes. `SKILL.md` stays under about 500 lines (today 150), and
`AGENTS.md` stays under 120 lines.

## Acceptance criteria

- [ ] `coder-handoff/SKILL.md` has a hard rule that holds the tier lists, the allowed coder set and the
      table from Decision 1, and the rules of Decisions 2 to 5. Checked by
      `grep -n "Fable\|Opus\|Sonnet\|Haiku\|astra\|terra\|luna" plugins/reasoning/skills/coder-handoff/SKILL.md`
      and by reading.
- [ ] The failure cases are covered in the text. Checked by reading; the coder's report quotes the lines.
      - An unknown planner model asks the user (Decisions 2 and 3).
      - No allowed coder stops the hand-off and gives the branch, plan and baseline (Decision 4). This
        includes a Sonnet planner.
      - A coder the user requests that is not lower, or is outside the set, needs confirmation (Decision 5).
- [ ] Step 3 and the Output format name the chosen model, and the review report example has a line like
      `Coder: sonnet (planner: opus; one tier lower)`. Checked by
      `grep -n "Coder:" plugins/reasoning/skills/coder-handoff/SKILL.md`.
- [ ] No text in `plugins/reasoning/` or `AGENTS.md` still describes the coder only as "the implementing
      model" without the lower-tier rule. Checked by `grep -rn "implementing model" plugins/reasoning AGENTS.md`,
      with each hit read in context.
- [ ] The description keeps its trigger phrases. Checked by
      `grep -c "giao cho Sonnet implement\|giao plan này cho coder\|the coder pushed" plugins/reasoning/skills/coder-handoff/SKILL.md`,
      which must print a number of at least 1, and by comparing the old and new description.
- [ ] `reasoning` is 0.3.0 in every manifest, and `[Unreleased]` has the entry. Checked by
      `grep -rn '"version"' plugins/reasoning/.github plugins/reasoning/.claude-plugin` and
      `grep -n -A3 '"name": "reasoning"' .github/plugin/marketplace.json .claude-plugin/marketplace.json`.
- [ ] `AGENTS.md` stays under 120 lines. Checked by `wc -l AGENTS.md`.
- [ ] The repository's required checks pass: `python3 tools/validate.py`,
      `python3 tools/materialize.py --check`, and `for t in tools/test_*.py; do python3 "$t" || break; done`.

## Risks

| Risk | How it is handled |
| --- | --- |
| The planner misreads its own model and picks the wrong tier | Decision 2: only a model the host or the user states counts; otherwise ask. The report names both models, so the user sees the choice |
| Tier names change (a new family or a renamed model) | The table is the default for Claude models; Decision 3 covers others by asking. A new family needs a one-row edit |
| The description change makes the skill fire differently | The trigger phrases are kept. The planner reruns the `reasoning` trigger evals in review (`claude plugin eval plugins/reasoning --tag trigger --ablation none --no-publish --max-cost-usd 3`) and reports the score |
| A Sonnet planner can no longer hand off at all | Intended: the allowed set has nothing below Sonnet. Decision 4 stops with what the user needs to run it another way |
| The GPT tier order astra > terra > luna is wrong | It comes from the user's naming in this conversation (astra as the high tier, terra and luna as coders). The planner confirms the order with the user before approval |

## Open questions

None.
