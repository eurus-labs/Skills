---
type: llm
focus: { source: file, path: requirements/export/analysis.md }
---

The text is the `analysis.md` the run wrote for a report-export requirement, comparing `requirements/v2.rst` with `requirements/v1.md` and the code in `src/exporter.py`.

PASS if it reports all five differences between the versions: the added requirement to schedule an export every night, with nothing in the code implementing it; the removed requirement that every export is recorded in the audit log; the limit changed from 50 to 100 reports per request; the new sentence that exports of large reports "should finish quickly", flagged as ambiguous or untestable, with a question for the Product Owner and no number invented for it; and the ownership requirement, which says a request from anyone but the owner is rejected, shown to contradict `src/exporter.py`, with a `path:line` citation of the code that lets a teammate export. Every open point is left open, and no answer is attributed to the Product Owner.
FAIL if any of the five is missing, if the contradiction is claimed without a `src/exporter.py` line, if a requirement that did not change is reported as changed, if an open point is marked resolved or answered, or if a number or time is given for "quickly".
