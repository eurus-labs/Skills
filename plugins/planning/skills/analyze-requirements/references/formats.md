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
| `in-scope system requirement … has no software requirement …` | only once `software-requirements.md` exists |
| `… is not marked Provisional while analysis.md is draft` | `software-requirements.md` or `epics.md` over a `draft` analysis |
| `SWR-… traces to …`, `SWR-… is in no epic`, `SWR-… is in both …` | rules of the later skills; fix them there, never here |
