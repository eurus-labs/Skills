---
type: llm
focus: { source: file, path: requirements/export/dou.md }
---

The text is the `dou.md` the run wrote: the one file of points for the Product Owner (PO), for a report-export requirement analysed unattended, with the PO unreachable.

PASS if all of these hold:
- It has `DOU-` points, each with a question, the `SYS-` IDs it concerns, a `Blocks:` value and a `Status:` value.
- Points cover at least the ownership contradiction with the code, and what "finish quickly" means for a large report; the latter quotes or names the DoD criterion it fails. A point about the 50 to 100 limit may be present but is not required.
- Every point is `Status: open`, and each answer line says it was not given. No answer, decision or date is attributed to the PO, and no number is proposed as the answer for "quickly".
FAIL if a point is closed, if an answer or a confirmation by the PO is written, if one of the two required questions is missing, or if the file holds anything the PO did not say presented as an answer.
