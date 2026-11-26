# `requirements.py check` output

`python3 scripts/requirements.py check <topic-folder>` reads `analysis.md` and `dou-*.md`, and `epics.md` when it
exists. It prints `FAIL <file>:<line>: <message>` per broken rule, then the count, and exits 1; it prints
`OK …` and exits 0 when consistent. Exit 2 means a usage error: a missing folder or `analysis.md`, or an
unreadable file.

| Message | Rule |
| ------- | ---- |
| `in-scope requirement … is in no epic and not in the 'Not in any epic' list` | a row whose Scope starts with `in` is in no epic's `Covers:` line and not in the "Not in any epic" list. It is reported against `analysis.md`, and only once `epics.md` exists |
| `… is in both E-01 and E-02` | a requirement is covered by two epics |
| `epics are not marked Provisional while blocking open point … is open` | `epics.md` exists, its title line lacks `Provisional`, and an open point with `Blocks: yes` is `open` |
| `duplicate ID …` | an `R-`, `OP-` or `E-` ID is declared twice |
| `unknown ID …` | an `R-` or `OP-` ID is referenced but no table row declares it. Only references are read: the ID, Affects, Resolved by, Note, Requirement, Covers and Depends columns, and text outside double quotes. Quoted source text is never scanned |
| `OP-… is resolved but names no DoU` / `names dou-NNN, which does not exist` | a resolved open point needs an existing `dou-NNN.md` |
| `… has status …` / `… has Blocks …` | an open point's Status is not `open` or `resolved`, or Blocks is not `yes` or `no` |

The epic rules apply only when `epics.md` exists, so `check` on a folder with no epics file passes while blocking
open points are open. That is how to run it before splitting: a pass means the analysis itself is consistent,
not that epics may be written. Whether epics may be written is the blocking-open-point rule in `SKILL.md`.
