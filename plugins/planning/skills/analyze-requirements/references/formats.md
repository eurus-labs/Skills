# What `check` reads in this skill's files

`python3 scripts/requirements.py check <topic-folder>` reads up to four files in the topic folder. This skill
writes the first two; the other two belong to `derive-software-requirements` and `group-epics`, and `check`
reads them only to see that the whole folder agrees.

## `analysis.md`

- A line at the start of a line, `Status: draft` or `Status: final`.
- The System requirements table. A body row whose first cell is `SYS-001` (one ID per row, never reused)
  declares a requirement. Its `Scope` cell starts with `in` for a requirement that needs work, or `out`.
- IDs it refers to (`SYS-`, `DOU-`) in the ID, Note and DoD cells and in lines outside tables. The Previous and
  Current cells, and any text inside double quotes, quote the source and are never read as references.

## `dou.md`

One block per point: a heading `## DOU-001 — <title>`, then `- Key: value` lines.

| Key | Value `check` expects |
| --- | --------------------- |
| `Status` | `open` or `closed` |
| `Blocks` | `yes` or `no` |
| `PO answer (as given)` | on a closed point, text that is not `not given`, `none` or `—` |
| `Date` | on a closed point, a `YYYY-MM-DD` date |
| `Concerns` | the `SYS-` IDs the point is about; each must exist in `analysis.md` |

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
| `duplicate ID …` | a `SYS-`, `DOU-`, `SWR-` or `E-` ID is declared twice |
| `unknown ID …` | an ID is referenced but no file declares it |
| `analysis.md has no 'Status: draft' or 'Status: final' line` | the Status line is missing or has another value |
| `DOU-… is closed but has no PO answer` / `has no date (YYYY-MM-DD)` | a closed point needs both |
| `DOU-… has status … ` / `has Blocks …` | Status is not `open` or `closed`, or Blocks is not `yes` or `no` |
| `analysis.md is final while blocking DOU-… is open (dou.md:N)` | `final` needs every `Blocks: yes` point closed |
| `in-scope system requirement … (analysis.md:N) has no software requirement …` | reported at `software-requirements.md`, only once it exists: a stale file; name `derive-software-requirements`, never edit it |
| `… is not marked Provisional while analysis.md is draft` | `software-requirements.md` or `epics.md` over a `draft` analysis |
| `SWR-… traces to …`, `SWR-… (software-requirements.md:N) is in no epic`, `SWR-… is in both …` | rules of the later skills (the last two are reported at `epics.md`, a stale file: name `group-epics`); fix them there, never here |
