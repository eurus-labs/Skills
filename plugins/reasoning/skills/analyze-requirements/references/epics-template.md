# Epics — <topic>

Add `Provisional` to this title line (`# Epics — <topic> — Provisional`) only when the user explicitly asked
for epics while a blocking open point is open; then every epic that depends on one names it.
Write in the language of the requirement. `scripts/requirements.py check` reads the `## E-NN` headings, the
`Covers:` lines and the `Not in any epic` list.

## E-01 — <epic title>

- Goal: <the outcome, in one sentence>
- Covers: R-001, R-003
- Acceptance criteria:
  - <an observable behavior, with the check that proves it>
  - <a negative case>
- Depends on epics: none
- Depends on open points: none (a Provisional epic lists its `OP-` IDs here)
- Risks: <what could go wrong, and how it is handled>
- Code areas: `src/exporter.py`

## E-02 — <epic title>

- Goal: <...>
- Covers: R-004
- Acceptance criteria:
  - <...>
- Depends on epics: E-01
- Depends on open points: none
- Risks: <...>
- Code areas: <paths, or "new">

## Not in any epic

Every in-scope requirement is in exactly one epic or listed here with the reason.

- R-005 — <reason, for example "already met: `src/exporter.py:41`">

## Traceability

| Requirement | Epic |
| ----------- | ---- |
| R-001 | E-01 |
| R-003 | E-01 |
| R-004 | E-02 |
| R-005 | not in any epic |
