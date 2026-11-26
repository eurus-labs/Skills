# Requirement analysis — <topic>

Status: final

Written in the language of the requirement. Fill every section; a section with nothing to say says "None".
`scripts/requirements.py check` reads the `Status:` line and the System requirements table, so keep them and
the `SYS-` IDs. `Status:` is `draft` while any blocking point in `dou.md` is open, and `final` only when none is.
The points for the PO are in `dou.md`, never here: refer to them by `DOU-` ID.

## Sources

One row per role. Repository is the URL, or `workspace`. Ref is the branch or tag. Commit is the exact sha
(`git rev-parse HEAD`). Local path is where the repository is on disk. Path in repository is relative to that
repository's root, and every `path:line` below is too. A previous version that is the same file at an earlier
revision gives that revision as its Commit. A role with no source says `none: first analysis`, `none: DoD not
given` or `code not checked`, with what was listed. In an unattended run every role is `workspace`, and the
question that would have been asked is a `DOU-` point.

| Role | Repository | Ref | Commit | Local path | Path in repository |
| ---- | ---------- | --- | ------ | ---------- | ------------------ |
| Current requirement | workspace | `main` | `3f9c2ab…` | `.` | `requirements/v2.rst` |
| Previous requirement | workspace | `main` | `1d7e0c4…` | `.` | `requirements/v1.md` |
| DoD | workspace | `main` | `3f9c2ab…` | `.` | `requirements/dod.md` |
| Code | `https://example.org/team/export-service.git` | `main` | `9b41e6a…` | `../export-service` | `src/` |

## System requirements

One row per requirement. Each is a system requirement: what the product must do, as the requirement states it.
Status is `added`, `removed`, `changed`, `unchanged`, `unchanged (wording)` or `superseded`. Scope is `in` for
a requirement that needs work (usually `added` and `changed`) or `out`, with the reason after it. Code impact
is `new`, `changes existing behavior`, `already met` or `not checked`, with `path:line`; `not software` for a
manual or process step. DoD is `met`, `gap: DOU-NNN` (the DoD criterion it fails, and the point that asks the
PO), or `DoD not given: DOU-NNN`. A row replaced by a PO decision keeps its text, gets status `superseded`,
and names the row that replaces it in the Note column; the replacement is a new row.

| ID | Status | Scope | Previous (path:line) | Current (path:line) | Code impact | DoD | Note |
| -- | ------ | ----- | -------------------- | ------------------- | ----------- | --- | ---- |
| SYS-001 | changed | in | "A user can export at most 50 reports in one request." `v1.md:10` | "A user can export at most 100 reports in one request." `v2.rst:13` | changes existing behavior: `src/exporter.py:8` | met | limit 50 to 100, for every user (DOU-001) |
| SYS-002 | added | in | — | "A user can schedule an export to run every night." `v2.rst:20` | new: nothing in `src/exporter.py` schedules work | gap: DOU-002 | time zone and failure handling unknown |
| SYS-003 | removed | out (dropped by the new version) | "Every export is recorded in the audit log." `v1.md:16` | — | already met: `src/exporter.py:41` | met | |
| SYS-004 | added | in | — | "The compliance officer reviews the export log every month." `v2.rst:22` | not software | met | a manual step |

## Findings

Per requirement, the problems that stop it being built or tested as written. A finding is `ambiguous`,
`missing`, `conflicting`, `untestable`, `non-functional gap` or `fails the DoD`, and quotes the words it is
about. A finding that needs the PO's answer points at a `DOU-` point.

- **SYS-001** — conflicting: the code rejects more than 50 reports (`src/exporter.py:8`). Settled by DOU-001.
- **SYS-002** — missing: the time zone of "every night" and what happens when a scheduled export fails are
  not stated. See DOU-002.

## Assumptions

Each assumption has an owner and the risk if it is wrong. An assumption is not a decision: it stays here until
a closed `DOU-` point confirms it.

| Assumption | Owner | Risk if wrong |
| ---------- | ----- | ------------- |
| A nightly export covers the reports the user could export by hand. | PO | The scheduler is built on the wrong report set. |

## Revision history

One line per update, newest last, naming the points it applied.

- 2026-11-25 — first analysis of `v2.rst` against `v1.md`; DOU-001 and DOU-002 raised.
- 2026-11-26 — updated from the PO's answers: DOU-001 closed, applied to SYS-001.
