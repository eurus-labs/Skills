# The `analysis.md` format

`split-epics` reads a topic folder (`requirements/<topic>/` by default). `analyze-requirements` in the
`reasoning` plugin writes it; an analysis written by hand works if it has the same shape. The script
`scripts/requirements.py check` reads the tables below by their column names, so a hand-written file must keep
them. Never edit any of these files from `split-epics`.

```
requirements/<topic>/
  analysis.md     read: the Changes table and the Open points table
  dou-001.md      read: the decisions that resolved an open point (one file per PO discussion)
  epics.md        written by split-epics
```

## Sections of `analysis.md`

| Section | What it holds | What `split-epics` uses it for |
| ------- | ------------- | ------------------------------ |
| `## Sources` | One row per role (current requirement, previous requirement, code): repository, ref, commit, local path, path in repository | Where the `path:line` citations point |
| `## Changes` | One row per requirement | The requirements to place in epics |
| `## Findings` | Per requirement, the problems that stop it being built or tested | Risks for an epic |
| `## Open points` | Questions for the Product Owner (PO) | Whether epics may be written at all |
| `## Assumptions` | What was assumed, with an owner and the risk | Risks for an epic |
| `## Revision history` | One line per update, newest last | Not read |

## The Changes table

```markdown
| ID | Status | Scope | Previous (path:line) | Current (path:line) | Code impact | Note |
| -- | ------ | ----- | -------------------- | ------------------- | ----------- | ---- |
| R-001 | changed | in | "..." `v1.md:10` | "..." `v2.rst:13` | changes existing behavior: `src/exporter.py:8` | |
```

- **ID** is `R-001`, `R-002`, and so on. An ID is never reused.
- **Status** is `added`, `removed`, `changed`, `unchanged`, `unchanged (wording)` or `superseded`. A
  `superseded` row was replaced by a later row, named in its Note; place the replacement, not the old row.
- **Scope** starts with `in` for a requirement that needs work, or `out` followed by the reason. Every `in`
  row goes in exactly one epic or in "Not in any epic". An `out` row is not placed anywhere.
- **Code impact** is `new`, `changes existing behavior`, `already met` or `not checked`, with `path:line`. Use
  it for an epic's code areas, and for a "Not in any epic" reason when the impact is `already met`.

## The Open points table

```markdown
| ID | Question for the PO | Affects | Blocks | Status | Resolved by |
| -- | ------------------- | ------- | ------ | ------ | ----------- |
| OP-001 | Is 100 the new limit for every user? | R-001 | yes | resolved | dou-001 |
```

- **Blocks** is `yes` or `no`. **Status** is `open` or `resolved`. **Resolved by** names an existing
  `dou-NNN.md` for a resolved point, and is `—` while it is open.
- A blocking open point is one with Blocks `yes` and Status `open`. While one exists, epics are not written,
  unless the user explicitly asks for provisional ones.

## When the file does not fit

If `analysis.md` is missing or has no Changes table, or `check` reports a duplicated ID, an unknown ID or a bad status, stop and
report the line. Do not repair the analysis and do not guess what a requirement meant. The usual way to make or
fix an analysis is `analyze-requirements` in the `reasoning` plugin.
