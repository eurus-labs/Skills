# What `check` reads in this skill's files

`python3 scripts/requirements.py check <topic-folder>` reads up to four files in the topic folder. This skill
reads `software-requirements.md` (and `check` reads `analysis.md` and `dou.md` to see that it agrees with
them), and writes `epics.md`.

## Input: `software-requirements.md`

- One block per requirement: a heading `## SWR-001 — <title>`, then `- Key: value` lines. This skill uses
  `Statement`, `Traces to` (the `SYS-` IDs), `Verification criteria`, `Component` and `Status`.
- The first `# ` line holds `Provisional` when the file was written over a draft analysis.
- The table under `Not derived to software` lists the `SYS-` IDs with no software requirement.

## Output: `epics.md`

- One block per epic: a heading `## E-01 — <title>`, then `- Key: value` lines. `check` reads the `Covers:`
  line, which lists the `SWR-` IDs. An ID there that `software-requirements.md` does not declare is an
  unknown ID.
- Each `SWR-` must appear on the `Covers:` line of exactly one epic.
- `Depends on epics:` may name `E-` IDs; each must be declared in the file.
- The first `# ` line: `check` looks for the word `Provisional` in it when `analysis.md` is `draft`.
- IDs it refers to (`SYS-`, `SWR-`, `E-`) in any cell of the traceability table and in lines outside tables.
  Text inside double quotes quotes the source and is never read as a reference.

## What fails

`check` prints `FAIL <file>:<line>: <message>` for each broken rule, then the count, and exits 1; it prints
`OK …` and exits 0 when consistent. Exit 2 is a usage error: a missing folder or `analysis.md`, an unreadable file.

| Message | Rule |
| ------- | ---- |
| `SWR-… is in no epic` | reported at the `## SWR-` heading in `software-requirements.md`; add it to an epic's `Covers:` |
| `SWR-… is in both E-01 and E-02` | a software requirement is covered by two epics; keep one |
| `duplicate ID …` | an `E-` ID is declared twice (or a `SYS-`, `DOU-` or `SWR-` one) |
| `unknown ID …` | an `SWR-`, `SYS-` or `E-` ID is referenced but no file declares it |
| `epics.md is not marked Provisional while analysis.md is draft` | the analysis is still a draft; stop, or head the file `Provisional` when the user asked |
| any other message | not this skill's files: stop and report the line to the user |
