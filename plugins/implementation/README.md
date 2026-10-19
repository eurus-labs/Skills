# implementation

Design a change to a repository, or make it and prove it works. Two skills, each usable on its own: the
boundary between them is the deliverable you ask for, not whether design thinking happens.

## Install

```bash
copilot plugin marketplace add eurus-labs/Skills
copilot plugin install implementation@CopilotBox
```

## Skills

- **`design-solution`** — an implementation-ready design and plan, grounded in the current code: goal, scope,
  acceptance criteria, constraints, affected components, decisions with the alternatives they beat, steps, a
  verification plan, and open questions. Changes no code. Fires on "design this", "plan the implementation",
  "compare approaches", "which design pattern fits", "how would you fix this bug?".
- **`implement`** — the code change itself: inspect, make the design decisions the task needs, implement,
  verify against the original request, and repair. Builds from a supplied design or fixes review findings
  when given them. Fires on "implement this", "fix this bug", "refactor X", "design and implement",
  "fix these review comments".

| You ask for | Skill |
| ----------- | ----- |
| A design, plan, or comparison of approaches, no code | `design-solution` |
| A feature, bug fix, or refactor | `implement` |
| Design **and** implementation | `implement` |
| A supplied design or plan built | `implement` |
| Review findings fixed | `implement` |
| A review of changes | `review-code`, in the `code-review` plugin |

## Verification and status

Verification lives inside `implement` and always runs; an independent review from `code-review` adds to it
and never replaces it. Acceptance criteria are fixed before coding, and the handoff reports one status:

- `implemented and verified` — every criterion has evidence that could have failed, and required checks pass.
- `implemented, verification incomplete` — a required check could not run or fails for a pre-existing reason;
  it is named with the reason.
- `implemented, checks failing` — a failure caused by the change remains after repair; the output is shown.
- `blocked` — essential information or access is missing.

## Notes

- **Side effects:** `implement` edits files in your repository and runs your project's own tests, linters,
  type checkers, and builds, which may write build output or reach the network themselves. It never installs
  a tool just to run a check, adds a project dependency only when your request requires one, does not commit
  or push unless asked, and asks before anything acting outside the working tree
  (database migrations, deploys, publishes). `design-solution` writes nothing except a design file you ask for.
- Neither skill depends on the other loading. A design from `design-solution` is an input to `implement`,
  which re-checks its assumptions against the code.
- No bundled scripts or reference files: every required rule is in each skill's `SKILL.md`.
