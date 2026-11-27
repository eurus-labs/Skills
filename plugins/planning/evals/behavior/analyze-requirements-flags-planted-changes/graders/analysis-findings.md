---
type: llm
focus: { source: file, path: requirements/export/analysis.md }
---

The text is the `analysis.md` the run wrote for a report-export requirement, comparing `requirements/v2.rst` with `requirements/v1.md`, the Definition of Done in `requirements/dod.md` and the code in `src/exporter.py`.

PASS if all of these hold:
- It reports all five differences between the versions as system requirements (`SYS-` rows): the added requirement to schedule an export every night, with nothing in the code implementing it; the removed requirement that every export is recorded in the audit log; the limit changed from 50 to 100 reports per request; the new sentence that exports of large reports "should finish quickly"; and the ownership requirement, which says a request from anyone but the owner is rejected.
- The ownership requirement is shown to contradict `src/exporter.py`, with a `path:line` citation of the code that lets a teammate export.
- Each in-scope requirement has a DoD verdict, and the "finish quickly" requirement is marked as failing the DoD (no number, unit or input size), pointing at a `DOU-` point. No number or time is given for "quickly".
- The file has a `Status:` line that says `draft`, not `final`, and refers to the questions for the Product Owner by `DOU-` ID without an open-point table.
FAIL if any of the five is missing, if the contradiction is claimed without a `src/exporter.py` line, if a requirement that did not change is reported as changed, if the "quickly" requirement is not tied to the DoD, if a number or time is given for "quickly", or if the status is `final`.
