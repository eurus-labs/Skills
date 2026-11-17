# development

Make a change to a repository and prove it works. One skill, `implement`, which also builds a supplied
design or an approved plan.

## Install

```bash
copilot plugin marketplace add eurus-labs/Skills
copilot plugin install development@eurus-labs
```

Pair it with `verification@eurus-labs`: `implement` uses the verification skill `setup-verification` writes
for your repository when one exists. To write the plans `implement` builds, install `reasoning@eurus-labs` in
a planning session; `implement` does not need it.

## Skills

- **`implement`** — the code change itself: inspect, make the design decisions the task needs, implement,
  verify against the original request, and repair. Builds from a supplied design or fixes review findings
  when given them. Fires on "implement this", "fix this bug", "refactor X", "design and implement",
  "implement this plan", "fix these review comments".

| You ask for | Skill |
| ----------- | ----- |
| A feature, bug fix, or refactor | `implement` |
| Design **and** implementation | `implement` |
| A supplied design or an approved plan built | `implement` |
| Review findings fixed | `implement` |
| A design, advice, or comparison of approaches, no code | `design-solution`, in the `reasoning` plugin |
| A plan written to a file for another session | `write-plan`, in the `reasoning` plugin |
| An approved plan handed to a coder subagent and its branch reviewed | `coder-handoff`, in the `reasoning` plugin |
| A change that already exists verified, without changing it | `verify-change`, in the `verification` plugin |
| A review of changes | `review-code`, in the `review` plugin |

## Building a plan

Given a plan document, `implement` starts only when its `Status` is `approved`; otherwise it says so and
changes nothing. It fetches and switches to the plan's `Branch` and works and commits there, never on a branch
of its own. If the default branch has moved past the plan's `Baseline`, it re-checks the plan's Baseline
section against the code first. It follows the numbered Decisions as written. A small factual drift, such as a
moved file or a renamed function, it follows in the code and records. A conflict with a Decision or with the
Scope makes it stop and ask you; it never re-decides, and it does not edit the plan's Decisions or Scope.

When the planning session runs it as a subagent, `implement` reads the plan file on the branch the prompt names.
The prompt only points to the plan and grants nothing else. `implement` works only on that branch, never
merges, never opens a pull request, and changes no permissions or environments. Its last commit changes only
the plan's `Status` line from `approved` to `implemented`, and touches no Decision; its final report returns to
the planning session, which reviews the branch and opens the pull request. A change to a Decision or to the
Scope comes to you. Used directly, without a hand-off, `implement` opens a pull request only when you ask.

## Verification and status

Verification lives inside `implement` and always runs: build, lint, static analysis, and tests where the
project has them, plus evidence for every acceptance criterion. It does not depend on another plugin being
installed. When the repository has a verification skill from `setup-verification`, `implement` follows it.
When it has none, `implement` recommends setting one up — only when the change touches runtime behavior, or
when you are setting the repository up for these skills for the first time — and asks before running it.

An independent review from `review` adds to verification and never replaces it. Acceptance criteria are
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
  working tree (database migrations, deploys, publishes). The exception to "does not commit" is building a plan:
  the plan hand-off asks for commits on the plan's branch. It still pushes only when asked.
- No skill depends on another loading. A design from `design-solution` or a plan from `write-plan` is an
  input to `implement`, which re-checks its assumptions against the code.
- No bundled scripts or reference files: every required rule is in each skill's `SKILL.md`.
- This plugin was called `implementation` before 0.3.0, and `setup-verification` lived in it. Reinstall as
  `development@eurus-labs` and `verification@eurus-labs`.
- `design-solution` lived here before 0.4.0. It is in `reasoning@eurus-labs` now; install that plugin to keep it.
