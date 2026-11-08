---
name: evaluate-skill
description: Evaluate an Agent Skill or a plugin's skills on three levels — static (frontmatter, description, scope, structure), triggering (does it fire on the requests it should and stay quiet on its siblings' and near-misses), and behavior (does an agent with the skill loaded produce the right outcome on a task with a known answer, compared with no skill at all) — by writing an eval suite for `claude plugin eval`, running it only with the user's agreement, and reporting what each failure means. Use when the user says "evaluate this skill", "test my skill", "does this skill work", "will this skill trigger", "write evals for this plugin", "benchmark my skill", or "is this skill better than nothing". To verify a code change, use verify-change instead; to review application code, use review-code instead.
---

# Evaluate skill

## Overview

Find out whether a skill works, not whether it reads well. The deliverable has two parts:

- **An eval suite**, written in the format `claude plugin eval` runs, under the plugin's eval directory.
- **An evaluation report**: static findings, trigger results, and behavior results with and without the skill,
  each turned into a concrete recommendation and ending in one verdict per skill.

Three levels, from cheap to expensive:

| Level | Question | Evidence |
| ----- | -------- | -------- |
| Static | Is the skill well formed and scoped? | Reading the files |
| Triggering | Does it fire on the requests it should, and stay quiet on the ones it should not? | `tool_used: Skill` graders across a set of prompts |
| Behavior | With the skill loaded, does the agent reach the right outcome on a task whose answer was written beforehand, and do better than without it? | Graded runs with and without the plugin: `WITH`, `W/OUT`, `Δ` |

## When to use this skill

- A skill or plugin is written or changed and the author wants to know whether it works.
- A skill seems not to fire, fires on the wrong requests, or fires and does the wrong thing.
- The author wants evals in place to catch regressions when the skill or the model changes.

## When not to use this skill

- **A code change needs verifying** — use `verify-change` from the `verification` plugin.
- **Application code needs reviewing** — use `review-code` from the `code-review` plugin.
- **The user wants the skill written or rewritten**, not evaluated — that is authoring work; this skill
  reports recommendations and does not edit the skill under evaluation unless asked.

## Hard rules

1. **No grading of the skill by the session that reads it.** Behavior is judged only by the eval runner's
   isolated runs against expected outcomes written in advance. This session writes the cases and reads the
   results; it never decides by itself whether an agent "would follow" the skill.
2. **Write the answer before the run, from the task, not from the skill.** Every behavior case states its
   expected outcome as concrete PASS and FAIL conditions derived from what is correct for the task. A rubric
   paraphrasing the skill's own instructions only tests that the agent repeats them. Where the repository has
   an answer key, such as `fixtures/EXPECTED.md`, it is the source; keep it out of anything the agent under
   test can read.
3. **Running costs the user money and can publish results; ask first.** Each case runs three times with the
   plugin and three without, plus judge calls. Before running, state the case count, the runs, that every run
   is a model call on their account, and a proposed `--max-cost-usd` ceiling, and get their agreement. The
   runner publishes its HTML report to claude.ai by default: pass `--no-publish` unless the user agrees to
   publish. With no one to ask, write the suite and report it `not run`.
4. **Credit the skill only for what it adds.** A case that scores the same with and without the plugin
   (`Δ` near 0) shows the task is easy, not that the skill works. A negative `Δ` is a finding against the
   skill, unless the judge is suspect (see step 7).
5. **Trigger checks need both directions.** For every skill, include prompts that should fire it and prompts
   that must not — each sibling skill's typical request, and near-misses that share words with the skill. A
   skill that fires on everything passes every should-fire case.
6. **Never edit the skill under evaluation** unless the user asks. Report each failure with the change it
   points to: a trigger failure points at the `description`; a behavior failure points at the body.
7. **Report results as they came out.** Quote the scores. A case that errored, timed out, or hit the turn cap
   is reported as such, not folded into a pass or a fail.

## Output format

### The eval suite

Under the plugin's eval directory: `evals/` by default, or the one set as `"experimental": { "evals": "<dir>" }`
in `plugin.json`. One directory per case, grouped by level:

```text
evals/
├── trigger/
│   ├── write-tests-fires-on-coverage/
│   │   ├── prompt.md
│   │   └── graders/fired.md
│   └── write-tests-quiet-on-failing-test/
│       ├── prompt.md
│       └── graders/not-fired.md
└── behavior/
    └── write-tests-reports-the-bug/
        ├── case.yaml                # context.scaffold_script seeds the fixture
        ├── scaffold.sh
        ├── prompt.md
        └── graders/
            ├── outcome.md           # the result
            └── used-skill.md        # the steps
```

A should-fire trigger case:

```markdown
---
max_turns: 3
allowed_tools: [Read, Glob, Grep, Skill]
tags: [trigger]
---

This module has no tests at all. Can you cover it?
```

```markdown
---
type: tool_used
tool: Skill
input_match: '"skill"\s*:\s*"(?:[\w-]+:)?write-tests"'
---
```

A must-not-fire case uses the same grader with `min: 0`, `max: 0`, and `arm: both`.

A behavior case's result grader, written from the task's correct answer:

```markdown
---
type: llm
---

PASS if the reply says `reserve()` accepts a zero quantity although its docstring forbids it, and the tests
it wrote assert the documented behavior.
FAIL if a test asserts that `reserve("A", 0)` succeeds, or if `inventory.py` was modified.
```

### The report

```markdown
## Skill evaluation: testing
Runner: `claude plugin eval` 2.1.319, 3 runs per arm — or: not run (reason)

## Static
| Skill | Finding | Points to |
| ----- | ------- | --------- |
| write-tests | description 1,610 characters; hand-off clause is cut at 1,536 | description |

## Triggering
| Prompt | Should | write-tests | review-tests | debug-failing-test |
| ------ | ------ | ----------- | ------------ | ------------------ |
| "This module has no tests at all. Can you cover it?" | write-tests | 3/3 | 0/3 | 0/3 |
| "Why is this test red in CI?" | debug-failing-test | 1/3 | 0/3 | 2/3 |

## Behavior
| Case | WITH | W/OUT | Δ | Finding |
| ---- | ---- | ----- | - | ------- |
| write-tests-reports-the-bug | 1.00 | 0.33 | +0.67 | — |
| write-tests-no-code-edits | 0.67 | 0.67 | 0.00 | the skill adds nothing here; one run edited the code |

## Verdict
- write-tests: needs work — fires on 1/3 failing-test prompts; tighten the description's hand-off to
  debug-failing-test.
```

Verdict per skill: `meets` (static clean, triggers correctly in both directions, `Δ` > 0 on its behavior
cases), `needs work` (name each failure and what it points to), or `not evaluated` (name what was not run
and why).

## Steps

1. **Read the skill or plugin**: every `SKILL.md` and its frontmatter, the plugin manifest, and its
   siblings — other skills in the plugin and the skills it hands off to. Note the requests each claims and
   the ones each sends elsewhere.
2. **Static review.** Check each skill against:
   - `name` equals the folder name.
   - The `description` says what the skill does and the phrases that should trigger it. It fits in 1,536
     characters, with the key use case and the hand-off clauses first.
   - A "When not to use" section names the adjacent cases and where they go.
   - Hard rules and the output format sit near the top of the body, and the body stays under about 500 lines.
   - Every bundled file is referenced. No link leaves the plugin folder. Side effects are declared.
   - No two sibling descriptions could match the same request.

   Each finding names the file, the line, and what it points to.
3. **Write the trigger cases** (hard rule 5). For each skill, write at least three should-fire prompts phrased
   as a user would type them, never naming the skill. Then write at least three must-not-fire prompts: one per
   sibling's typical request, and near-misses that share the skill's words. Use `max_turns` 3 and read-only
   tools; only the `Skill` call matters.
4. **Write the behavior cases** (hard rule 2). Use a task with a known correct outcome. That can be an existing
   fixture with its answer key, or a small one seeded by `context.scaffold_script` that holds the very defect
   the skill must not accommodate. Give each case one grader on the result and one on the steps (`tool_used`
   or `tool_order`). For long output, grade a file with `regex` rather than `llm`.
5. **Ask, then run** (hard rule 3). Run `claude plugin eval --help` first; the interface is young. Then:

   ```bash
   claude plugin eval <plugin-dir> --no-publish --max-cost-usd <agreed ceiling> \
     [--scaffold] [--allow-tools Bash Write Edit]
   ```

   Add `--scaffold` only for cases whose scaffold script you wrote, and `--allow-tools` only for the gated
   tools a behavior case needs. The first run in a plugin directory asks the user to trust it; never pass
   `--trust-plugin` on their behalf. If the command is missing, too old, or unavailable for the account, or if
   the plugin does not resolve from its directory, stop at the written suite and say why.
6. **Read the results** from `evals/results/<timestamp>/aggregate-result.json` and fill the report. A
   trigger case's numbers come from its `tool_used` grader in the with-arm. A behavior case's come from
   `WITH`, `W/OUT`, and `Δ`.
7. **Suspect the judge before the skill** when a `Skill` grader passes but `Δ` is negative. Re-run that case
   with `--judge-model sonnet` and tighten the rubric so formatting cannot decide it.
8. **Report** in the output format, with one verdict per skill and each failure tied to what it points to.

## Bundled resources

None. The case formats used are in [Output format](#output-format); `claude plugin eval --help` is the
authority on the runner's current options.

## Conventions

- **Side effects.** Writes the eval suite under the plugin's eval directory. With the user's agreement, runs
  `claude plugin eval`, which makes model calls billed to their account and writes
  `evals/results/<timestamp>/`, and which publishes its report to claude.ai unless `--no-publish` is passed. Recommend adding `results/` under the eval directory to `.gitignore`;
  propose it, do not make the edit. Installs nothing; never edits the skill under evaluation unless asked.
- A suite written once is meant to be re-run after every change to the skill and on new models. Keep case
  names stable, so results can be compared.
