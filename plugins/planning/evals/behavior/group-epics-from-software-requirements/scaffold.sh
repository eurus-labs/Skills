#!/usr/bin/env bash
# GENERATED FILE -- DO NOT EDIT. Regenerate with: python3 tools/build_eval_scaffolds.py
# Recreates fixtures/18-final-analysis/with-software-requirements in the eval's empty workspace.
set -euo pipefail
mkdir -p 'requirements'
cat > 'requirements/dod.md' <<'EVAL_FIXTURE_EOF'
# Definition of Done

A requirement is done when it meets all of these.

1. It states one behavior that a test can observe from outside the system.
2. A time or speed target gives a number, its unit, and the size of the input it applies to.
3. It can be checked with a number or an example; "fast", "easy" and similar words are not criteria.
EVAL_FIXTURE_EOF
mkdir -p 'requirements'
cat > 'requirements/v1.md' <<'EVAL_FIXTURE_EOF'
# Report Export Requirements

## Formats

- The system exports a saved report as CSV.
- The system exports a saved report as PDF.

## Limits

- A user can export at most 50 reports in one request.
- An export request is rejected when the report has no rows.

## Access

- Only the owner of a report can export it.
- Every export is recorded in the audit log.
EVAL_FIXTURE_EOF
mkdir -p 'requirements'
cat > 'requirements/v2.rst' <<'EVAL_FIXTURE_EOF'
Report Export Requirements
==========================

Formats
-------

- The system exports a saved report as CSV.
- The system exports a saved report as PDF.

Limits
------

- A user can export at most 100 reports in one request.
- An export request is rejected when the report has no rows.

Access
------

- Only the owner of a report can export it; a request from anyone else is rejected with an error.
- A user can schedule an export to run every night.
- Exports of large reports should finish quickly.
EVAL_FIXTURE_EOF
mkdir -p 'requirements/export'
cat > 'requirements/export/analysis.md' <<'EVAL_FIXTURE_EOF'
# Requirement analysis — export

Status: final

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
| SYS-005 | superseded | out (replaced by SYS-007) | — | "Exports of large reports should finish quickly." `v2.rst:21` | not checked | gap: DOU-003 | no number; replaced by SYS-007 |
| SYS-006 | added | in | "Every export is recorded in the audit log." `v1.md:16` | "Every export is recorded in the audit log." `dou.md:46` | already met: `src/exporter.py:42` | met | the PO kept the requirement v2 dropped (DOU-004) |
| SYS-007 | added | in | — | "A report with up to 10,000 rows must export within 30 seconds." `dou.md:35` | new: `src/exporter.py:22-27` writes rows one at a time, with no time limit | met | replaces SYS-005 (DOU-003) |
| SYS-008 | unchanged | out (unchanged) | "The system exports a saved report as CSV." `v1.md:5` | "The system exports a saved report as CSV." `v2.rst:7` | already met: `src/exporter.py:9` | met | |

## Findings

- **SYS-003** — conflicting: v2 says a request from anyone but the owner is rejected, and `src/exporter.py:19` lets a teammate export. Settled by DOU-002.
- **SYS-004** — missing: the time zone of "every night" and what happens when a scheduled export fails are not stated. Settled by DOU-005.
- **SYS-005** — untestable, fails the DoD (`requirements/dod.md:6`): "should finish quickly" has no number, unit or input size. Settled by DOU-003.

## Assumptions

| Assumption | Owner | Risk if wrong |
| ---------- | ----- | ------------- |
| A nightly export covers the reports the user could export by hand. | PO | The scheduler is built on the wrong report set. |

## Revision history

- 2026-11-25 — first analysis of `v2.rst` against `v1.md`; DOU-001 to DOU-005 raised.
- 2026-11-26 — updated from the PO's answers: DOU-001 to DOU-005 closed; SYS-002 and SYS-005 superseded by SYS-006 and SYS-007.
EVAL_FIXTURE_EOF
mkdir -p 'requirements/export'
cat > 'requirements/export/dou.md' <<'EVAL_FIXTURE_EOF'
# DoU — export

Discussion of Understanding: the one file of points for the Product Owner (PO). It records what the PO said,
as given.

## DOU-001 — Limit per request

- Question: Is 100 the new limit for every user, or only for some roles?
- Concerns: SYS-001
- Blocks: yes
- Status: closed
- Raised: 2026-11-25
- PO answer (as given): "Every user. 50 was a mistake in the first version."
- Date: 2026-11-26
- Confirmed by: Lan (PO)

## DOU-002 — Who may export

- Question: v2 says only the owner can export, but the code lets teammates export each other's reports (`src/exporter.py:19`). Which one is right?
- Concerns: SYS-003
- Blocks: yes
- Status: closed
- Raised: 2026-11-25
- PO answer (as given): "Owner only. Teammates must ask the owner."
- Date: 2026-11-26
- Confirmed by: Lan (PO)

## DOU-003 — What "quickly" means

- Question: The DoD (`requirements/dod.md:6`) asks a speed target for a number, its unit and the input size. What does "finish quickly" mean for a large report?
- Concerns: SYS-005, SYS-007
- Blocks: yes
- Status: closed
- Raised: 2026-11-25
- PO answer (as given): "A report with up to 10,000 rows must export within 30 seconds."
- Date: 2026-11-26
- Confirmed by: Lan (PO)

## DOU-004 — Audit log

- Question: v2 drops "every export is recorded in the audit log". Is that on purpose?
- Concerns: SYS-002, SYS-006
- Blocks: yes
- Status: closed
- Raised: 2026-11-25
- PO answer (as given): "No, keep it. Compliance needs it."
- Date: 2026-11-26
- Confirmed by: Lan (PO)

## DOU-005 — Nightly export

- Question: Which time zone does "every night" use, and what happens when a scheduled export fails?
- Concerns: SYS-004
- Blocks: no
- Status: closed
- Raised: 2026-11-25
- PO answer (as given): "UTC. If it fails, tell the user and run it again the next night."
- Date: 2026-11-26
- Confirmed by: Lan (PO)
EVAL_FIXTURE_EOF
mkdir -p 'requirements/export'
cat > 'requirements/export/software-requirements.md' <<'EVAL_FIXTURE_EOF'
# Software requirements — export

## SWR-001 — Limit per request

- Statement: The software shall accept an export request for up to 100 reports and reject one for more than 100.
- Rationale: SYS-001 raises the limit from 50 to 100 for every user (DOU-001).
- Traces to: SYS-001
- Type: functional
- Verification criteria:
  - A request for 100 reports succeeds and returns 100 outputs.
  - A request for 101 reports is rejected with an error, and no output is written.
- Component: `src/exporter.py:8`, `src/exporter.py:33`
- Status: changes existing behavior

## SWR-002 — Owner-only export

- Statement: The software shall reject an export request for a report whose owner is not the requesting user.
- Rationale: SYS-003 limits export to the owner, teammates included (DOU-002).
- Traces to: SYS-003
- Type: functional
- Verification criteria:
  - A request from the owner of a report succeeds.
  - A request from a teammate of the owner is rejected with an error, and no output is written.
- Component: `src/exporter.py:17-19`
- Status: changes existing behavior

## SWR-003 — Nightly export

- Statement: The software shall run each export a user has scheduled once every night, in UTC.
- Rationale: SYS-004 asks for a nightly export; the time zone is UTC (DOU-005).
- Traces to: SYS-004
- Type: functional
- Verification criteria:
  - A scheduled export that is due runs once between 00:00 and 24:00 UTC, and its output is written.
  - A scheduled export that fails is reported to the user and runs again the next night.
- Component: new: no scheduler exists in `src/exporter.py`
- Status: new

## SWR-004 — Audit record

- Statement: The software shall record every export in the audit log.
- Rationale: SYS-006 keeps the audit requirement that v2 dropped (DOU-004).
- Traces to: SYS-006
- Type: functional
- Verification criteria:
  - After an export of 3 reports, the audit log holds 3 new entries, one per report.
  - An export that is rejected adds no entry for the report it rejected.
- Component: `src/exporter.py:42`
- Status: already met

## SWR-005 — Export time

- Statement: The software shall export a report of up to 10,000 rows within 30 seconds.
- Rationale: SYS-007 gives the number for "finish quickly" (DOU-003).
- Traces to: SYS-007
- Type: non-functional (performance)
- Verification criteria:
  - A report of 10,000 rows is exported in 30 seconds or less, measured from the request to the written output.
  - A report of 10,000 rows that takes 31 seconds fails the criterion.
- Component: `src/exporter.py:22-27`
- Status: new

## Traceability

| System requirement | Software requirements |
| ------------------ | --------------------- |
| SYS-001 | SWR-001 |
| SYS-003 | SWR-002 |
| SYS-004 | SWR-003 |
| SYS-006 | SWR-004 |
| SYS-007 | SWR-005 |

## Not derived to software

None.

## Gaps found

None.
EVAL_FIXTURE_EOF
mkdir -p 'src'
cat > 'src/exporter.py' <<'EVAL_FIXTURE_EOF'
"""Exports saved reports as files.

`export_reports` is the only entry point. It returns one output path per report.
"""

import os

MAX_REPORTS_PER_REQUEST = 50
SUPPORTED_FORMATS = ("csv", "pdf")
EXPORT_DIR = "/srv/exports"


class ExportError(Exception):
    pass


def _may_export(user, report):
    # Teammates may export each other's reports.
    return report.owner == user.name or report.team == user.team


def _write(report, fmt):
    path = os.path.join(EXPORT_DIR, "%s.%s" % (report.id, fmt))
    with open(path, "w") as out:
        for row in report.rows:
            out.write(",".join(str(cell) for cell in row) + "\n")
    return path


def export_reports(user, reports, fmt, audit_log):
    if fmt not in SUPPORTED_FORMATS:
        raise ExportError("unsupported format: %s" % fmt)
    if len(reports) > MAX_REPORTS_PER_REQUEST:
        raise ExportError("too many reports in one request")
    paths = []
    for report in reports:
        if not report.rows:
            raise ExportError("report %s has no rows" % report.id)
        if not _may_export(user, report):
            raise ExportError("not allowed to export report %s" % report.id)
        paths.append(_write(report, fmt))
        audit_log.write("exported %s" % report.id)
    return paths
EVAL_FIXTURE_EOF
