#!/usr/bin/env python3
"""Every eval file's YAML frontmatter must parse.

`claude plugin eval` reads each case's prompt.md and each grader as `---` frontmatter plus a
body. A plain (unquoted) value that holds `: ` or ` #`, or a quote that is not closed, is a YAML
error, and the runner refuses to load that case. The repository's own validator reads
frontmatter with a line parser that accepts all of those, so it cannot catch this. Nine
descriptions shipped that way and four cases failed to load on the first real run.

The check below is stdlib only, so it runs everywhere; with PyYAML installed it also runs the
real parser over every file.

    python3 tools/test_eval_frontmatter.py
"""

import glob
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILURES = []


def check(name, condition, detail=""):
    if condition:
        print("ok   %s" % name)
    else:
        print("FAIL %s %s" % (name, detail))
        FAILURES.append(name)


def frontmatter(text):
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    return m.group(1) if m else None


def problem(line):
    """What is wrong with one top-level `key: value` line, or None. Covers the plain, single- and
    double-quoted scalars the eval files use; flow collections are left to the real parser."""
    m = re.match(r"([A-Za-z_][\w-]*):(?: +(.*))?$", line)
    if not m or m.group(2) is None:
        return None
    value = m.group(2).rstrip()
    if value[:1] in ("[", "{", "|", ">", "&", "*", "!", "%", "@", "`"):
        return None
    if value[:1] == "'":
        inner = value[1:-1] if value.endswith("'") and len(value) > 1 else None
        if inner is None:
            return "single-quoted value is not closed"
        if re.search(r"(?<!')'(?!')", inner.replace("''", "")):
            return "a lone ' inside a single-quoted value; double it"
        return None
    if value[:1] == '"':
        if not (value.endswith('"') and len(value) > 1):
            return "double-quoted value is not closed"
        if re.search(r'(?<!\\)"', value[1:-1]):
            return 'an unescaped " inside a double-quoted value'
        return None
    if ": " in value or value.endswith(":"):
        return "a plain value holding ': ' is a YAML error; put it in quotes"
    if " #" in value:
        return "a plain value holding ' #' is cut there as a comment; put it in quotes"
    return None


def main():
    # The heuristic must reject what the runner rejected, and accept what it loaded.
    check("an unquoted ': ' is caught",
          problem("description: should fire no skill: making a change is implement's") is not None)
    check("the same text in double quotes passes",
          problem('description: "should fire no skill: making a change is implement\'s"') is None)
    check("an unquoted ' #' is caught", problem("description: one # two") is not None)
    check("a lone quote in a single-quoted value is caught", problem("pattern: 'it's'") is not None)
    check("a doubled quote is fine", problem("pattern: 'it''s'") is None)
    check("a plain value without a colon passes", problem("description: fixtures/07 — green tests") is None)
    check("a flow list is left alone", problem("tags: [behavior, expensive]") is None)

    try:
        import yaml
    except ImportError:
        yaml = None
        print("note: PyYAML is not installed; only the stdlib check runs")

    files = sorted(glob.glob(os.path.join(REPO, "plugins", "*", "evals", "**", "*.md"), recursive=True))
    files += sorted(glob.glob(os.path.join(REPO, "plugins", "*", "evals", "**", "case.yaml"), recursive=True))
    bad = []
    for path in files:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        block = text if path.endswith(".yaml") else frontmatter(text)
        rel = os.path.relpath(path, REPO).replace(os.sep, "/")
        if block is None:
            if "/graders/" in rel or rel.endswith("prompt.md"):
                bad.append("%s: no --- frontmatter" % rel)
            continue
        for line in block.splitlines():
            why = problem(line)
            if why:
                bad.append("%s: %s (%s)" % (rel, why, line[:70]))
        if yaml is not None:
            try:
                yaml.safe_load(block)
            except yaml.YAMLError as exc:
                bad.append("%s: PyYAML: %s" % (rel, str(exc).splitlines()[0]))
    check("every eval file's frontmatter parses (%d files)" % len(files), not bad, "\n  " + "\n  ".join(bad))

    print()
    if FAILURES:
        print("%d failure(s): %s" % (len(FAILURES), ", ".join(FAILURES)))
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
