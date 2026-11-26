#!/usr/bin/env python3
"""Behavioural tests for shared/scripts/requirements/requirements.py, the source of the copies in
the analyze-requirements and split-epics skills.

`diff` must find every added, removed, changed and unchanged unit in .md, .rst and .txt files with
correct line ranges, and `check` must fail, naming the line, for each rule of the skill's Decision 8
and pass on a consistent folder. Stdlib only, no test framework -- see tools/test_check_env.py for why.

    python3 tools/test_requirements_script.py
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO, "shared", "scripts", "requirements", "requirements.py")
spec = importlib.util.spec_from_file_location("requirements_script", SCRIPT)
req = importlib.util.module_from_spec(spec)
spec.loader.exec_module(req)

FAILURES = []


def check(name, condition, detail=""):
    if condition:
        print("ok   %s" % name)
    else:
        print("FAIL %s %s" % (name, detail))
        FAILURES.append(name)


def write(root, name, text):
    path = os.path.join(root, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


def by_status(result, status):
    return [u for u in result["units"] if u["status"] == status]


def texts(units, side):
    return [u[side]["text"] for u in units]


V1_MD = """# Export

## Limits

- A user can export at most 50 reports in one request.
- A report with no rows is rejected.

## Access

1. Only the owner can export a report.
2. Every export is logged.
"""

V2_RST = """Export
======

Limits
------

- A user can export at most 100 reports in one request.
- A report with no rows is rejected.

Access
------

1. Only the owner can export a report.
#. Exports run every night.
"""


def test_diff_markdown_and_rst(tmp):
    prev = write(tmp, "v1.md", V1_MD)
    cur = write(tmp, "v2.rst", V2_RST)
    result = req.diff(prev, cur)
    check("diff reads md and rst", (result["previous"]["format"], result["current"]["format"]) == ("md", "rst"))
    s = result["summary"]
    check("diff counts the four statuses", (s["added"], s["removed"], s["changed"]) == (1, 1, 1), str(s))
    changed = by_status(result, "changed")
    check("a changed number inside an otherwise identical item is changed",
          len(changed) == 1 and "50" in changed[0]["previous"]["text"] and "100" in changed[0]["current"]["text"],
          str(changed))
    check("changed carries both line ranges",
          changed[0]["previous"]["lines"] == [5, 5] and changed[0]["current"]["lines"] == [7, 7],
          str([changed[0]["previous"]["lines"], changed[0]["current"]["lines"]]))
    added = by_status(result, "added")
    check("an added item is added, with its rst line range",
          texts(added, "current") == ["Exports run every night."] and added[0]["current"]["lines"] == [14, 14],
          str(added))
    removed = by_status(result, "removed")
    check("a removed item is removed, with its md line range",
          texts(removed, "previous") == ["Every export is logged."] and removed[0]["previous"]["lines"] == [11, 11],
          str(removed))
    unchanged = by_status(result, "unchanged")
    check("the same text across md and rst, with markers and underlines, is unchanged",
          s["unchanged"] == len(unchanged) == 5, str(s))
    check("a unit carries its section", changed[0]["section"] == "Export > Limits", changed[0]["section"])
    check("a removed unit sits after its matched neighbour, not at the end",
          result["units"].index(removed[0]) < result["units"].index(added[0]))


def test_diff_changes_only(tmp):
    prev = write(tmp, "v1.md", V1_MD)
    cur = write(tmp, "v2.rst", V2_RST)
    result = req.diff(prev, cur, changes_only=True)
    check("--changes-only drops unchanged units but keeps the count",
          not by_status(result, "unchanged") and result["summary"]["unchanged"] == 5)


def test_diff_text(tmp):
    prev = write(tmp, "a.txt", "Overview of the export.\n\n"
                               "1. Reports are exported as CSV.\n"
                               "   Large reports are split.\n"
                               "2. Reports are exported as PDF.\n\n"
                               "The limit is 10 MB.\n")
    cur = write(tmp, "b.txt", "Overview of the export.\n\n"
                              "1. Reports are exported as CSV.\n"
                              "   Large reports are split.\n"
                              "2. Reports are exported as XLSX.\n\n"
                              "The limit is 25 MB.\n")
    result = req.diff(prev, cur)
    kinds = [u["kind"] for u in result["units"]]
    check("txt splits paragraphs and numbered items", sorted(set(kinds)) == ["item", "paragraph"], str(kinds))
    first = [u for u in result["units"] if u["current"]["text"].startswith("Reports are exported as CSV")][0]
    check("a continuation line belongs to its item, with the range covering both lines",
          first["current"]["lines"] == [3, 4] and first["status"] == "unchanged", str(first["current"]))
    check("txt changes are detected", result["summary"]["changed"] == 2, str(result["summary"]))


def test_diff_first_analysis_and_moves(tmp):
    prev = write(tmp, "empty.md", "")
    cur = write(tmp, "v.md", "# T\n\n- One thing.\n- Another thing.\n")
    result = req.diff(prev, cur)
    check("with an empty previous version every requirement is added",
          result["summary"]["added"] == 3 and result["summary"]["changed"] == 0, str(result["summary"]))
    prev = write(tmp, "m1.md", "# A\n\n- Keep this exactly.\n\n# B\n\n- Other.\n")
    cur = write(tmp, "m2.md", "# A\n\n- Other.\n\n# B\n\n- Keep this exactly.\n")
    moved = by_status(req.diff(prev, cur), "moved")
    check("a unit moved to another section has the status moved",
          len(moved) == 2, str(moved))
    check("a moved unit names both sections and both line ranges",
          moved[0]["previous_section"] == "B" and moved[0]["section"] == "A"
          and moved[0]["previous"]["lines"] == [7, 7] and moved[0]["current"]["lines"] == [3, 3], str(moved[0]))
    check("the summary counts moved units", req.diff(prev, cur)["summary"]["moved"] == 2)


def test_diff_move_survives_changes_only(tmp):
    prev = write(tmp, "a.md", "# Doc\n\n## Administrators\n\n- Can export reports.\n\n"
                              "## All users\n\n- Can view reports.\n")
    cur = write(tmp, "b.md", "# Doc\n\n## Administrators\n\n## All users\n\n- Can view reports.\n"
                             "- Can export reports.\n- Can print reports.\n")
    result = req.diff(prev, cur, changes_only=True)
    check("a section move is kept in --changes-only output, next to the unrelated added line",
          [u["status"] for u in result["units"]] == ["moved", "added"]
          or sorted(u["status"] for u in result["units"]) == ["added", "moved"], str(result["units"]))
    moved = by_status(result, "moved")
    check("the move names the old and new section",
          moved and moved[0]["previous_section"] == "Doc > Administrators"
          and moved[0]["section"] == "Doc > All users", str(moved))
    check("the move counts in the summary", result["summary"]["moved"] == 1 and result["summary"]["unchanged"] > 0,
          str(result["summary"]))


def test_diff_literal_changes_survive_normalization(tmp):
    prev = write(tmp, "p.md", "- Files match `report*.csv`.\n- Status must be READY.\n"
                              "- Keep the trailing dot.\n- Use a * b and snake_case_name.\n")
    cur = write(tmp, "c.md", "- Files match `report.csv`.\n- Status must be ready.\n"
                             "- Keep the trailing dot\n- Use a * b and snake_case_name.\n")
    result = req.diff(prev, cur)
    changed = [u["current"]["text"] for u in by_status(result, "changed")]
    check("a changed glob inside inline code is changed", "Files match `report.csv`." in changed, str(changed))
    check("a change of case is changed", "Status must be ready." in changed, str(changed))
    check("a dropped trailing period is changed", "Keep the trailing dot" in changed, str(changed))
    check("a stray * and underscores inside a word are kept, so that unit is unchanged",
          result["summary"]["unchanged"] == 1 and result["summary"]["changed"] == 3, str(result["summary"]))
    only = req.diff(prev, cur, changes_only=True)
    check("--changes-only returns the literal changes", len(only["units"]) == 3, str(only["units"]))


def test_diff_formatting_only_is_unchanged(tmp):
    prev = write(tmp, "f.md", "# Export\n\n- The **system** exports `report*.csv`  and _only_ owners.\n"
                              "- Exports  run\n  every night.\n")
    cur = write(tmp, "f.rst", "Export\n======\n\n- The **system** exports ``report*.csv`` and *only* owners.\n"
                              "- Exports run every night.\n")
    result = req.diff(prev, cur)
    check("emphasis, code delimiters, whitespace and heading style differences are unchanged",
          result["summary"] == {"added": 0, "removed": 0, "changed": 0, "moved": 0, "unchanged": 3},
          str(result["summary"]))


def test_diff_fixture_17_reports_five_changes():
    base = os.path.join(REPO, "fixtures", "17-requirement-change", "requirements")
    result = req.diff(os.path.join(base, "v1.md"), os.path.join(base, "v2.rst"), changes_only=True)
    check("fixture 17 reports exactly its five planted changes",
          (result["summary"]["added"], result["summary"]["removed"], result["summary"]["changed"],
           result["summary"]["moved"]) == (2, 1, 2, 0) and len(result["units"]) == 5, str(result["summary"]))


def test_diff_ids_and_failures(tmp):
    prev = write(tmp, "p.md", "- REQ-1 The service answers within 2 seconds.\n")
    cur = write(tmp, "c.md", "- REQ-1 Respond to every call.\n")
    result = req.diff(prev, cur)
    check("the same explicit ID pairs two very different texts as changed",
          result["summary"]["changed"] == 1 and result["summary"]["added"] == 0, str(result["summary"]))
    unrelated = req.diff(write(tmp, "x.md", "- Alpha goes first.\n"), write(tmp, "y.md", "- Zebra crossing paint.\n"))
    check("unrelated items are removed and added, not paired",
          unrelated["summary"]["removed"] == 1 and unrelated["summary"]["added"] == 1)
    for bad, name in ((write(tmp, "r.docx", "x"), "an unsupported extension"),
                      (os.path.join(tmp, "missing.md"), "a missing file")):
        try:
            req.diff(bad, cur)
            check("diff fails on %s" % name, False)
        except req.UsageError:
            check("diff fails on %s" % name, True)
    proc = subprocess.run([sys.executable, SCRIPT, "diff", os.path.join(tmp, "p.md"), os.path.join(tmp, "c.md")],
                          capture_output=True, text=True)
    check("the CLI prints one JSON object and exits 0",
          proc.returncode == 0 and json.loads(proc.stdout)["summary"]["changed"] == 1, proc.stderr)
    proc = subprocess.run([sys.executable, SCRIPT, "diff", os.path.join(tmp, "r.docx"), os.path.join(tmp, "c.md")],
                          capture_output=True, text=True)
    check("the CLI exits 2 on an unsupported format, with the reason on stderr",
          proc.returncode == 2 and "unsupported format" in proc.stderr and not proc.stdout, proc.stderr)


ANALYSIS = """# Requirement analysis

## Changes

| ID | Status | Scope | Previous | Current | Code impact | Note |
| -- | ------ | ----- | -------- | ------- | ----------- | ---- |
| R-001 | changed | in | a | b | new | |
| R-002 | added | in | - | c | new | |
| R-003 | removed | out (dropped) | d | - | already met | |

## Open points

| ID | Question | Affects | Blocks | Status | Resolved by |
| -- | -------- | ------- | ------ | ------ | ----------- |
| OP-001 | Which limit? | R-001 | yes | resolved | dou-001 |
| OP-002 | Who owns it? | R-002 | no | open | - |
"""

EPICS = """# Epics - export

## E-01 - Limits

- Goal: raise the limit
- Covers: R-001, R-002
- Depends on open points: none

## Not in any epic

- R-003 - removed

## Traceability

| Requirement | Epic |
| ----------- | ---- |
| R-001 | E-01 |
"""

DOU = """# DoU 001

### OP-001

- PO answer (as given): "100"
- Changes requirements: R-001
"""


def folder(tmp, name, analysis=ANALYSIS, epics=EPICS, dou=DOU):
    root = os.path.join(tmp, name)
    write(root, "analysis.md", analysis)
    if epics is not None:
        write(root, "epics.md", epics)
    if dou is not None:
        write(root, "dou-001.md", dou)
    return root


def problems(root):
    return req.check(root)[0]


def has(found, name, fragment):
    return [p for p in found if p[0] == name and fragment in p[2]]


def test_check(tmp):
    ok = folder(tmp, "ok")
    check("check passes on a consistent folder", problems(ok) == [], str(problems(ok)))
    proc = subprocess.run([sys.executable, SCRIPT, "check", ok], capture_output=True, text=True)
    check("the CLI exits 0 and prints OK for a consistent folder",
          proc.returncode == 0 and proc.stdout.startswith("OK"), proc.stdout)
    only = folder(tmp, "only-analysis", epics=None, dou=None,
                  analysis=ANALYSIS.replace("resolved | dou-001", "open | -"))
    check("a folder with no epics.md and no DoU passes", problems(only) == [], str(problems(only)))

    dup = folder(tmp, "dup", analysis=ANALYSIS.replace("| R-002 | added", "| R-001 | added"))
    found = has(problems(dup), "analysis.md", "duplicate ID R-001")
    check("a duplicated ID fails, naming the line", len(found) == 1 and found[0][1] == 8, str(problems(dup)))
    dup_op = folder(tmp, "dup-op", analysis=ANALYSIS.replace("| OP-002 |", "| OP-001 |"))
    check("a duplicated open point ID fails", has(problems(dup_op), "analysis.md", "duplicate ID OP-001"))
    dup_epic = folder(tmp, "dup-epic", epics=EPICS + "\n## E-01 - Again\n\n- Covers: R-003\n")
    check("a duplicated epic ID fails", has(problems(dup_epic), "epics.md", "duplicate ID E-01"))

    unknown = folder(tmp, "unknown", epics=EPICS.replace("R-001, R-002", "R-001, R-002, R-009"))
    found = has(problems(unknown), "epics.md", "unknown ID R-009")
    check("an unknown R- ID in an epic fails, naming the line", len(found) == 1 and found[0][1] == 6,
          str(problems(unknown)))
    unknown_dou = folder(tmp, "unknown-dou", dou=DOU + "- Raises: OP-007\n")
    check("an unknown OP- ID in a DoU fails", has(problems(unknown_dou), "dou-001.md", "unknown ID OP-007"))
    unknown_an = folder(tmp, "unknown-an", analysis=ANALYSIS.replace("| R-001 | yes", "| R-044 | yes"))
    check("an unknown ID in the analysis itself fails", has(problems(unknown_an), "analysis.md", "unknown ID R-044"))

    no_dou = folder(tmp, "no-dou", analysis=ANALYSIS.replace("resolved | dou-001", "resolved | -"))
    found = has(problems(no_dou), "analysis.md", "OP-001 is resolved but names no DoU")
    check("a resolved open point with no DoU fails, naming the line", len(found) == 1 and found[0][1] == 15,
          str(problems(no_dou)))
    missing_dou = folder(tmp, "missing-dou", analysis=ANALYSIS.replace("dou-001", "dou-004"))
    check("a resolved open point naming a DoU that does not exist fails",
          has(problems(missing_dou), "analysis.md", "dou-004, which does not exist"))

    uncovered = folder(tmp, "uncovered", epics=EPICS.replace("R-001, R-002", "R-001"))
    found = has(problems(uncovered), "analysis.md", "R-002 is in no epic")
    check("an in-scope requirement in no epic fails, naming the line", len(found) == 1 and found[0][1] == 8,
          str(problems(uncovered)))
    listed = folder(tmp, "listed", epics=EPICS.replace("R-001, R-002", "R-001").replace(
        "- R-003 - removed", "- R-002 - waits for the PO\n- R-003 - removed"))
    check("a requirement in the 'Not in any epic' list passes", problems(listed) == [], str(problems(listed)))
    twice = folder(tmp, "twice", epics=EPICS + "\n## E-02 - More\n\n- Covers: R-002\n")
    check("a requirement in two epics fails", has(problems(twice), "epics.md", "R-002 is in both E-01 and E-02"))

    blocking = ANALYSIS.replace("| OP-002 | Who owns it? | R-002 | no |", "| OP-002 | Who owns it? | R-002 | yes |")
    final = folder(tmp, "blocked", analysis=blocking)
    found = has(problems(final), "epics.md", "not marked Provisional")
    check("non-provisional epics with an open blocking point fail, naming the point and both lines",
          len(found) == 1 and found[0][1] == 1 and "OP-002" in found[0][2] and "analysis.md:16" in found[0][2],
          str(problems(final)))
    prov = folder(tmp, "provisional", analysis=blocking, epics=EPICS.replace("# Epics - export", "# Epics - export - Provisional"))
    check("provisional epics with an open blocking point pass", problems(prov) == [], str(problems(prov)))
    resolved = folder(tmp, "unblocked", analysis=blocking.replace("yes | open | -", "yes | resolved | dou-001"))
    check("a resolved blocking point does not block epics", problems(resolved) == [], str(problems(resolved)))

    bad_status = folder(tmp, "bad-status", analysis=ANALYSIS.replace("no | open", "no | pending"))
    check("an open point with an unknown status fails", has(problems(bad_status), "analysis.md", "status 'pending'"))
    bad_blocks = folder(tmp, "bad-blocks", analysis=ANALYSIS.replace("| no | open", "| maybe | open"))
    check("an open point with an unknown Blocks value fails", has(problems(bad_blocks), "analysis.md", "Blocks 'maybe'"))

    quoted = ANALYSIS.replace("| R-001 | changed | in | a | b |",
                              '| R-001 | changed | in | "R-1042: Reports must be encrypted." | "OP-77 is old; R-1042 stays." |')
    qdir = folder(tmp, "quoted", analysis=quoted,
                  dou=DOU + '- PO answer (as given): "R-1042 is dropped, see OP-77."\n',
                  epics=EPICS.replace("- Goal: raise the limit", '- Goal: keep "R-1042: Reports must be encrypted."'))
    check("IDs quoted from the source, in a table cell, a DoU line or an epic line, are not references",
          problems(qdir) == [], str(problems(qdir)))
    bare = folder(tmp, "bare-ref", analysis=quoted.replace("| R-001 | yes | resolved", "| R-1042 | yes | resolved"))
    check("an unknown ID in an Affects cell still fails when the quote cells hold IDs",
          has(problems(bare), "analysis.md", "unknown ID R-1042"), str(problems(bare)))
    bare_epic = folder(tmp, "bare-epic", epics=EPICS.replace("- Goal: raise the limit",
                                                             '- Goal: "R-1042 quoted" and R-2000'))
    check("an unquoted unknown ID next to a quote still fails",
          [p[2] for p in problems(bare_epic)] == ["unknown ID R-2000"], str(problems(bare_epic)))
    note = folder(tmp, "note", analysis=ANALYSIS.replace("| new | |\n| R-002", "| new | superseded by R-099 |\n| R-002"))
    check("an unknown ID in the Note column of a requirement row still fails",
          has(problems(note), "analysis.md", "unknown ID R-099"), str(problems(note)))
    trace = folder(tmp, "trace", epics=EPICS.replace("| R-001 | E-01 |", "| R-001 | E-01 |\n| R-050 | E-01 |"))
    check("an unknown ID in a traceability row still fails",
          has(problems(trace), "epics.md", "unknown ID R-050"), str(problems(trace)))

    proc = subprocess.run([sys.executable, SCRIPT, "check", os.path.join(tmp, "uncovered")],
                          capture_output=True, text=True)
    check("the CLI exits 1 and prints FAIL file:line: message",
          proc.returncode == 1 and "FAIL analysis.md:8:" in proc.stdout, proc.stdout)
    empty = os.path.join(tmp, "empty-folder")
    os.makedirs(empty)
    proc = subprocess.run([sys.executable, SCRIPT, "check", empty], capture_output=True, text=True)
    check("the CLI exits 2 when analysis.md is missing", proc.returncode == 2 and "analysis.md" in proc.stderr,
          proc.stderr)
    proc = subprocess.run([sys.executable, SCRIPT, "frobnicate"], capture_output=True, text=True)
    check("the CLI exits 2 on an unknown subcommand", proc.returncode == 2 and "usage" in proc.stderr)


def test_template_is_checkable():
    """The shipped templates, filled as-is, must follow the format `check` reads."""
    refs = os.path.join(REPO, "plugins", "reasoning", "skills", "analyze-requirements", "references")
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(refs, "analysis-template.md"), encoding="utf-8") as fh:
            analysis = fh.read()
        with open(os.path.join(refs, "epics-template.md"), encoding="utf-8") as fh:
            epics = fh.read()
        write(tmp, "analysis.md", analysis)
        found = req.check(tmp)[0]
        check("the analysis template parses and passes on its own", found == [], str(found))
        write(tmp, "epics.md", epics)
        found = [p for p in req.check(tmp)[0] if "unknown ID" not in p[2]]
        check("the epics template is read: its blocking point and uncovered requirements are reported",
              any("not marked Provisional" in p[2] for p in found), str(found))


def main():
    with tempfile.TemporaryDirectory() as tmp:
        for test in (test_diff_markdown_and_rst, test_diff_changes_only, test_diff_text,
                     test_diff_first_analysis_and_moves, test_diff_move_survives_changes_only,
                     test_diff_literal_changes_survive_normalization, test_diff_formatting_only_is_unchanged,
                     test_diff_ids_and_failures, test_check):
            sub = os.path.join(tmp, test.__name__)
            os.makedirs(sub)
            test(sub)
    test_diff_fixture_17_reports_five_changes()
    test_template_is_checkable()
    if FAILURES:
        print("\n%d failure(s)." % len(FAILURES))
        return 1
    print("\nall passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
