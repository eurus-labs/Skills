# Plan template — copy this file; it is not a plan

Copy to `doc/plan-<n>-<topic>.md`, fill every section, and delete the guidance lines in italics. A section
that does not apply says "None" rather than disappearing, so the implementer knows it was considered.

---

# Plan N — <title>

Status: draft | approved | implemented — *the user sets `approved`; implementation starts only then*
Date: YYYY-MM-DD
Branch: `<type>/<area>-<outcome>` — *created from `origin/main` by the planning session; implement here*
Baseline: `origin/main` at `<sha>` — *if `main` has moved, rebase and re-check the Baseline section*
Target: `<plugin>/<skill>`, `tools/<script>.py`, or another named area

## Goal

*What must be true when this is done, and the problem it solves. One short paragraph.*

## Decisions

*Agreed choices, numbered, each with the option rejected and why. The implementer follows these as
written and asks instead of re-deciding (AGENTS.md, Start Each Task, step 2).*

1. <decision> — rejected: <alternative>, because <reason>.

## Scope

In:

- *Files, skills, scripts, and behavior this plan changes.*

Out:

- *Things a reader might expect but this plan deliberately leaves alone.*

## Baseline

*What already exists and is reused or changed, with file paths. A document describing a script does not
prove it exists; check the file.*

| Existing | Keep, change, or remove |
| --- | --- |
| `path/to/file` | <what to do with it> |

## Tech stack and constraints

*Default per AGENTS.md: Markdown skills and stdlib-only Python 3.9+, no new dependencies. List only
deviations and their reason, or write "Default".*

## Acceptance criteria

*Each criterion is checkable, and at least one covers a failure case. Give the exact commands.*

- [ ] <observable result> — checked by `<command>`
- [ ] <failure case handled> — checked by `<command or fixture>`
- [ ] `python3 tools/validate.py` passes and `for t in tools/test_*.py; do python3 "$t" || break; done` passes

## Risks

| Risk | How it is handled |
| --- | --- |
| <what could go wrong> | <prevention or detection> |

## Open questions

*Anything not decided. The implementer asks the user about these and does not guess. "None" if empty.*
