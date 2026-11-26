---
type: llm
focus: { source: file, path: requirements/export/epics.md }
---

The text is the `epics.md` the run wrote from a `software-requirements.md` with five software requirements for a report export: SWR-001 (accept up to 100 reports per request), SWR-002 (owner-only export), SWR-003 (nightly export), SWR-004 (audit record of every export) and SWR-005 (export of 10,000 rows within 30 seconds).

PASS if all of these hold:
- The grouping basis is stated first, before the epics (the user outcome by default).
- Each of SWR-001 to SWR-005 is on the `Covers:` line of exactly one epic, no software requirement is in two epics, and there is no list of requirements left out.
- Every epic has a goal, the `SWR-` IDs it covers, acceptance criteria that state observable behavior with at least one negative case (for example the 101st report rejected, or a teammate's request rejected), dependencies, risks and code areas.
- The acceptance criteria come from the verification criteria of the epic's software requirements, and an epic that holds the export-time requirement keeps 10,000 rows and 30 seconds in its criteria.
- A traceability table maps each `SYS-` to its `SWR-` and its `E-`.
- No epic states something that none of the five software requirements states.
FAIL if any of these is missing, if a software requirement is in no epic or in two, if the file is headed `Provisional`, or if an epic is invented.
