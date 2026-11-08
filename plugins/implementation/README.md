# implementation

Design a change to a repository, make it and prove it works, or teach agents how to prove changes in your
specific app. Three skills, each usable on its own: the boundary between them is the deliverable you ask for.

## Install

```bash
copilot plugin marketplace add eurus-labs/Skills
copilot plugin install implementation@CopilotBox
```

## Start here

Run `setup-verification` once per repository, before the first `implement`:

> *"Set up verification for this repo"*

It writes a `verify-<app>` skill into the repository — the feature map, a fresh-build check, change-to-area
mapping, and evidence capture — so every later `implement` verifies against the running app and against
confirmed behavior, not only against tests that may mirror the code. If a repository has no such skill,
`implement` recommends this step first — only when the change touches runtime behavior, or when you are
setting the repository up for these skills for the first time — and asks before running it. A docs-only,
test-only, or formatting-only change goes ahead without the question; a refactor of running code does not.
When you decline, or no one can be asked, it continues with the project's own tests and says so in its
report.

## Skills

- **`design-solution`** — an implementation-ready design and plan, grounded in the current code: goal, scope,
  acceptance criteria, constraints, affected components, decisions with the alternatives they beat, steps, a
  verification plan, and open questions. Changes no code. Fires on "design this", "plan the implementation",
  "compare approaches", "which design pattern fits", "how would you fix this bug?".
- **`implement`** — the code change itself: inspect, make the design decisions the task needs, implement,
  verify against the original request, and repair. Builds from a supplied design or fixes review findings
  when given them. Fires on "implement this", "fix this bug", "refactor X", "design and implement",
  "fix these review comments". Uses the repository's own verification skill, and recommends
  `setup-verification` first when there is none.
- **`setup-verification`** — writes a project-local `verify-<app>` skill into your repository with five
  capabilities: a feature map (one file per area, with the source paths it owns); a small CLI
  (`doctor`, `start`, `stop`) that proves the build is fresh; `affected <base>`, which maps a diff to the
  feature areas it touches; `capture` and `report` for evidence; and a review of that evidence against the
  goal, one verdict per criterion. The CLI wraps the commands and tools your repository already has. Asks you
  for the business rules the code cannot settle, then trial-runs every command. Fires on "set up verification
  for this repo", "make a verify skill", "create a feature map".

| You ask for | Skill |
| ----------- | ----- |
| A design, plan, or comparison of approaches, no code | `design-solution` |
| A feature, bug fix, or refactor | `implement` |
| Design **and** implementation | `implement` |
| A supplied design or plan built | `implement` |
| Review findings fixed | `implement` |
| A repository's own verification skill and feature map | `setup-verification` |
| A review of changes | `review-code`, in the `code-review` plugin |

## Verification and status

Verification lives inside `implement` and always runs; an independent review from `code-review` adds to it
and never replaces it. Acceptance criteria are fixed before coding, and the handoff reports one status:

- `implemented and verified` — every criterion has evidence that could have failed, and required checks pass.
- `implemented, verification incomplete` — a required check could not run or fails for a pre-existing reason;
  it is named with the reason.
- `implemented, checks failing` — a failure caused by the change remains after repair; the output is shown.
- `blocked` — essential information or access is missing.

## Observed is not correct

Code and a running app show what the system does, not what it should do. Every expected behavior in a
generated feature map carries its source — `[confirmed: spec …]`, `[confirmed: user, <date>]`,
`[confirmed: test …]`, or `[observed]` — and only confirmed entries are pass criteria. Each behavior is
checked against its target — what the function is for, from its spec, docstring, docs, name, and callers.
Code or a passing test that contradicts the target is recorded as a suspected bug, with both sides cited;
a test written to match the bug counts as evidence for it, not as confirmation. `implement` keeps the map
current when a change alters an area it describes, and never promotes `[observed]` to confirmed because the
code now does it.

## Notes

- **Side effects:** `implement` edits files in your repository and runs your project's own tests, linters,
  type checkers, and builds, which may write build output or reach the network themselves. It installs
  nothing: when your request needs a new dependency it declares it in the manifest and gives you the install
  command to run. It does not commit or push unless asked, and asks before anything acting outside the working tree
  (database migrations, deploys, publishes). `design-solution` writes nothing except a design file you ask for.
  `setup-verification` writes only the verification skill folder (including an executable `scripts/verify`),
  runs your project's own build, start, and test commands during its survey and trial run, installs nothing,
  and proposes — never makes — an `AGENTS.md` pointer to the new skill and a `.gitignore` entry for the
  `.verify/` evidence directory.
- No skill depends on another loading. A design from `design-solution` is an input to `implement`,
  which re-checks its assumptions against the code.
- No bundled scripts or reference files: every required rule is in each skill's `SKILL.md`.
