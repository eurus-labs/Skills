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
