# What `check` reads in this skill's files

`python3 scripts/requirements.py check <topic-folder>` reads up to four files in the topic folder. This skill
reads the first two and writes the third; `check` reads the fourth only to see that the whole folder agrees.

## Input: `analysis.md` and `dou.md`

- `analysis.md` has a line at the start of a line, `Status: draft` or `Status: final`, and a System
  requirements table. A body row whose first cell is `SYS-001` declares a requirement. The `Scope` cell starts
  with `in` for a requirement that needs work, or `out`. Derive only the `in` rows. The `Code impact` cell gives
  the starting `path:line`, and the Sources table names the DoD file and the code repository.
- `dou.md` has one block per point: `## DOU-001 — <title>`, then `- Key: value` lines (`Question`, `Concerns`,
  `Blocks` `yes` or `no`, `Status` `open` or `closed`, `PO answer (as given)`, `Date`, `Confirmed by`). A
  point with `Blocks: yes` and `Status: open` blocks the derivation.

## Output: `software-requirements.md`

- A block per requirement: a heading `## SWR-001 — <title>`, then `- Key: value` lines. `check` reads
  `Traces to`, which must name at least one `SYS-` ID that exists in `analysis.md`.
- The table under the heading `Not derived to software`: a body row whose first cell is a `SYS-` ID.
- The first `# ` line: `check` looks for the word `Provisional` in it when `analysis.md` is `draft`.
- IDs it refers to (`SYS-`, `SWR-`, `DOU-`) in the table cells of the System requirement, Software requirement
  and Reason columns and in lines outside tables. Text inside double quotes quotes the source and is never
  read as a reference.

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
| `duplicate ID …` | an `SWR-` ID is declared twice (or a `SYS-`, `DOU-` or `E-` one) |
| `unknown ID …` | an ID is referenced but no file declares it |
| `in-scope system requirement SYS-… (analysis.md:N) has no software requirement and is not in 'Not derived to software'` | reported at `software-requirements.md:1`; derive it, or list it with a reason |
| `SWR-… traces to no SYS- ID` / `traces to SYS-…, which does not exist in analysis.md` | a `Traces to:` line with no ID, or an ID `analysis.md` does not declare |
| `software-requirements.md is not marked Provisional while analysis.md is draft` | the file needs `Provisional` in its title, or the analysis must become final first |
| `analysis.md is final while blocking DOU-… is open`, `DOU-… is closed but has no …` | not this skill's files: stop and report them to the user for `analyze-requirements` |
| `SWR-… (software-requirements.md:N) is in no epic`, `SWR-… is in both …` | reported at `epics.md`, only once it exists; a rule of `group-epics`. Run `--upto software` |
