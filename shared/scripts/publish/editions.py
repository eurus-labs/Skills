#!/usr/bin/env python3
"""Check that the reader edition and the audit edition tell the same story.

    import editions
    verdict = editions.check(out_dir, doc, ".rst", extensions)

The rendered RST or MyST is one source for both editions. A normal Sphinx build is the
reader edition and must show no `path:line` at all; `sphinx-build -t audit` is the audit
edition and must show every cited block's citations. Two things keep that honest, and this
checks both:

    the reader source holds no `path:line`    everything cited sits inside an `only`
                                              audit block, which the reader build drops
    every cited block has its audit block     a block that rests on source lines is
                                              followed by an audit block naming each one

The first runs on the source and needs nothing installed. When `sphinx-build` is present,
both are repeated on real plain-text builds, which is the check that cannot be fooled by how
the source happens to be written. The audit edition is built here only to be compared and is
never kept.

Only the pages generated from `doc.json` are checked. An authored-page scaffold is a brief
for a person, replaced before publication, and carries its evidence in a table by design.

Standard library only. Reads; writes nothing.
"""

import os
import re

import citations
import sphinx_support

# `.. only:: audit` and everything indented under it; a fenced MyST `{only}` block.
_RST_AUDIT = re.compile(r"^\.\. only:: audit[ \t]*$")
_MYST_AUDIT = re.compile(r"^```\{only\} audit[ \t]*\n.*?^```[ \t]*$",
                         re.MULTILINE | re.DOTALL)


def split_editions(text, extension):
    """`(reader source, [audit block, ...])` for one rendered page."""
    if extension == ".md":
        blocks = [m.group(0) for m in _MYST_AUDIT.finditer(text)]
        return _MYST_AUDIT.sub("", text), blocks
    reader, blocks, current = [], [], None
    for line in text.splitlines():
        if current is not None:
            if not line.strip() or line[:1] in (" ", "\t"):
                current.append(line)
                continue
            blocks.append("\n".join(current))
            current = None
        if _RST_AUDIT.match(line):
            current = [line]
        else:
            reader.append(line)
    if current is not None:
        blocks.append("\n".join(current))
    return "\n".join(reader), blocks


def expected_for(page, context):
    """`(blocks that must carry an audit block, citations that must appear)` for a page."""
    claims, statements = context.get("claims"), context.get("statements")
    blocks, wanted = 0, []
    for block in page.get("blocks", ()):
        kind = block.get("type")
        if kind == "prose":
            found = citations.of_block(block, claims, statements)
        elif kind == "table":
            columns, rows, located = citations.split_columns(block["columns"], block["rows"])
            found = citations.of_block(dict(block, columns=columns, rows=rows), claims,
                                       statements)
            found = found + [c for _label, cites in located for c in cites]
        else:
            continue
        if found:
            blocks += 1
            wanted.extend(found)
    return blocks, wanted


def check(out_dir, doc, extension, extensions=(), context=None, build=True):
    """`{"status", "detail", "problems"}` for the generated pages under `out_dir`.

    `build=False` checks the source only, for a caller that must not start Sphinx.
    """
    context = context or {}
    problems, checked, cited_blocks = [], 0, 0
    reader_files, wanted_by_file = {}, {}
    for page in doc.get("pages", ()):
        name = page["id"] + extension
        path = os.path.join(out_dir, name)
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        checked += 1
        reader, audit = split_editions(text, extension)
        reader_files[name] = page["id"]
        for leaked in sorted(set(citations.inline_in(reader)))[:5]:
            problems.append("%s: the reader edition cites %s outside an audit block"
                            % (name, leaked))
        # A diagram is shown in both editions, so its source is reader source: a
        # `path:line` in an arrow label or a comment is a leak the page text cannot show.
        for block in page.get("blocks", ()):
            if block.get("type") != "plantuml":
                continue
            source = os.path.join(out_dir, "_diagrams", os.path.basename(block["src"]))
            if not os.path.isfile(source):
                continue
            with open(source, encoding="utf-8", errors="replace") as fh:
                for leaked in sorted(set(citations.inline_in(fh.read())))[:5]:
                    problems.append("%s: the diagram %s cites %s; the reader edition "
                                    "shows a diagram as drawn" % (name, block["src"], leaked))
        blocks, wanted = expected_for(page, context)
        cited_blocks += blocks
        wanted_by_file[name] = wanted
        joined = "\n".join(audit)
        if len(audit) < blocks:
            problems.append("%s: %d block(s) cite source lines but only %d audit block(s) "
                            "follow" % (name, blocks, len(audit)))
        for citation in sorted(set(wanted)):
            if citation not in joined:
                problems.append("%s: no audit block names %s" % (name, citation))
                break
    status = "failed" if problems else "passed"
    detail = ("%d generated page(s), %d cited block(s); reader source clean, audit "
              "blocks present" % (checked, cited_blocks)) if not problems else (
                  "%d problem(s) in the source" % len(problems))

    built = sphinx_support.build_text(out_dir, extensions) if checked and build else None
    if not build:
        pass
    elif built is None:
        detail += "; no Sphinx build was run (sphinx-build is not installed)"
    elif "" in built:
        detail += "; the reader build could not be read: %s" % built[""]
    else:
        audit_built = sphinx_support.build_text(out_dir, extensions, ("audit",)) or {}
        for name in sorted(reader_files):
            page_key = name.rsplit(".", 1)[0] + ".txt"
            for leaked in sorted(set(citations.inline_in(built.get(page_key, ""))))[:5]:
                problems.append("%s: the reader build shows %s" % (page_key, leaked))
            shown = audit_built.get(page_key, "")
            for citation in sorted(set(wanted_by_file.get(name, ()))):
                if citation not in shown:
                    problems.append("%s: the audit build does not show %s"
                                    % (page_key, citation))
                    break
        status = "failed" if problems else "passed"
        detail += "; confirmed on a reader build and an audit build"
    return {"status": status, "detail": detail, "problems": problems}
