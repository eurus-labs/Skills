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

## Stages: `--upto`

`check <topic-folder> --upto analysis|software|epics` reads the folder up to a stage and leaves later files
unread, so a stale downstream file never blocks the skill that regenerates it.

| Flag | Reads | Rules |
| ---- | ----- | ----- |
| `--upto analysis` | `analysis.md`, `dou.md` | IDs, `Status:`, closed points, `final` over a blocking point |
| `--upto software` | adds `software-requirements.md` | the `SYS-` to `SWR-` rules, and `Provisional` over a draft analysis |
| `--upto epics`, or no flag | adds `epics.md` | every `SWR-` in exactly one epic |

A coverage failure is reported at the file that lacks the coverage, not at the upstream row, with the upstream
line in the message: `FAIL software-requirements.md:1: in-scope system requirement SYS-009 (analysis.md:24) has no
software requirement …` and `FAIL epics.md:1: SWR-003 (software-requirements.md:40) is in no epic`. A row whose
Status is `superseded` is never expected to have a software requirement, whatever its Scope says.

## What fails

`check` prints `FAIL <file>:<line>: <message>` for each broken rule, then the count, and exits 1; it prints
`OK …` and exits 0 when consistent. Exit 2 is a usage error: a missing folder or `analysis.md`, an unreadable file.

| Message | Rule |
| ------- | ---- |
| `SWR-… (software-requirements.md:N) is in no epic` | reported at `epics.md:1`; add it to an epic's `Covers:` |
| `SWR-… is in both E-01 and E-02` | a software requirement is covered by two epics; keep one |
| `duplicate ID …` | an `E-` ID is declared twice (or a `SYS-`, `DOU-` or `SWR-` one) |
| `unknown ID …` | an `SWR-`, `SYS-`, `DOU-` or `E-` ID is referenced but no file declares it |
| `epics.md is not marked Provisional while analysis.md is draft` | the analysis is still a draft; stop, or head the file `Provisional` when the user asked |
| any other message | not this skill's files: stop and report the line to the user |
