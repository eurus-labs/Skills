#!/usr/bin/env python3
"""Behavioural tests for shared/scripts/requirements/requirements.py, the source of the copy in each skill of
the planning plugin.

`diff` must find every added, removed, changed and unchanged unit in .md, .rst and .txt files with
correct line ranges, and `check` must fail, naming the line, for each rule of plan 25 (Decision 7)
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


ANALYSIS = """# Requirement analysis - export

Status: final

## System requirements

| ID | Status | Scope | Previous | Current | Code impact | DoD | Note |
| -- | ------ | ----- | -------- | ------- | ----------- | --- | ---- |
| SYS-001 | changed | in | a | b | new | met | |
| SYS-002 | added | in | - | c | new | gap: DOU-002 | |
| SYS-003 | removed | out (dropped) | d | - | already met | met | |
| SYS-004 | added | in | - | e | new | met | |

## Findings

- **SYS-002** - untestable, see DOU-002.
"""

DOU = """# DoU - export

## DOU-001 - Which limit?

- Question: Is 100 the limit for every user?
- Concerns: SYS-001
- Blocks: yes
- Status: closed
- PO answer (as given): "Every user."
- Date: 2026-11-26
- Confirmed by: Lan

## DOU-002 - How fast?

- Question: What does "quickly" mean?
- Concerns: SYS-002
- Blocks: no
- Status: open
- PO answer (as given): not given
- Date: -
- Confirmed by: -
"""

SWR = """# Software requirements - export

## SWR-001 - Limit

- Statement: The software shall accept at most 100 reports in one export request.
- Traces to: SYS-001
- Type: functional
- Verification criteria:
  - A request for 101 reports is rejected.

## SWR-002 - Speed

- Statement: The software shall export a 10,000-row report within 30 seconds.
- Traces to: SYS-002
- Type: non-functional (performance)

## Traceability

| System requirement | Software requirements |
| ------------------ | --------------------- |
| SYS-001 | SWR-001 |
| SYS-002 | SWR-002 |
| SYS-004 | not derived |

## Not derived to software

| System requirement | Reason |
| ------------------ | ------ |
| SYS-004 | a manual review step |
"""

EPICS = """# Epics - export

## E-01 - Limits

- Goal: raise the limit
- Covers: SWR-001
- Depends on epics: none

## E-02 - Speed

- Goal: export quickly
- Covers: SWR-002
- Depends on epics: E-01

## Traceability

| System requirement | Software requirement | Epic |
| ------------------ | -------------------- | ---- |
| SYS-001 | SWR-001 | E-01 |
| SYS-002 | SWR-002 | E-02 |
"""


def folder(tmp, name, analysis=ANALYSIS, dou=DOU, swr=SWR, epics=EPICS):
    root = os.path.join(tmp, name)
    write(root, "analysis.md", analysis)
    for fname, text in (("dou.md", dou), ("software-requirements.md", swr), ("epics.md", epics)):
        if text is not None:
            write(root, fname, text)
    return root


def problems(root):
    return req.check(root)[0]


def has(found, name, fragment):
    return [p for p in found if p[0] == name and fragment in p[2]]


def line_of(text, fragment):
    for n, line in enumerate(text.splitlines(), 1):
        if fragment in line:
            return n
    raise AssertionError(fragment)


def test_check_consistent(tmp):
    ok = folder(tmp, "ok")
    check("check passes on a consistent folder of four files", problems(ok) == [], str(problems(ok)))
    proc = subprocess.run([sys.executable, SCRIPT, "check", ok], capture_output=True, text=True)
    check("the CLI exits 0 and prints OK with the counts",
          proc.returncode == 0 and proc.stdout.startswith("OK 4 system requirement(s), 2 DoU point(s), "
                                                           "2 software requirement(s), 2 epic(s)"),
          proc.stdout)
    plain = ANALYSIS.replace("gap: DOU-002", "gap").replace("see DOU-002", "see the PO")
    only = folder(tmp, "only-analysis", dou=None, swr=None, epics=None, analysis=plain)
    check("a folder with only analysis.md passes", problems(only) == [], str(problems(only)))
    draft = folder(tmp, "draft-no-dou", dou=None, swr=None, epics=None,
                   analysis=plain.replace("Status: final", "Status: draft"))
    check("a draft analysis with no blocking point passes", problems(draft) == [], str(problems(draft)))


def test_check_ids(tmp):
    dup = folder(tmp, "dup", analysis=ANALYSIS.replace("| SYS-002 | added", "| SYS-001 | added"))
    found = has(problems(dup), "analysis.md", "duplicate ID SYS-001")
    check("a duplicated SYS- ID fails, naming the line",
          len(found) == 1 and found[0][1] == line_of(ANALYSIS, "| SYS-002 |"), str(problems(dup)))
    dup_dou = folder(tmp, "dup-dou", dou=DOU.replace("## DOU-002", "## DOU-001"))
    check("a duplicated DOU- ID fails", has(problems(dup_dou), "dou.md", "duplicate ID DOU-001"))
    dup_swr = folder(tmp, "dup-swr", swr=SWR.replace("## SWR-002", "## SWR-001"))
    check("a duplicated SWR- ID fails", has(problems(dup_swr), "software-requirements.md", "duplicate ID SWR-001"))
    dup_epic = folder(tmp, "dup-epic", epics=EPICS.replace("## E-02", "## E-01"))
    check("a duplicated epic ID fails", has(problems(dup_epic), "epics.md", "duplicate ID E-01"))

    unknown = folder(tmp, "unknown-swr", epics=EPICS.replace("Covers: SWR-001", "Covers: SWR-001, SWR-009"))
    found = has(problems(unknown), "epics.md", "unknown ID SWR-009")
    check("an unknown SWR- ID in an epic fails, naming the line",
          len(found) == 1 and found[0][1] == line_of(EPICS, "Covers: SWR-001"), str(problems(unknown)))
    unknown_dou = folder(tmp, "unknown-dou", analysis=ANALYSIS.replace("see DOU-002", "see DOU-077"))
    check("an unknown DOU- ID in the analysis fails", has(problems(unknown_dou), "analysis.md", "unknown ID DOU-077"))
    unknown_sys = folder(tmp, "unknown-sys", dou=DOU.replace("Concerns: SYS-002", "Concerns: SYS-044"))
    check("an unknown SYS- ID in a DoU point fails", has(problems(unknown_sys), "dou.md", "unknown ID SYS-044"))
    unknown_epic = folder(tmp, "unknown-epic", epics=EPICS.replace("Depends on epics: E-01", "Depends on epics: E-07"))
    check("an unknown epic ID in Depends on epics fails", has(problems(unknown_epic), "epics.md", "unknown ID E-07"))
    trace = folder(tmp, "trace-row", epics=EPICS.replace("| SYS-001 | SWR-001 | E-01 |",
                                                         "| SYS-001 | SWR-001 | E-01 |\n| SYS-050 | SWR-001 | E-01 |"))
    check("an unknown ID in a traceability row fails", has(problems(trace), "epics.md", "unknown ID SYS-050"))
    note = folder(tmp, "note", analysis=ANALYSIS.replace("| new | met | |\n| SYS-002", "| new | met | superseded by SYS-099 |\n| SYS-002"))
    check("an unknown ID in the Note column fails", has(problems(note), "analysis.md", "unknown ID SYS-099"))

    quoted = ANALYSIS.replace("| SYS-001 | changed | in | a | b |",
                              '| SYS-001 | changed | in | "SYS-1042: Reports must be encrypted." | "DOU-77 is old; SYS-1042 stays." |')
    qdir = folder(tmp, "quoted", analysis=quoted,
                  dou=DOU.replace('"Every user."', '"SYS-1042 is dropped, see DOU-77."'),
                  swr=SWR.replace("- Type: functional", '- Rationale: the source says "SYS-1042: encrypt" and "SWR-88"\n- Type: functional'),
                  epics=EPICS.replace("- Goal: raise the limit", '- Goal: keep "SYS-1042: Reports must be encrypted." and "E-90"'))
    check("IDs quoted from the source, in a table cell, a DoU answer, a requirement or an epic line, are not references",
          problems(qdir) == [], str(problems(qdir)))
    bare = folder(tmp, "bare-epic", epics=EPICS.replace("- Goal: raise the limit", '- Goal: "SYS-1042 quoted" and SYS-2000'))
    check("an unquoted unknown ID next to a quote still fails",
          [p[2] for p in problems(bare)] == ["unknown ID SYS-2000"], str(problems(bare)))


def test_check_dou(tmp):
    no_answer = folder(tmp, "closed-no-answer", dou=DOU.replace('"Every user."', "not given"))
    found = has(problems(no_answer), "dou.md", "DOU-001 is closed but has no PO answer")
    check("a closed DoU point with no answer fails, naming the point's line",
          len(found) == 1 and found[0][1] == line_of(DOU, "## DOU-001"), str(problems(no_answer)))
    empty_answer = folder(tmp, "closed-empty-answer", dou=DOU.replace(' "Every user."', ""))
    check("a closed DoU point with an empty answer fails",
          has(problems(empty_answer), "dou.md", "has no PO answer"), str(problems(empty_answer)))
    no_date = folder(tmp, "closed-no-date", dou=DOU.replace("- Date: 2026-11-26", "- Date: -"))
    found = has(problems(no_date), "dou.md", "DOU-001 is closed but has no date")
    check("a closed DoU point with no date fails, naming the point's line",
          len(found) == 1 and found[0][1] == line_of(DOU, "## DOU-001"), str(problems(no_date)))
    check("an open point with no answer and no date passes", problems(folder(tmp, "open-ok")) == [])
    bad_status = folder(tmp, "bad-status", dou=DOU.replace("Status: open", "Status: pending"))
    check("a DoU point with an unknown status fails", has(problems(bad_status), "dou.md", "status 'pending'"))
    bad_blocks = folder(tmp, "bad-blocks", dou=DOU.replace("Blocks: no", "Blocks: maybe"))
    check("a DoU point with an unknown Blocks value fails", has(problems(bad_blocks), "dou.md", "Blocks 'maybe'"))
    wrapped = folder(tmp, "wrapped-answer",
                     dou=DOU.replace('- PO answer (as given): "Every user."',
                                     '- PO answer (as given):\n  "Every user.\n  Fifty was a mistake."'))
    check("an answer continued on indented lines counts as given", problems(wrapped) == [], str(problems(wrapped)))


def test_check_status(tmp):
    blocking = DOU.replace("Blocks: no", "Blocks: yes")
    final = folder(tmp, "final-blocked", dou=blocking)
    found = has(problems(final), "analysis.md", "final while blocking DOU-002 is open")
    check("a final analysis with an open blocking point fails, naming the point and both lines",
          len(found) == 1 and found[0][1] == line_of(ANALYSIS, "Status: final")
          and "dou.md:%d" % line_of(DOU, "## DOU-002") in found[0][2], str(problems(final)))
    draft = folder(tmp, "draft-blocked", dou=blocking,
                   analysis=ANALYSIS.replace("Status: final", "Status: draft"), swr=None, epics=None)
    check("a draft analysis with an open blocking point passes", problems(draft) == [], str(problems(draft)))
    closed = folder(tmp, "final-closed", dou=blocking.replace("Status: open", "Status: closed")
                    .replace("- PO answer (as given): not given", '- PO answer (as given): "30 seconds."')
                    .replace("- Date: -", "- Date: 2026-11-26"))
    check("a final analysis whose blocking point is closed passes", problems(closed) == [], str(problems(closed)))
    no_status = folder(tmp, "no-status", analysis=ANALYSIS.replace("Status: final\n", ""))
    check("an analysis with no Status line fails", has(problems(no_status), "analysis.md", "no 'Status: draft'"))
    odd = folder(tmp, "odd-status", analysis=ANALYSIS.replace("Status: final", "Status: done"))
    check("an analysis with another status fails", has(problems(odd), "analysis.md", "status 'done'"))

    over_draft = ANALYSIS.replace("Status: final", "Status: draft")
    swr_draft = folder(tmp, "swr-over-draft", analysis=over_draft, epics=None)
    found = has(problems(swr_draft), "software-requirements.md", "not marked Provisional while analysis.md is draft")
    check("a non-provisional software-requirements.md over a draft analysis fails",
          len(found) == 1 and found[0][1] == 1, str(problems(swr_draft)))
    epics_draft = folder(tmp, "epics-over-draft", analysis=over_draft,
                         swr=SWR.replace("# Software requirements - export", "# Software requirements - export - Provisional"))
    found = has(problems(epics_draft), "epics.md", "not marked Provisional while analysis.md is draft")
    check("non-provisional epics over a draft analysis fail, even over provisional software requirements",
          len(found) == 1 and found[0][1] == 1, str(problems(epics_draft)))
    prov = folder(tmp, "provisional", analysis=over_draft,
                  swr=SWR.replace("# Software requirements - export", "# Software requirements - export - Provisional"),
                  epics=EPICS.replace("# Epics - export", "# Epics - export - Provisional"))
    check("provisional files over a draft analysis pass", problems(prov) == [], str(problems(prov)))


def test_check_traceability(tmp):
    untraced = folder(tmp, "untraced", swr=SWR.replace("Traces to: SYS-002", "Traces to: SYS-001"))
    found = has(problems(untraced), "analysis.md", "SYS-002 has no software requirement")
    check("an in-scope SYS- with no SWR- and not in 'Not derived' fails, naming the line",
          len(found) == 1 and found[0][1] == line_of(ANALYSIS, "| SYS-002 |"), str(problems(untraced)))
    listed = folder(tmp, "listed", swr=SWR.replace("Traces to: SYS-002", "Traces to: SYS-001").replace(
        "| SYS-004 | a manual review step |", "| SYS-004 | a manual review step |\n| SYS-002 | hardware |"))
    check("an in-scope SYS- in the 'Not derived to software' table passes", problems(listed) == [], str(problems(listed)))
    out_of_scope = folder(tmp, "out-of-scope")
    check("an out-of-scope SYS- needs no SWR-", not has(problems(out_of_scope), "analysis.md", "SYS-003"))
    wrong_section = folder(tmp, "wrong-section", swr=SWR.replace("## Not derived to software", "## Elsewhere"))
    check("a SYS- listed under another heading is not 'Not derived'",
          has(problems(wrong_section), "analysis.md", "SYS-004 has no software requirement"),
          str(problems(wrong_section)))

    nowhere = folder(tmp, "traces-nowhere", swr=SWR.replace("Traces to: SYS-002", "Traces to: SYS-088"))
    found = has(problems(nowhere), "software-requirements.md", "SWR-002 traces to SYS-088, which does not exist")
    check("an SWR- tracing to a SYS- that does not exist fails, naming the Traces to line",
          len(found) == 1 and found[0][1] == line_of(SWR, "Traces to: SYS-002")
          and not has(problems(nowhere), "software-requirements.md", "unknown ID SYS-088"), str(problems(nowhere)))
    empty = folder(tmp, "traces-empty", swr=SWR.replace("Traces to: SYS-002", "Traces to: none"))
    check("an SWR- with no SYS- in its Traces to line fails",
          has(problems(empty), "software-requirements.md", "SWR-002 traces to no SYS- ID"), str(problems(empty)))
    missing = folder(tmp, "traces-missing", swr=SWR.replace("- Traces to: SYS-002\n", ""))
    check("an SWR- with no Traces to line fails, naming its heading",
          has(problems(missing), "software-requirements.md", "SWR-002 traces to no SYS- ID"), str(problems(missing)))

    uncovered = folder(tmp, "swr-in-no-epic", epics=EPICS.replace("Covers: SWR-002", "Covers: none"))
    found = has(problems(uncovered), "software-requirements.md", "SWR-002 is in no epic")
    check("an SWR- in no epic fails, naming the line",
          len(found) == 1 and found[0][1] == line_of(SWR, "## SWR-002"), str(problems(uncovered)))
    twice = folder(tmp, "swr-in-two-epics", epics=EPICS.replace("Covers: SWR-002", "Covers: SWR-001, SWR-002"))
    found = has(problems(twice), "epics.md", "SWR-001 is in both E-01 and E-02")
    check("an SWR- in two epics fails", len(found) == 1 and found[0][1] == line_of(EPICS, "Covers: SWR-002"),
          str(problems(twice)))
    no_epics = folder(tmp, "no-epics-file", epics=None)
    check("with no epics.md, no SWR- needs an epic", problems(no_epics) == [], str(problems(no_epics)))


def test_check_cli(tmp):
    bad = folder(tmp, "cli-bad", swr=SWR.replace("Traces to: SYS-002", "Traces to: SYS-001"))
    proc = subprocess.run([sys.executable, SCRIPT, "check", bad], capture_output=True, text=True)
    check("the CLI exits 1 and prints FAIL file:line: message",
          proc.returncode == 1 and "FAIL analysis.md:%d:" % line_of(ANALYSIS, "| SYS-002 |") in proc.stdout
          and "1 problem(s)." in proc.stdout, proc.stdout)
    empty = os.path.join(tmp, "empty-folder")
    os.makedirs(empty)
    proc = subprocess.run([sys.executable, SCRIPT, "check", empty], capture_output=True, text=True)
    check("the CLI exits 2 when analysis.md is missing", proc.returncode == 2 and "analysis.md" in proc.stderr,
          proc.stderr)
    proc = subprocess.run([sys.executable, SCRIPT, "frobnicate"], capture_output=True, text=True)
    check("the CLI exits 2 on an unknown subcommand", proc.returncode == 2 and "usage" in proc.stderr)


def test_templates_are_checkable(tmp):
    """The four shipped templates, copied as they are, must be one consistent folder for `check`."""
    skills = os.path.join(REPO, "plugins", "planning", "skills")
    sources = (("analysis.md", "analyze-requirements", "analysis-template.md"),
               ("dou.md", "analyze-requirements", "dou-template.md"),
               ("software-requirements.md", "derive-software-requirements", "software-requirements-template.md"),
               ("epics.md", "group-epics", "epics-template.md"))
    root = os.path.join(tmp, "templates")
    for name, skill, template in sources:
        with open(os.path.join(skills, skill, "references", template), encoding="utf-8") as fh:
            write(root, name, fh.read())
    found = problems(root)
    check("the four templates together pass check", found == [], str(found))
    counts = req.check(root)[1]
    check("the templates declare system requirements, points, software requirements and epics",
          counts == {"system_requirements": 4, "dou_points": 2, "software_requirements": 2, "epics": 2},
          str(counts))
    with open(os.path.join(root, "epics.md"), encoding="utf-8") as fh:
        text = fh.read()
    write(root, "epics.md", text.replace("Covers: SWR-002", "Covers: SWR-001"))
    check("a template epic that drops a software requirement is reported",
          has(problems(root), "software-requirements.md", "SWR-002 is in no epic"), str(problems(root)))


def main():
    with tempfile.TemporaryDirectory() as tmp:
        for test in (test_diff_markdown_and_rst, test_diff_changes_only, test_diff_text,
                     test_diff_first_analysis_and_moves, test_diff_move_survives_changes_only,
                     test_diff_literal_changes_survive_normalization, test_diff_formatting_only_is_unchanged,
                     test_diff_ids_and_failures, test_check_consistent, test_check_ids, test_check_dou,
                     test_check_status, test_check_traceability, test_check_cli,
                     test_templates_are_checkable):
            sub = os.path.join(tmp, test.__name__)
            os.makedirs(sub)
            test(sub)
    test_diff_fixture_17_reports_five_changes()
    if FAILURES:
        print("\n%d failure(s)." % len(FAILURES))
        return 1
    print("\nall passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
