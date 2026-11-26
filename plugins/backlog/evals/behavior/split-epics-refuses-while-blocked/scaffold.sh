#!/usr/bin/env bash
# GENERATED FILE -- DO NOT EDIT. Regenerate with: python3 tools/build_eval_scaffolds.py
# Recreates fixtures/18-settled-analysis/blocked in the eval's empty workspace.
set -euo pipefail
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
EVAL_FIXTURE_EOF
mkdir -p 'requirements/export'
cat > 'requirements/export/dou-001.md' <<'EVAL_FIXTURE_EOF'
# DoU 001 — export

Discussion of Understanding. It records what the PO said, as given.

- Date: 2026-11-26
- Participants: Lan (PO), Minh (analyst)
- Source: the analyst's notes of the call

## Points discussed

### OP-001

- Question: Is 100 the new limit for every user, or only for some roles?
- PO answer (as given): "Every user. 50 was a mistake in the first version."
- Decision: the limit is 100 reports per request for every user.
- Confirmed by: Lan
- Changes requirements: R-001

### OP-002

- Question: v2 says only the owner can export, but the code lets teammates export each other's reports. Which one is right?
- PO answer (as given): "Owner only. Teammates must ask the owner."
- Decision: a request from anyone but the owner is rejected, teammates included.
- Confirmed by: Lan
- Changes requirements: R-003

### OP-003

- Question: What does "finish quickly" mean for a large report?
- PO answer (as given): not given
- Decision: none
- Confirmed by: none
- Changes requirements: none

### OP-004

- Question: v2 drops "every export is recorded in the audit log". Is that on purpose?
- PO answer (as given): "No, keep it. Compliance needs it."
- Decision: the audit log requirement stays.
- Confirmed by: Lan
- Changes requirements: R-002, R-006

## New open points

- Which time zone does "every night" use, and what happens when a scheduled export fails? Affects R-004, blocks epics: no.
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
