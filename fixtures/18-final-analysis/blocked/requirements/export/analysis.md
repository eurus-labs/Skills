# Requirement analysis — export

Status: draft

## Sources

| Role | Repository | Ref | Commit | Local path | Path in repository |
| ---- | ---------- | --- | ------ | ---------- | ------------------ |
| Current requirement | workspace | none | none (not a git repository) | `.` | `requirements/v2.rst` |
| Previous requirement | workspace | none | none (not a git repository) | `.` | `requirements/v1.md` |
| DoD | workspace | none | none (not a git repository) | `.` | `requirements/dod.md` |
| Code | workspace | none | none (not a git repository) | `.` | `src/` |

## System requirements

| ID | Status | Scope | Previous (path:line) | Current (path:line) | Code impact | DoD | Note |
| -- | ------ | ----- | -------------------- | ------------------- | ----------- | --- | ---- |
| SYS-001 | changed | in | "A user can export at most 50 reports in one request." `v1.md:10` | "A user can export at most 100 reports in one request." `v2.rst:13` | changes existing behavior: `src/exporter.py:8` | met | limit 50 to 100, for every user (DOU-001) |
| SYS-002 | superseded | out (replaced by SYS-006) | "Every export is recorded in the audit log." `v1.md:16` | — | already met: `src/exporter.py:42` | met | dropped by v2, kept by the PO (DOU-004); replaced by SYS-006 |
| SYS-003 | changed | in | "Only the owner of a report can export it." `v1.md:15` | "Only the owner of a report can export it; a request from anyone else is rejected with an error." `v2.rst:19` | changes existing behavior: `src/exporter.py:17-19` | met | the code lets teammates export; owner only (DOU-002) |
| SYS-004 | added | in | — | "A user can schedule an export to run every night." `v2.rst:20` | new: nothing in `src/exporter.py` schedules work | met | UTC, run again the next night on failure (DOU-005) |
| SYS-005 | added | in | — | "Exports of large reports should finish quickly." `v2.rst:21` | not checked | gap: DOU-003 | no number; see DOU-003 |
| SYS-006 | added | in | "Every export is recorded in the audit log." `v1.md:16` | "Every export is recorded in the audit log." `dou.md:46` | already met: `src/exporter.py:42` | met | the PO kept the requirement v2 dropped (DOU-004) |
| SYS-008 | unchanged | out (unchanged) | "The system exports a saved report as CSV." `v1.md:5` | "The system exports a saved report as CSV." `v2.rst:7` | already met: `src/exporter.py:9` | met | |

## Findings

- **SYS-003** — conflicting: v2 says a request from anyone but the owner is rejected, and `src/exporter.py:19` lets a teammate export. Settled by DOU-002.
- **SYS-004** — missing: the time zone of "every night" and what happens when a scheduled export fails are not stated. Settled by DOU-005.
- **SYS-005** — untestable, fails the DoD (`requirements/dod.md:6`): "should finish quickly" has no number, unit or input size. See DOU-003.

## Assumptions

| Assumption | Owner | Risk if wrong |
| ---------- | ----- | ------------- |
| A nightly export covers the reports the user could export by hand. | PO | The scheduler is built on the wrong report set. |

## Revision history

- 2026-11-25 — first analysis of `v2.rst` against `v1.md`; DOU-001 to DOU-005 raised.
- 2026-11-26 — updated from the PO's answers: DOU-001, DOU-002, DOU-004 and DOU-005 closed; DOU-003 not discussed; SYS-002 superseded by SYS-006.
