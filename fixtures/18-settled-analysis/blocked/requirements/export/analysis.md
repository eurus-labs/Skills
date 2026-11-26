# Requirement analysis — export

## Sources

| Role | Repository | Ref | Commit | Local path | Path in repository |
| ---- | ---------- | --- | ------ | ---------- | ------------------ |
| Current requirement | workspace | none | none (not a git repository) | `.` | `requirements/v2.rst` |
| Previous requirement | workspace | none | none (not a git repository) | `.` | `requirements/v1.md` |
| Code | workspace | none | none (not a git repository) | `.` | `src/` |

## Changes

| ID | Status | Scope | Previous (path:line) | Current (path:line) | Code impact | Note |
| -- | ------ | ----- | -------------------- | ------------------- | ----------- | ---- |
| R-001 | changed | in | "A user can export at most 50 reports in one request." `v1.md:10` | "A user can export at most 100 reports in one request." `v2.rst:13` | changes existing behavior: `src/exporter.py:8` | limit 50 to 100, for every user (dou-001) |
| R-002 | superseded | out (replaced by R-006) | "Every export is recorded in the audit log." `v1.md:16` | — | already met: `src/exporter.py:42` | dropped by v2, kept by the PO; replaced by R-006 |
| R-003 | changed | in | "Only the owner of a report can export it." `v1.md:15` | "Only the owner of a report can export it; a request from anyone else is rejected with an error." `v2.rst:19` | changes existing behavior: `src/exporter.py:17-19` | the code lets teammates export |
| R-004 | added | in | — | "A user can schedule an export to run every night." `v2.rst:20` | new: nothing in `src/exporter.py` schedules work | |
| R-005 | added | in | — | "Exports of large reports should finish quickly." `v2.rst:21` | not checked | no number; see OP-003 |
| R-006 | added | in | "Every export is recorded in the audit log." `v1.md:16` | "Every export is recorded in the audit log." `dou-001.md:38` | already met: `src/exporter.py:42` | the PO kept the requirement v2 dropped |
| R-008 | unchanged | out (unchanged) | "The system exports a saved report as CSV." `v1.md:5` | "The system exports a saved report as CSV." `v2.rst:7` | already met: `src/exporter.py:9` | |

## Findings

- **R-003** — conflicting: v2 says a request from anyone but the owner is rejected, and `src/exporter.py:19` lets a teammate export. Settled by OP-002.
- **R-004** — missing: the time zone of "every night" and what happens when a scheduled export fails are not stated. See OP-005.
- **R-005** — untestable: "should finish quickly" has no size or time. See OP-003.

## Open points

| ID | Question for the PO | Affects | Blocks | Status | Resolved by |
| -- | ------------------- | ------- | ------ | ------ | ----------- |
| OP-001 | Is 100 the new limit for every user, or only for some roles? | R-001 | yes | resolved | dou-001 |
| OP-002 | v2 says only the owner can export, but the code lets teammates export. Which one is right? | R-003 | yes | resolved | dou-001 |
| OP-003 | What does "finish quickly" mean for a large report? | R-005 | yes | open | — |
| OP-004 | Is dropping the audit log requirement on purpose? | R-002, R-006 | yes | resolved | dou-001 |
| OP-005 | Which time zone does "every night" use, and what happens when a scheduled export fails? | R-004 | no | open | — |

## Assumptions

| Assumption | Owner | Risk if wrong |
| ---------- | ----- | ------------- |
| A nightly export covers the reports the user could export by hand. | PO | The scheduler is built on the wrong report set. |

## Revision history

- 2026-11-26 — first analysis of `v2.rst` against `v1.md`.
- 2026-11-26 — updated from `dou-001`: OP-001, OP-002 and OP-004 resolved; R-002 superseded by R-006; OP-005 opened; OP-003 not discussed.
