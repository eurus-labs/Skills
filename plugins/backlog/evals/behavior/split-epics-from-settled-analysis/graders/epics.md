---
type: llm
focus: { source: file, path: requirements/export/epics.md }
---

The text is the `epics.md` the run wrote for a report-export requirement analysis whose blocking open points are all resolved and whose one remaining open point, OP-005 (the time zone and failure handling of the nightly export), does not block.

PASS if all of these hold:
- The file is not headed `Provisional`.
- Each of the four in-scope requirements that need work, R-001 (limit of 100 reports), R-003 (owner-only export), R-004 (nightly scheduled export) and R-007 (10,000 rows within 30 seconds), is covered by exactly one epic, and no requirement is covered by two epics.
- R-006, the audit log requirement the code already meets, is listed under "Not in any epic" with a reason that names the code, and is not an epic of its own. The superseded rows R-002 and R-005 and the unchanged row R-008 are not placed in any epic.
- Every epic has a goal, the R- IDs it covers, acceptance criteria that state observable behavior with at least one negative case (for example a request from a non-owner rejected, or the 101st report rejected), dependencies, risks and code areas.
- The epic that covers R-004 names OP-005 as a risk or open question, or is otherwise marked as depending on it, and does not invent a time zone or a failure policy.
- A traceability table maps every in-scope requirement to its epic or to "not in any epic".

FAIL if any of these is missing, if a superseded requirement is covered by an epic, if an answer to OP-005 is invented, or if the file is headed `Provisional`.
