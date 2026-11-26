# `requirements.py` output

## `diff <previous> <current> [--changes-only]`

Prints one JSON object. The file extension picks the splitter: `.md` and `.markdown`, `.rst`, or `.txt`.

| Field | Meaning |
| ----- | ------- |
| `previous`, `current` | `path`, `format` and the number of `units` found in each file |
| `summary` | counts of `added`, `removed`, `changed`, `moved` and `unchanged` units |
| `units[]` | one entry per unit, in the order of the current file; a removed unit follows the unit that matched its nearest earlier neighbour |

A unit entry:

| Field | Meaning |
| ----- | ------- |
| `status` | `added`, `removed`, `changed`, `moved` (the same text under a different section) or `unchanged` |
| `kind` | `heading`, `item` (a bulleted or numbered item), `paragraph`, `row` (a Markdown table row) or `code` |
| `section` | the headings above the unit, joined with ` > ` |
| `previous`, `current` | `{path, lines: [first, last], text}`, or `null` on the side where the unit does not exist; lines are 1-based |
| `similarity` | on `changed` only: how alike the two texts are, 0 to 1 |
| `previous_section` | on a `moved` unit, or a `changed` unit that also changed section: the section it was under before; `section` is the new one |

How units are matched, in order: identical text in the same section, identical text anywhere, the same
explicit ID (such as `REQ-12`) once on each side, then the most similar pairs of the same kind (similarity of
at least 0.6, or one text contained in the other). Text is compared after removing formatting only: list
markers, heading underlines, whitespace runs, the delimiters of inline code, and emphasis marks around words.
The same sentence in `.md` and `.rst` therefore compares equal. Case, punctuation and the content of inline
code are kept, so a changed number, glob, word, capital letter or full stop makes the unit `changed`.

The script decides what differs, not what it means. A `changed` unit may be a rewording, a real change, or two
different requirements paired by similarity; read both texts.

## `check <topic-folder>`

Reads `analysis.md`, `dou-*.md` and `epics.md`. Prints `FAIL <file>:<line>: <message>` per broken rule, then the
count, and exits 1; prints `OK …` and exits 0 when consistent. Exit 2 means a usage error: a missing folder or
`analysis.md`, an unreadable file.

| Message | Rule |
| ------- | ---- |
| `duplicate ID …` | an `R-`, `OP-` or `E-` ID is declared twice |
| `unknown ID …` | an `R-` or `OP-` ID is referenced but no table row declares it. Only references are read: the ID, Affects, Resolved by, Note, Requirement, Covers and Depends columns, and text outside double quotes. Quoted source text, and the Previous and Current columns, are never scanned |
| `OP-… is resolved but names no DoU` / `names dou-NNN, which does not exist` | a resolved open point needs an existing `dou-NNN.md` |
| `in-scope requirement … is in no epic …` | a row whose Scope starts with `in` is in no epic's `Covers:` line and not in the "Not in any epic" list |
| `… is in both E-01 and E-02` | a requirement is covered by two epics |
| `epics are not marked Provisional while blocking open point …` | `epics.md` exists, its title lacks `Provisional`, and an open point with `Blocks: yes` is `open` |
| `… has status …` / `… has Blocks …` | an open point's Status is not `open` or `resolved`, or Blocks is not `yes` or `no` |
