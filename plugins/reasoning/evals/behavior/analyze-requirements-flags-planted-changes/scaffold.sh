#!/usr/bin/env bash
# GENERATED FILE -- DO NOT EDIT. Regenerate with: python3 tools/build_eval_scaffolds.py
# Recreates fixtures/17-requirement-change in the eval's empty workspace.
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
