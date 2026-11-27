# Software requirements — <topic>

Written in the language of the analysis. Add `Provisional` to this title line (`# Software requirements —
<topic> — Provisional`) only when the user explicitly asked for the file while a blocking point in `dou.md` is
open; then each `SWR-` that depends on one names it in its rationale.
`scripts/requirements.py check` reads the `## SWR-NNN` headings, the `Traces to:` lines and the "Not derived to
software" table.

Each `SWR-` is a block, `## SWR-001 — <title>`, then these lines, in this order:

- `Statement` — one sentence, "The software shall …": what the software does, never how it is built.
- `Rationale` — why, with the `SYS-` and the closed `DOU-` point that fix it.
- `Traces to` — the `SYS-` IDs it derives from, comma separated. At least one, and each must exist.
- `Type` — `functional`, or `non-functional (<quality>)`: performance, security, availability, usability, …
- `Verification criteria` — a list of testable criteria that meet the DoD: the input, the observable result,
  the pass condition, a number where the DoD asks for one, and a negative case where a request can be refused.
- `Component` — the code area as `path:line` after reading it, or `new: <where it would live>`.
- `Status` — `new`, `changes existing behavior` or `already met`.

## SWR-001 — Limit per request

- Statement: The software shall accept an export request for up to 100 reports and reject one for more.
- Rationale: SYS-001 raises the limit from 50 to 100 for every user (DOU-001).
- Traces to: SYS-001
- Type: functional
- Verification criteria:
  - A request for 100 reports succeeds and returns 100 outputs.
  - A request for 101 reports is rejected with an error, and no output is written.
- Component: `src/exporter.py:8`, `src/exporter.py:31`
- Status: changes existing behavior

## SWR-002 — Nightly export

- Statement: The software shall run each export a user has scheduled once every night.
- Rationale: SYS-002 asks for a nightly export. The time zone and the failure policy are not settled (DOU-002).
- Traces to: SYS-002
- Type: functional
- Verification criteria:
  - A scheduled export that is due runs once during the night, and its output is written.
  - A scheduled export that fails is reported to the user, and the next night's run is not affected.
- Component: new: no scheduler exists in `src/exporter.py`
- Status: new

## Traceability

Two ways: every in-scope `SYS-` lists the `SWR-` that derive it or says `not derived`, and every `SWR-` above
traces to a `SYS-` listed here.

| System requirement | Software requirements |
| ------------------ | --------------------- |
| SYS-001 | SWR-001 |
| SYS-002 | SWR-002 |
| SYS-004 | not derived |

## Not derived to software

Every in-scope `SYS-` with no `SWR-` is here with the reason: a manual or process step, or hardware.

| System requirement | Reason |
| ------------------ | ------ |
| SYS-004 | a manual step: the compliance officer's monthly review |

## Gaps found

Questions this derivation raised, for the user to take to `analyze-requirements`, which adds the `DOU-` point.
This skill does not edit `analysis.md` or `dou.md`. Each says the `SYS-` it concerns and whether it blocks.
`None` when there are none.

- None
