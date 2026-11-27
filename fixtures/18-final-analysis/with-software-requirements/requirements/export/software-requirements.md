# Software requirements — export

## SWR-001 — Limit per request

- Statement: The software shall accept an export request for up to 100 reports and reject one for more than 100.
- Rationale: SYS-001 raises the limit from 50 to 100 for every user (DOU-001).
- Traces to: SYS-001
- Type: functional
- Verification criteria:
  - A request for 100 reports succeeds and returns 100 outputs.
  - A request for 101 reports is rejected with an error, and no output is written.
- Component: `src/exporter.py:8`, `src/exporter.py:33`
- Status: changes existing behavior

## SWR-002 — Owner-only export

- Statement: The software shall reject an export request for a report whose owner is not the requesting user.
- Rationale: SYS-003 limits export to the owner, teammates included (DOU-002).
- Traces to: SYS-003
- Type: functional
- Verification criteria:
  - A request from the owner of a report succeeds.
  - A request from a teammate of the owner is rejected with an error, and no output is written.
- Component: `src/exporter.py:17-19`
- Status: changes existing behavior

## SWR-003 — Nightly export

- Statement: The software shall run each export a user has scheduled once every night, in UTC.
- Rationale: SYS-004 asks for a nightly export; the time zone is UTC (DOU-005).
- Traces to: SYS-004
- Type: functional
- Verification criteria:
  - A scheduled export that is due runs once between 00:00 and 24:00 UTC, and its output is written.
  - A scheduled export that fails is reported to the user and runs again the next night.
- Component: new: no scheduler exists in `src/exporter.py`
- Status: new

## SWR-004 — Audit record

- Statement: The software shall record every export in the audit log.
- Rationale: SYS-006 keeps the audit requirement that v2 dropped (DOU-004).
- Traces to: SYS-006
- Type: functional
- Verification criteria:
  - After an export of 3 reports, the audit log holds 3 new entries, one per report.
  - An export that is rejected adds no entry for the report it rejected.
- Component: `src/exporter.py:42`
- Status: already met

## SWR-005 — Export time

- Statement: The software shall export a report of up to 10,000 rows within 30 seconds.
- Rationale: SYS-007 gives the number for "finish quickly" (DOU-003).
- Traces to: SYS-007
- Type: non-functional (performance)
- Verification criteria:
  - A report of 10,000 rows is exported in 30 seconds or less, measured from the request to the written output.
  - A report of 10,000 rows that takes 31 seconds fails the criterion.
- Component: `src/exporter.py:22-27`
- Status: new

## Traceability

| System requirement | Software requirements |
| ------------------ | --------------------- |
| SYS-001 | SWR-001 |
| SYS-003 | SWR-002 |
| SYS-004 | SWR-003 |
| SYS-006 | SWR-004 |
| SYS-007 | SWR-005 |

## Not derived to software

None.

## Gaps found

None.
