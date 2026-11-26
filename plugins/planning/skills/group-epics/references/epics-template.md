# Epics — <topic>

Grouping basis: the user outcome each epic delivers.

Written in the language of the software requirements. State the grouping basis on the line above: the user
outcome by default, or the component or the category when the user asked for that. Add `Provisional` to the
title line (`# Epics — <topic> — Provisional`) only when the user explicitly asked for epics over `Provisional`
software requirements; then every epic that depends on a blocking `DOU-` point names it.
`scripts/requirements.py check` reads the `## E-NN` headings and the `Covers:` lines. Every `SWR-` is in
exactly one epic; there is no list of requirements left out.

Each epic is a block, `## E-01 — <epic title>`, then these lines:

- `Goal` — the outcome, in one sentence.
- `Covers` — the `SWR-` IDs, comma separated.
- `Acceptance criteria` — observable behavior, drawn from the verification criteria of its software
  requirements and from the DoD, with at least one negative case.
- `Depends on epics` — `E-` IDs, or `none`.
- `Risks` — what could go wrong, and how it is handled.
- `Code areas` — `path:line` after reading it, or `new`.

## E-01 — Raise the export limit

- Goal: a user can export up to 100 reports in one request.
- Covers: SWR-001
- Acceptance criteria:
  - A request for 100 reports succeeds and returns 100 outputs.
  - A request for 101 reports is rejected with an error, and no output is written.
- Depends on epics: none
- Risks: other limits in the service still assume 50; the limit is read in one place only.
- Code areas: `src/exporter.py:8`, `src/exporter.py:31`

## E-02 — Nightly export

- Goal: a user can schedule an export that runs every night.
- Covers: SWR-002
- Acceptance criteria:
  - A scheduled export that is due runs once during the night, and its output is written.
  - A scheduled export that fails is reported to the user, and the next night's run is not affected.
- Depends on epics: E-01
- Risks: the time zone and the failure policy are not settled (DOU-002).
- Code areas: new, beside `src/exporter.py`

## Traceability

One row per software requirement, from the system requirement it derives from to the epic that holds it. A
system requirement listed in "Not derived to software" has a row with `not derived`.

| System requirement | Software requirement | Epic |
| ------------------ | -------------------- | ---- |
| SYS-001 | SWR-001 | E-01 |
| SYS-002 | SWR-002 | E-02 |
| SYS-004 | not derived | not in any epic |
