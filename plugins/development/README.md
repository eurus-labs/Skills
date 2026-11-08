# development

Design a change to a repository, or make it and prove it works. Two skills, each usable on its own: the
boundary between them is the deliverable you ask for, not whether design thinking happens.

## Install

```bash
copilot plugin marketplace add eurus-labs/Skills
copilot plugin install development@eurus-labs
```

Pair it with `verification@eurus-labs`: `implement` uses the verification skill `setup-verification` writes
for your repository when one exists.

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
| A change that already exists verified, without changing it | `verify-change`, in the `verification` plugin |
| A review of changes | `review-code`, in the `code-review` plugin |

## Verification and status

Verification lives inside `implement` and always runs: build, lint, static analysis, and tests where the
project has them, plus evidence for every acceptance criterion. It does not depend on another plugin being
installed. When the repository has a verification skill from `setup-verification`, `implement` follows it.
When it has none, `implement` recommends setting one up — only when the change touches runtime behavior, or
when you are setting the repository up for these skills for the first time — and asks before running it.

An independent review from `code-review` adds to verification and never replaces it. Acceptance criteria are
fixed before coding, and the handoff reports one status:

- `implemented and verified` — every criterion has evidence that could have failed, and required checks pass.
- `implemented, verification incomplete` — a required check could not run or fails for a pre-existing reason;
  it is named with the reason.
- `implemented, checks failing` — a failure caused by the change remains after repair; the output is shown.
- `blocked` — essential information or access is missing.

## Notes

- **Side effects:** `implement` edits files in your repository and runs your project's own tests, linters,
  type checkers, and builds, which may write build output or reach the network themselves. It installs
  nothing: when your request needs a new dependency it declares it in the manifest and gives you the install
  command to run. It does not commit or push unless asked, and asks before anything acting outside the
  working tree (database migrations, deploys, publishes). `design-solution` writes nothing except a design
  file you ask for.
- No skill depends on another loading. A design from `design-solution` is an input to `implement`, which
  re-checks its assumptions against the code.
- No bundled scripts or reference files: every required rule is in each skill's `SKILL.md`.
- This plugin was called `implementation` before 0.3.0, and `setup-verification` lived in it. Reinstall as
  `development@eurus-labs` and `verification@eurus-labs`.
