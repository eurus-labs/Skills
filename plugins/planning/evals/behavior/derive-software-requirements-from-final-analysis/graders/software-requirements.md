---
type: llm
focus: { source: file, path: requirements/export/software-requirements.md }
---

The text is the `software-requirements.md` the run wrote from a final requirement analysis of a report export. The analysis has five in-scope system requirements: SYS-001 (at most 100 reports per request, `src/exporter.py:8`), SYS-003 (only the owner can export; a teammate's request is rejected, and `src/exporter.py:17-19` lets teammates export today), SYS-004 (a scheduled export runs every night, in UTC; when it fails, the user is told and it runs again the next night), SYS-006 (every export is recorded in the audit log, already met at `src/exporter.py:42`) and SYS-007 (a report of up to 10,000 rows exports within 30 seconds). SYS-002 and SYS-005 are superseded, SYS-008 is unchanged, and all three are out of scope. The Definition of Done asks that each requirement states one observable behavior and that a speed target gives a number, its unit and the input size.

PASS if all of these hold:
- Each of the five in-scope system requirements is traced by at least one `SWR-` whose statement starts "The software shall" and states what the software does, not how it is built. The superseded and unchanged requirements are not derived.
- Each `SWR-` has a rationale, its `Traces to` line, a type (the export-time one is non-functional with the quality named), testable verification criteria and a code area as `path:line`, or "new" with where.
- The criteria meet the DoD: the export-time requirement has 10,000 rows and 30 seconds in its criteria, and a requirement that can refuse a request has a negative case.
- No requirement is invented: nothing states a behavior that none of the five system requirements supports.
- A traceability table maps every in-scope system requirement to its software requirements, and the file has a "Not derived to software" section.
FAIL if an in-scope requirement has no `SWR-`, if a statement names a technology, class or table, if the export-time criteria have no number, if a requirement no system requirement supports is present, or if a superseded requirement is derived.
