# DoU — <topic>

Discussion of Understanding: the one file of points for the Product Owner (PO). Written in the language of the
requirement. Every analysis pass adds points; after each discussion the points the PO answered are closed.
It records what the PO said, as given, and never the analyst's guess. Nothing is deleted: a point the PO
later changes is answered by a new point that names the old one in `Supersedes:`.
`scripts/requirements.py check` reads the `## DOU-NNN` headings and the `- Key: value` lines under them, so
keep the keys. Write each value on its own line; an indented line continues the line above.

Keys: `Question`, `Concerns` (the `SYS-` IDs), `Blocks` (`yes` when the requirement cannot be derived into a
testable software requirement until the PO answers, else `no`), `Status` (`open` or `closed`), `Raised`,
`PO answer (as given)`, `Date` (when the PO answered, `YYYY-MM-DD`), `Confirmed by` and, when there is one,
`Supersedes`. A closed point needs an answer and a date. An open point says `not given` and `—`.

## DOU-001 — Limit per request

- Question: Is 100 the new limit for every user, or only for some roles?
- Concerns: SYS-001
- Blocks: yes
- Status: closed
- Raised: 2026-11-25
- PO answer (as given): "Every user. 50 was a mistake in the first version."
- Date: 2026-11-26
- Confirmed by: Lan (PO), from the analyst's notes of the call

## DOU-002 — Nightly export

- Question: Which time zone does "every night" use, and what happens when a scheduled export fails?
- Concerns: SYS-002
- Blocks: no
- Status: open
- Raised: 2026-11-25
- PO answer (as given): not given
- Date: —
- Confirmed by: —
