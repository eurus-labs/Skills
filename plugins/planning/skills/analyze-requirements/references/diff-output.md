# `requirements.py diff` output

`check` is described in `formats.md`.

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
