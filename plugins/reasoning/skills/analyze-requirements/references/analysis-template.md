# Requirement analysis — <topic>

Written in the language of the requirement. Fill every section; a section with nothing to say says "None".
`scripts/requirements.py check` reads the tables below, so keep their column names and the `R-`, `OP-` IDs.

## Sources

One row per role. Repository is the URL, or `workspace`. Ref is the branch or tag. Commit is the exact sha
(`git rev-parse HEAD`). Local path is where the repository is on disk. Path in repository is relative to that
repository's root, and every `path:line` below is too. A previous version that is the same file at an earlier
revision gives that revision as its Commit. A role with no source says `none: first analysis` or
`code not checked`, with what was listed. In an unattended run all three roles are `workspace`, and the
question that would have been asked is an open point.

| Role | Repository | Ref | Commit | Local path | Path in repository |
| ---- | ---------- | --- | ------ | ---------- | ------------------ |
| Current requirement | workspace | `main` | `3f9c2ab…` | `.` | `requirements/v2.rst` |
| Previous requirement | workspace | `main` | `1d7e0c4…` | `.` | `requirements/v1.md` |
| Code | `https://example.org/team/export-service.git` | `main` | `9b41e6a…` | `../export-service` | `src/` |

## Changes

One row per requirement. Status is `added`, `removed`, `changed`, `unchanged`, `unchanged (wording)` or
`superseded`. Scope is `in` for a requirement that needs work (usually `added` and `changed`) or `out`, with
the reason after it. Code impact is `new`, `changes existing behavior`, `already met` or `not checked`, with
`path:line`. A row replaced by a DoU decision keeps its text, gets status `superseded`, and names the row that
replaces it in the Note column; the replacement is a new row.

| ID | Status | Scope | Previous (path:line) | Current (path:line) | Code impact | Note |
| -- | ------ | ----- | -------------------- | ------------------- | ----------- | ---- |
| R-001 | changed | in | "A user can export at most 50 reports in one request." `v1.md:10` | "A user can export at most 100 reports in one request." `v2.rst:13` | changes existing behavior: `src/exporter.py:8` | limit 50 to 100 |
| R-002 | removed | out (dropped by the new version) | "Every export is recorded in the audit log." `v1.md:16` | — | already met: `src/exporter.py:41` | |

## Findings

Per requirement, the problems that stop it being built or tested as written. A finding is `ambiguous`,
`missing`, `conflicting`, `untestable` or `non-functional gap`, and quotes the words it is about. A finding
that needs the PO's answer points at an open point.

- **R-001** — conflicting: the code rejects more than 50 reports (`src/exporter.py:8`). See OP-001.

## Open points

Questions for the PO. `Blocks` is `yes` when the epics cannot be split sensibly until it is answered, else
`no`. `Status` is `open` or `resolved`. `Resolved by` names the DoU file, for example `dou-001`, and is `—`
while the point is open.

| ID | Question for the PO | Affects | Blocks | Status | Resolved by |
| -- | ------------------- | ------- | ------ | ------ | ----------- |
| OP-001 | Is 100 the new limit for every user, or only for some roles? | R-001 | yes | open | — |

## Assumptions

Each assumption has an owner and the risk if it is wrong. An assumption is not a decision: it stays here until
a DoU confirms it.

| Assumption | Owner | Risk if wrong |
| ---------- | ----- | ------------- |
| The limit applies per request, not per day. | PO | The limit check is built in the wrong place. |

## Revision history

One line per update, newest last.

- 2026-11-25 — first analysis of `v2.rst` against `v1.md`.
