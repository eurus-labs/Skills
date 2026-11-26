# DoU — export

Discussion of Understanding: the one file of points for the Product Owner (PO). It records what the PO said,
as given.

## DOU-001 — Limit per request

- Question: Is 100 the new limit for every user, or only for some roles?
- Concerns: SYS-001
- Blocks: yes
- Status: closed
- Raised: 2026-11-25
- PO answer (as given): "Every user. 50 was a mistake in the first version."
- Date: 2026-11-26
- Confirmed by: Lan (PO)

## DOU-002 — Who may export

- Question: v2 says only the owner can export, but the code lets teammates export each other's reports (`src/exporter.py:19`). Which one is right?
- Concerns: SYS-003
- Blocks: yes
- Status: closed
- Raised: 2026-11-25
- PO answer (as given): "Owner only. Teammates must ask the owner."
- Date: 2026-11-26
- Confirmed by: Lan (PO)

## DOU-003 — What "quickly" means

- Question: The DoD (`requirements/dod.md:6`) asks a speed target for a number, its unit and the input size. What does "finish quickly" mean for a large report?
- Concerns: SYS-005
- Blocks: yes
- Status: open
- Raised: 2026-11-25
- PO answer (as given): not given
- Date: —
- Confirmed by: —

## DOU-004 — Audit log

- Question: v2 drops "every export is recorded in the audit log". Is that on purpose?
- Concerns: SYS-002, SYS-006
- Blocks: yes
- Status: closed
- Raised: 2026-11-25
- PO answer (as given): "No, keep it. Compliance needs it."
- Date: 2026-11-26
- Confirmed by: Lan (PO)

## DOU-005 — Nightly export

- Question: Which time zone does "every night" use, and what happens when a scheduled export fails?
- Concerns: SYS-004
- Blocks: no
- Status: closed
- Raised: 2026-11-25
- PO answer (as given): "UTC. If it fails, tell the user and run it again the next night."
- Date: 2026-11-26
- Confirmed by: Lan (PO)
