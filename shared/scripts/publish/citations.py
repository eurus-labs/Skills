#!/usr/bin/env python3
"""Where a block's citations live: in `evidence`, shown in the audit edition only.

A reader of the documentation wants prose; an auditor wants to know which lines each
paragraph rests on. Both come from one rendered source. Every block that rests on source
lines is followed, in the rendered RST or MyST, by a Sphinx `only` block that names them:

    .. only:: audit            (RST)          ```{only} audit        (MyST)

A normal Sphinx build is the **reader edition** and omits those blocks. `sphinx-build -t
audit` is the **audit edition** and shows each one. Nothing is rendered twice and nothing is
stored twice, so the two editions cannot disagree about what a block says.

This module is what the renderer, the prose check and the edition check share, so that
"what counts as a citation" is decided once:

    CITATION        the `path:line` or `path:start-end` pattern
    of_block        the citations a block rests on, from its own `evidence` and from the
                    claims and statements it refers to
    strip_inline    the citations generator prose carries inside its sentences, so the
                    reader edition shows clean text while the audit edition keeps them
    split_columns   a table's location column, so the reader edition drops the column and
                    the audit edition lists each row's location

Standard library only. No I/O.
"""

import re

# A source path, a colon and a line or line range. A path with a directory in it is a path
# whatever its extension; a bare file name needs a source-like extension, so a host and
# port (`example.com:8080`) and a clock time are not mistaken for one.
_NAME = r"[\w@+~-][\w.@+~-]*"
_EXT = (r"(?:py|pyi|js|jsx|mjs|cjs|ts|tsx|go|rs|java|kt|rb|c|h|cc|cpp|hpp|cs|php|sh|bash|"
        r"sql|md|rst|txt|json|jsonl|ya?ml|toml|ini|cfg|conf|html|css|scss|xml|lock|mk|"
        r"gradle|swift|scala|lua|pl|ex|exs)")
CITATION_SOURCE = (r"(?<![\w./@+~-])(?:(?:%s/)+%s\.\w+|%s\.%s):\d+(?:-\d+)?(?![\w:])"
                   % (_NAME, _NAME, _NAME, _EXT))
CITATION = re.compile(CITATION_SOURCE)

# `(observed src/a.py:3, src/b.py:9)`, `(Inferred from ...)`, `(src/a.py:3)`: the
# parenthetical a generated sentence ends with.
_PARENTHETICAL = re.compile(
    r"\s*\((?:[A-Za-z][A-Za-z ]*? )?%s(?:,\s*%s)*\)" % (CITATION_SOURCE, CITATION_SOURCE))
# The paragraph a composed manual section ends with when it lists its sources.
_SOURCE_PARAGRAPH = re.compile(r"(?:\n\n|^)Source code: [^\n]*(?:\n(?!\n)[^\n]*)*")


def format_item(item):
    """One `evidence` record as `path:line` or `path:start-end`; '' when it has no path."""
    if not isinstance(item, dict) or not item.get("path"):
        return ""
    start, end = item.get("line_start"), item.get("line_end", item.get("line_start"))
    if not isinstance(start, int):
        return str(item["path"])
    if isinstance(end, int) and end != start:
        return "%s:%d-%d" % (item["path"], start, end)
    return "%s:%d" % (item["path"], start)


def block_text(block):
    """Every string in a block a reader reads: its prose, column headers and cells."""
    parts = [block.get("text", "")]
    parts.extend(str(column) for column in block.get("columns", ()) or ())
    for row in block.get("rows", ()) or ():
        parts.extend(str(cell) for cell in row)
    return "\n".join(p for p in parts if p)


def inline_in(text):
    """The citations written into a string, in order of appearance."""
    return [m.group(0) for m in CITATION.finditer(str(text or ""))]


def strip_inline(text):
    """`(clean text, [citations removed])` for a block's prose.

    Removes only the two shapes the generators write -- a trailing parenthetical and a
    `Source code:` paragraph -- and leaves any other `path:line` in a sentence alone, which
    the edition check then reports instead of this function quietly rewording a sentence.
    """
    removed = []

    def take(match):
        removed.extend(inline_in(match.group(0)))
        return ""

    clean = _SOURCE_PARAGRAPH.sub(take, str(text or ""))
    clean = _PARENTHETICAL.sub(take, clean)
    return clean.rstrip(), removed


def of_block(block, claims=None, statements=None):
    """The citations a block rests on, deduplicated, in the order they are first met.

    Its own `evidence` first, then the evidence of each claim and statement it refers to,
    then any citation written into its text. A block with none returns an empty list and
    gets no audit entry: there is nothing to show.
    """
    claims, statements = claims or {}, statements or {}
    found = [format_item(item) for item in block.get("evidence") or ()]
    for ref in block.get("claim_refs") or ():
        found.extend(format_item(i) for i in (claims.get(ref) or {}).get("evidence") or ())
    for ref in block.get("analysis_refs") or ():
        found.extend(format_item(i) for i in (statements.get(ref) or {}).get("evidence") or ())
    found.extend(inline_in(block_text(block)))
    seen, out = set(), []
    for citation in found:
        if citation and citation not in seen:
            seen.add(citation)
            out.append(citation)
    return out


def is_location(cell):
    """Whether a table cell is nothing but one citation, or an empty marker beside one."""
    text = str(cell).strip()
    return bool(CITATION.fullmatch(text))


def location_columns(columns, rows):
    """Indices of the columns that hold only locations: every cell a citation or `-`.

    A column needs at least one real citation to count, and the table needs at least one
    other column to keep -- a table that is all locations is left as it is, because
    dropping everything would leave the reader an empty table.
    """
    found = []
    for position in range(len(columns)):
        cells = [str(row[position]).strip() for row in rows if position < len(row)]
        real = [c for c in cells if c not in ("", "-")]
        if real and all(is_location(c) for c in real):
            found.append(position)
    return found if len(found) < len(columns) else []


def split_columns(columns, rows):
    """`(columns, rows, locations)` with location columns removed.

    `locations` is one entry per row: `(label, [citations])`, the label being the row's
    remaining cells, so the audit edition can say which row each location belongs to.
    """
    drop = location_columns(columns, rows)
    if not drop:
        return list(columns), [list(r) for r in rows], []
    keep = [i for i in range(len(columns)) if i not in drop]
    kept_rows = [[row[i] for i in keep if i < len(row)] for row in rows]
    locations = []
    for row, kept in zip(rows, kept_rows):
        cites = [str(row[i]).strip() for i in drop
                 if i < len(row) and is_location(row[i])]
        if cites:
            locations.append((" / ".join(str(c) for c in kept), cites))
    return [columns[i] for i in keep], kept_rows, locations
