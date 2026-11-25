#!/usr/bin/env python3
"""Compare two versions of a requirement, and check a requirement-analysis folder.

    requirements.py diff <previous> <current> [--changes-only]
    requirements.py check <topic-folder>

`diff` splits each file into units (headings, list items, paragraphs, table rows), matches
the units of the two versions and prints one JSON object: each unit is `added`, `removed`,
`changed`, `moved` or `unchanged`, with its file and 1-based line range. It decides what differs,
not what the difference means; the caller reads every non-`unchanged` unit.

`check` reads analysis.md, dou-*.md and epics.md in a folder and prints one line per
broken rule, `file:line: message`. Exit 0 when consistent, 1 when a rule is broken,
2 on a usage error.

Standard library only. Reads only the files it is given; makes no network call; writes nothing.
"""

import difflib
import glob
import json
import os
import re
import sys

MD_EXT = (".md", ".markdown")
RST_EXT = (".rst",)
TXT_EXT = (".txt",)

# An item marker: -, *, +, 1., 1), 3.1.2, 3.1), or rst's #.
ITEM_RE = re.compile(r"^(\s*)((?:[-*+]|\d+(?:\.\d+)+[.)]?|\d+[.)]|#\.))\s+(\S.*)$")
ATX_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
ROW_RE = re.compile(r"^\s*\|.*\|\s*$")
ROW_SEP_RE = re.compile(r"^\s*\|[\s:|-]+\|\s*$")
# An explicit requirement ID at the start of a unit, such as REQ-12 or FR-3.
KEY_RE = re.compile(r"\b[A-Z][A-Za-z]{0,5}-\d+\b")
SIMILARITY_MIN = 0.6


class UsageError(Exception):
    pass


def file_format(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in MD_EXT:
        return "md"
    if ext in RST_EXT:
        return "rst"
    if ext in TXT_EXT:
        return "txt"
    raise UsageError("%s: unsupported format; use .md, .rst or .txt (export other formats to text first)"
                     % path)


def read_lines(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read().splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise UsageError("%s: cannot read (%s)" % (path, exc))


def underline_char(line, fmt):
    """The character of a heading underline, or None."""
    s = line.strip()
    if len(s) < 3 or len(set(s)) != 1:
        return None
    allowed = "=-" if fmt == "md" else "=-~^\"'`#*+:._"
    return s[0] if s[0] in allowed else None


def split_units(lines, fmt):
    """Split a document into units, each with kind, section, 1-based line range and text."""
    units = []
    sections = []          # (level, title)
    styles = []            # rst/setext heading styles in order of first appearance
    cur = None
    blank_before = False
    in_fence = False
    i = 0

    def section_path():
        return " > ".join(t for _, t in sections)

    def flush():
        nonlocal cur
        if cur:
            cur["text"] = " ".join(s.strip() for s in cur.pop("raw")).strip()
            units.append(cur)
        cur = None

    def start(kind, lineno, text, indent=0, content_indent=0):
        nonlocal cur
        flush()
        cur = {"kind": kind, "section": section_path(), "start": lineno, "end": lineno,
               "raw": [text], "indent": indent, "content_indent": content_indent}

    def heading(level_key, title, first, last):
        flush()
        if level_key not in styles:
            styles.append(level_key)
        level = styles.index(level_key) + 1
        while sections and sections[-1][0] >= level:
            sections.pop()
        sections.append((level, title))
        units.append({"kind": "heading", "section": section_path(), "start": first, "end": last,
                      "text": title})

    if fmt == "md" and lines and lines[0].strip() == "---":
        for j in range(1, len(lines)):           # skip YAML front matter
            if lines[j].strip() == "---":
                i = j + 1
                break

    while i < len(lines):
        line = lines[i]
        lineno = i + 1
        if in_fence:
            cur["raw"].append(line)
            cur["end"] = lineno
            if FENCE_RE.match(line):
                in_fence = False
            i += 1
            continue
        if not line.strip():
            blank_before = True
            i += 1
            continue
        if FENCE_RE.match(line) and fmt != "txt":
            start("code", lineno, line)
            in_fence = True
            blank_before = False
            i += 1
            continue
        if fmt != "txt":
            m = ATX_RE.match(line) if fmt == "md" else None
            if m:
                heading(("atx", len(m.group(1))), m.group(2), lineno, lineno)
                blank_before = False
                i += 1
                continue
            # rst overline + title + underline
            if fmt == "rst" and underline_char(line, fmt) and i + 2 < len(lines) \
                    and lines[i + 1].strip() and lines[i + 2].strip() == line.strip():
                heading((line.strip()[0], True), lines[i + 1].strip(), lineno, lineno + 2)
                blank_before = False
                i += 3
                continue
            # title + underline
            if i + 1 < len(lines) and not ITEM_RE.match(line) and not ROW_RE.match(line):
                u = underline_char(lines[i + 1], fmt)
                if u and not underline_char(line, fmt) \
                        and (cur is None or blank_before or cur["kind"] == "heading"):
                    heading((u, False), line.strip(), lineno, lineno + 1)
                    blank_before = False
                    i += 2
                    continue
        if fmt == "md" and ROW_RE.match(line):
            flush()
            if not ROW_SEP_RE.match(line):
                start("row", lineno, line)
            blank_before = False
            i += 1
            continue
        m = ITEM_RE.match(line)
        if m:
            start("item", lineno, m.group(3), indent=len(m.group(1)),
                  content_indent=len(m.group(1)) + len(m.group(2)) + 1)
            cur["marker"] = m.group(2)
            blank_before = False
            i += 1
            continue
        indent = len(line) - len(line.lstrip())
        if cur and cur["kind"] in ("item", "paragraph") and cur["end"] + 1 == lineno:
            cur["raw"].append(line)
            cur["end"] = lineno
        elif cur and cur["kind"] == "item" and blank_before and indent >= cur["content_indent"]:
            cur["raw"].append(line)
            cur["end"] = lineno
        else:
            start("paragraph", lineno, line)
        blank_before = False
        i += 1
    flush()
    for u in units:
        u.pop("indent", None)
        u.pop("content_indent", None)
    return units


CODE_SPAN_RE = re.compile(r"(`+)(.+?)\1")
EMPHASIS_RES = (
    re.compile(r"(?<![\w*])(\*\*|\*)(?=\S)(.+?)(?<=\S)\1(?![\w*])"),
    re.compile(r"(?<![\w_])(__|_)(?=\S)(.+?)(?<=\S)\1(?![\w_])"),
)


def normalize(text):
    """Text with formatting removed, so the same sentence in .md and .rst compares equal.

    Only formatting goes: whitespace runs, the delimiters of inline code, and emphasis marks around
    words. Case, punctuation and the content of inline code stay, so a changed glob, a lower-cased
    status or a dropped full stop is still a difference."""
    out = []
    pos = 0
    for m in CODE_SPAN_RE.finditer(text):
        out.append(strip_emphasis(text[pos:m.start()]))
        out.append(m.group(2).strip())
        pos = m.end()
    out.append(strip_emphasis(text[pos:]))
    return re.sub(r"\s+", " ", "".join(out)).strip()


def strip_emphasis(text):
    for pattern in EMPHASIS_RES:
        text = pattern.sub(r"\2", text)
    return re.sub(r"\\([^\w\s])", r"\1", text)


def unit_key(unit):
    m = KEY_RE.search(unit["text"][:40])
    return m.group(0) if m else None


def match_units(prev, cur):
    """Pair previous and current units. Returns {prev_index: cur_index}."""
    pairs = {}
    used_cur = set()
    pn = [normalize(u["text"]) for u in prev]
    cn = [normalize(u["text"]) for u in cur]

    def take(pi, ci):
        pairs[pi] = ci
        used_cur.add(ci)

    # 1. identical text in the same section, then identical text anywhere (a moved unit).
    for same_section in (True, False):
        for pi, pu in enumerate(prev):
            if pi in pairs:
                continue
            for ci, cu in enumerate(cur):
                if ci in used_cur or pu["kind"] != cu["kind"] or pn[pi] != cn[ci]:
                    continue
                if same_section and pu["section"] != cu["section"]:
                    continue
                take(pi, ci)
                break
    # 2. the same explicit ID on both sides, once on each side.
    pkeys, ckeys = {}, {}
    for pi, pu in enumerate(prev):
        if pi not in pairs and unit_key(pu):
            pkeys.setdefault(unit_key(pu), []).append(pi)
    for ci, cu in enumerate(cur):
        if ci not in used_cur and unit_key(cu):
            ckeys.setdefault(unit_key(cu), []).append(ci)
    for key, pis in pkeys.items():
        cis = ckeys.get(key, [])
        if len(pis) == 1 and len(cis) == 1:
            take(pis[0], cis[0])
    # 3. the most similar remaining pairs of the same kind.
    scored = []
    for pi, pu in enumerate(prev):
        if pi in pairs:
            continue
        for ci, cu in enumerate(cur):
            if ci in used_cur or pu["kind"] != cu["kind"]:
                continue
            short, long_ = sorted((pn[pi], cn[ci]), key=len)
            if len(short) >= 15 and short in long_:
                ratio = 0.8        # one text extends the other: the same requirement, reworded
            else:
                sm = difflib.SequenceMatcher(None, pn[pi], cn[ci], autojunk=False)
                if sm.real_quick_ratio() < SIMILARITY_MIN or sm.quick_ratio() < SIMILARITY_MIN:
                    continue
                ratio = sm.ratio()
            if ratio >= SIMILARITY_MIN:
                bonus = 0.05 if pu["section"] == cu["section"] else 0.0
                scored.append((ratio + bonus, ratio, pi, ci))
    for _, _, pi, ci in sorted(scored, key=lambda s: (-s[0], s[2], s[3])):
        if pi not in pairs and ci not in used_cur:
            take(pi, ci)
    return pairs


def side(path, unit):
    return {"path": path, "lines": [unit["start"], unit["end"]], "text": unit["text"]}


def diff(prev_path, cur_path, changes_only=False):
    pfmt, cfmt = file_format(prev_path), file_format(cur_path)
    prev = split_units(read_lines(prev_path), pfmt)
    cur = split_units(read_lines(cur_path), cfmt)
    pairs = match_units(prev, cur)
    matched_cur = {ci: pi for pi, ci in pairs.items()}

    # A removed unit is listed after the current unit that matches its nearest matched predecessor.
    removed_after = {}
    anchor = -1
    for pi, pu in enumerate(prev):
        if pi in pairs:
            anchor = pairs[pi]
        else:
            removed_after.setdefault(anchor, []).append(pi)

    entries = []

    def removed_entries(anchor_index):
        for pi in removed_after.get(anchor_index, []):
            entries.append({"status": "removed", "kind": prev[pi]["kind"], "section": prev[pi]["section"],
                            "previous": side(prev_path, prev[pi]), "current": None})

    removed_entries(-1)
    for ci, cu in enumerate(cur):
        if ci not in matched_cur:
            entries.append({"status": "added", "kind": cu["kind"], "section": cu["section"],
                            "previous": None, "current": side(cur_path, cu)})
        else:
            pu = prev[matched_cur[ci]]
            same = normalize(pu["text"]) == normalize(cu["text"])
            moved = pu["section"] != cu["section"]
            status = "changed" if not same else ("moved" if moved else "unchanged")
            entry = {"status": status, "kind": cu["kind"], "section": cu["section"],
                     "previous": side(prev_path, pu), "current": side(cur_path, cu)}
            if not same:
                entry["similarity"] = round(difflib.SequenceMatcher(
                    None, normalize(pu["text"]), normalize(cu["text"]), autojunk=False).ratio(), 2)
            if moved:
                entry["previous_section"] = pu["section"]
            entries.append(entry)
        removed_entries(ci)

    counts = {k: sum(1 for e in entries if e["status"] == k)
              for k in ("added", "removed", "changed", "moved", "unchanged")}
    if changes_only:
        entries = [e for e in entries if e["status"] != "unchanged"]
    return {"previous": {"path": prev_path, "format": pfmt, "units": len(prev)},
            "current": {"path": cur_path, "format": cfmt, "units": len(cur)},
            "summary": counts, "units": entries}


# --- check ---------------------------------------------------------------------------------

ID_RE = re.compile(r"\b(?:R|OP)-\d+\b")
R_RE = re.compile(r"\bR-\d+\b")
OP_RE = re.compile(r"\bOP-\d+\b")
EPIC_HEAD_RE = re.compile(r"^##\s+(E-\d+)\b")
DOU_RE = re.compile(r"\bdou-(\d+)\b", re.I)


def split_row(line):
    s = line.strip()
    if not (s.startswith("|") and s.endswith("|")):
        return None
    cells = re.split(r"(?<!\\)\|", s[1:-1])
    return [c.strip() for c in cells]


def read_text(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read().splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise UsageError("%s: cannot read (%s)" % (path, exc))


def parse_tables(lines):
    """Yield (lineno, header-map, cells) for each table row whose first cell is an ID."""
    header = None
    rows = []
    for n, line in enumerate(lines, 1):
        cells = split_row(line)
        if cells is None:
            header = None
            continue
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c) and any(cells):
            continue
        if header is None:
            header = {c.lower(): k for k, c in enumerate(cells)}
            continue
        rows.append((n, header, cells))
    return rows


def column(header, cells, *names):
    for key, idx in header.items():
        if any(key.startswith(n) for n in names) and idx < len(cells):
            return cells[idx]
    return None


def check(folder):
    if not os.path.isdir(folder):
        raise UsageError("%s: not a folder" % folder)
    problems = []

    def fail(path, line, message):
        problems.append((os.path.basename(path), line, message))

    analysis_path = os.path.join(folder, "analysis.md")
    if not os.path.isfile(analysis_path):
        raise UsageError("%s: analysis.md not found" % folder)
    alines = read_text(analysis_path)
    dou_files = sorted(glob.glob(os.path.join(folder, "dou-*.md")))
    dou_ids = {re.match(r"dou-(\d+)\.md$", os.path.basename(p), re.I).group(1)
               for p in dou_files if re.match(r"dou-(\d+)\.md$", os.path.basename(p), re.I)}
    dou_ids = {d.lstrip("0") or "0" for d in dou_ids}

    reqs, ops = {}, {}          # id -> (line, fields)
    for n, header, cells in parse_tables(alines):
        first = cells[0] if cells else ""
        if R_RE.fullmatch(first):
            if first in reqs:
                fail(analysis_path, n, "duplicate ID %s (first at line %d)" % (first, reqs[first][0]))
                continue
            reqs[first] = (n, {"scope": column(header, cells, "scope") or ""})
        elif OP_RE.fullmatch(first):
            if first in ops:
                fail(analysis_path, n, "duplicate ID %s (first at line %d)" % (first, ops[first][0]))
                continue
            status = (column(header, cells, "status") or "").strip().lower()
            blocks = (column(header, cells, "block") or "").strip().lower()
            resolved_by = column(header, cells, "resolved by", "dou") or ""
            if status.split(" ")[0] not in ("open", "resolved"):
                fail(analysis_path, n, "%s has status '%s'; use open or resolved" % (first, status))
            if blocks.split(" ")[0] not in ("yes", "no"):
                fail(analysis_path, n, "%s has Blocks '%s'; use yes or no" % (first, blocks))
            ops[first] = (n, {"status": status.split(" ")[0], "blocking": blocks.startswith("yes"),
                              "resolved_by": resolved_by})

    for op, (n, f) in ops.items():
        if f["status"] != "resolved":
            continue
        named = DOU_RE.findall(f["resolved_by"])
        if not named:
            fail(analysis_path, n, "%s is resolved but names no DoU" % op)
        for num in named:
            if (num.lstrip("0") or "0") not in dou_ids:
                fail(analysis_path, n, "%s names dou-%s, which does not exist in the folder" % (op, num))

    def unknown_ids(path, lines):
        for n, line in enumerate(lines, 1):
            for tok in ID_RE.findall(line):
                known = reqs if tok.startswith("R-") else ops
                if tok not in known:
                    fail(path, n, "unknown ID %s" % tok)

    unknown_ids(analysis_path, alines)
    for path in dou_files:
        unknown_ids(path, read_text(path))

    epics_path = os.path.join(folder, "epics.md")
    if os.path.isfile(epics_path):
        elines = read_text(epics_path)
        unknown_ids(epics_path, elines)
        epic_ids = {}
        covered = {}               # R-id -> epic id
        current = None
        not_in = False
        not_in_ids = set()
        for n, line in enumerate(elines, 1):
            head = re.match(r"^(#{1,6})\s+(.*)", line)
            if head:
                not_in = bool(re.match(r"not in any epic", head.group(2).strip(), re.I))
                m = EPIC_HEAD_RE.match(line)
                if m:
                    current = m.group(1)
                    if current in epic_ids:
                        fail(epics_path, n, "duplicate ID %s (first at line %d)" % (current, epic_ids[current]))
                    else:
                        epic_ids[current] = n
                else:
                    current = None
                continue
            if not_in:
                not_in_ids.update(R_RE.findall(line))
            elif current and re.match(r"^\W*covers\b", line, re.I):
                for rid in R_RE.findall(line):
                    if rid in covered and covered[rid] != current:
                        fail(epics_path, n, "%s is in both %s and %s" % (rid, covered[rid], current))
                    covered.setdefault(rid, current)
        for rid, (n, f) in reqs.items():
            if f["scope"].strip().lower().startswith("in") and rid not in covered and rid not in not_in_ids:
                fail(analysis_path, n, "in-scope requirement %s is in no epic and not in the "
                                       "'Not in any epic' list" % rid)
        provisional = False
        for line in elines:
            if line.startswith("# "):
                provisional = "provisional" in line.lower()
                break
        if not provisional:
            for op, (n, f) in ops.items():
                if f["blocking"] and f["status"] == "open":
                    fail(epics_path, 1, "epics are not marked Provisional while blocking open point %s "
                                        "is open (analysis.md:%d)" % (op, n))
    return problems, {"requirements": len(reqs), "open_points": len(ops), "dous": len(dou_files),
                      "epics": os.path.isfile(epics_path)}


def main(argv):
    if len(argv) >= 2 and argv[1] == "diff":
        args = [a for a in argv[2:] if a != "--changes-only"]
        if len(args) != 2:
            raise UsageError("usage: requirements.py diff <previous> <current> [--changes-only]")
        json.dump(diff(args[0], args[1], "--changes-only" in argv[2:]), sys.stdout, indent=2,
                  ensure_ascii=False)
        sys.stdout.write("\n")
        return 0
    if len(argv) == 3 and argv[1] == "check":
        problems, stats = check(argv[2])
        for name, line, message in problems:
            print("FAIL %s:%d: %s" % (name, line, message))
        if problems:
            print("%d problem(s)." % len(problems))
            return 1
        print("OK %d requirement(s), %d open point(s), %d DoU file(s)%s"
              % (stats["requirements"], stats["open_points"], stats["dous"],
                 ", epics.md present" if stats["epics"] else ""))
        return 0
    raise UsageError("usage: requirements.py diff <previous> <current> [--changes-only] | "
                     "check <topic-folder>")


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except UsageError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)
