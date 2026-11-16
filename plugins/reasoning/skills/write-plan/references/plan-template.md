# Plan template — copy this file; it is not a plan

Copy to `<plan-folder>/plan-<n>-<topic>.md`, fill every section, and delete the guidance lines in italics.
A section that does not apply says "None" rather than disappearing, so the implementer knows it was
considered.

---

# Plan N — <title>

Status: draft | approved | implemented — *the user sets `approved` (the planner commits it); the coder sets `implemented` in its last commit; implementation starts only at `approved`*
Date: YYYY-MM-DD
Branch: `<branch name>` — *created from the latest default branch by the planning session; implement here*
Baseline: `<default branch>` at `<sha>` — *if the default branch has moved, rebase and re-check the Baseline section*
Target: `<path or component>` — *the plugin, module, script, or area this plan changes*

## Goal

*What must be true when this is done, and the problem it solves. One short paragraph.*

## Decisions

*Agreed choices, numbered, each with the option rejected and why. The implementer follows these as
written and asks instead of re-deciding.*

1. <decision> — rejected: <alternative>, because <reason>.

## Scope

In:

- *Files, components, and behavior this plan changes.*

Out:

- *Things a reader might expect but this plan deliberately leaves alone.*

## Baseline

*What already exists and is reused or changed, with file paths. A document describing code does not
prove it exists; check the file.*

| Existing | Keep, change, or remove |
| --- | --- |
| `path/to/file` | <what to do with it> |

## Tech stack and constraints

*The repository's documented constraints (its contributor and agent instructions, language floor, lint and
test gates). List only deviations from them and the reason, or write "Default".*

## Acceptance criteria

*Each criterion is checkable, and at least one covers a failure case. Give the exact commands.*

- [ ] <observable result> — checked by `<command>`
- [ ] <failure case handled> — checked by `<command or fixture>`
- [ ] The repository's required checks pass — checked by `<the repository's check commands>`

## Risks

| Risk | How it is handled |
| --- | --- |
| <what could go wrong> | <prevention or detection> |

## Open questions

*Anything not decided. The implementer asks the user about these and does not guess. "None" if empty.*
