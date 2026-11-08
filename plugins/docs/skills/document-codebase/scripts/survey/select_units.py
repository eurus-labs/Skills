#!/usr/bin/env python3
# GENERATED FILE -- DO NOT EDIT.
# Source: shared/scripts/survey/select_units.py
# Regenerate: python3 tools/materialize.py
"""Choose the modules this run describes in full, by how connected each one is.

    python3 scripts/select_units.py --index .docs-build/structure.json \\
        --out .docs-build/units.txt --top 25

Every module named here costs a model call, and the ones worth that call are the ones the
rest of the system is wired through. Rank by connections -- how many other modules import
this one (fan-in) plus how many it imports (fan-out) -- keep the top N, and add every entry
point: a way into the system earns a paragraph whether or not anything imports it.

**Why not fan-in alone.** Fan-in finds the foundations -- compatibility shims, shared
types, helpers -- and ranks the modules that drive the system last, because an
orchestrator imports a great deal and is imported by almost nothing. On requests it put
`compat.py` first and `sessions.py`, `adapters.py` and `api.py` near the bottom, so a
tighter budget documented the helpers and dropped the request path. Counting both
directions keeps the foundations and brings the orchestrators up beside them.

`units.txt` is a contract: `derive_claims.py` claims exactly these modules, `assemble.py`
fails on any of them that came back without a row, and `quality_docs.py` measures coverage
against them and counts everything else apart. Edit the selection here, not afterwards.

**Fan-in is a heuristic, and this prints when it is a bad one.** A repository of standalone
programs -- CLIs invoked by a shell, scripts run by a scheduler -- imports nothing from
itself, so every fan-in is 0 and the ranking is arbitrary. The warning says so rather than
letting an arbitrary top 25 read like a considered one.

Ties break by path, so the same index always selects the same modules.

Standard library only. Exit codes: 0 ok, 2 input error, 3 internal error.
"""

import argparse
import json
import os
import sys


def fail(message, code=2):
    sys.stderr.write("FAIL  %s\n" % message)
    return code


def production_degree(index):
    """`(fan_in, fan_out)`: for each module, how many distinct non-test modules import it
    and how many it imports.

    The scanner's own `fan_in` counts every incoming edge, tests included, which is the
    right factual measure and the wrong ranking. A well-tested helper is imported by
    twenty test files and by one module, and on that count it outranks the entry point --
    so the budget goes to whatever the suite exercises most rather than to what the
    system is built on. Dropping test files from the selection without dropping their
    edges fixes half of it and leaves the half that decides the order.

    Modules are counted, not import statements: two `from x import` lines in one file
    are one dependency, and counting them twice ranks a file by how its imports are
    formatted.

    Falls back to the scanner's maps when an index carries no edges, so an older or
    edge-less index ranks as it always did rather than flatly at zero.
    """
    edges = index.get("edges")
    if not edges:
        return dict(index.get("fan_in") or {}), dict(index.get("fan_out") or {})
    tests = {record["path"] for record in index.get("files", ())
             if record.get("is_test")}
    importers, imported = {}, {}
    for edge in edges:
        source, target = edge.get("from"), edge.get("to")
        if not target or source == target or source in tests or target in tests:
            continue
        importers.setdefault(target, set()).add(source)
        imported.setdefault(source, set()).add(target)
    return ({path: len(found) for path, found in importers.items()},
            {path: len(found) for path, found in imported.items()})


def connections(index):
    """Every module's `(fan_in, fan_out)`, and the ordering both the selection and the
    overview use: most connections first, then most depended upon, then by path."""
    fan_in, fan_out = production_degree(index)

    def key(path):
        return (-(fan_in.get(path, 0) + fan_out.get(path, 0)), -fan_in.get(path, 0), path)
    return fan_in, fan_out, key


def select(index, top):
    """The paths to describe in full, and why each one is in the list.

    Returns `(paths, reasons, ranked)` -- `reasons` maps a path to `connected`,
    `entry_point` or both, and `ranked` is the `(path, connections)` ordering the cutoff
    was taken from.
    """
    fan_in, fan_out, order = connections(index)
    # Not tests. A test file is evidence that the code works, not a part of the system a
    # reader is being introduced to: documenting it spends the budget describing scaffolding
    # and puts `test_parser.py` in a module reference beside the parser. The scanner already
    # marks them, the gate's fallback budget already skips them, and the selection did not --
    # so a repository with a large suite spent most of its units on it. A reader who wants
    # the tests is told how to run them, on the page the operations analysis fills.
    #
    # Only files that define something. A module with no symbol has nothing to anchor a
    # statement to -- `validate_analysis` requires a statement to name something that is
    # in the file it describes, and `assemble` requires a fragment citing a derived
    # claim, of which an empty `__init__.py` has none. Selecting one puts a unit in the
    # budget that no amount of work can satisfy: the assembler fails the run for a unit
    # with no row, and the coverage it drags down cannot be recovered. The gate's own
    # fallback budget has always filtered on this; the selection did not, and the two
    # disagreeing is what put empty package markers in `units.txt`.
    known = sorted(record["path"] for record in index.get("files", ())
                   if record.get("symbols") and not record.get("is_test"))
    # Rank every scanned file, not every key of `fan_in`: the scanner builds that map by
    # counting incoming edges, so a module nothing imports is absent from it rather than
    # present with 0. Ranking only its keys would drop those modules from the cutoff
    # entirely, and a repository of independent programs -- which has no keys at all --
    # would select nothing and be reported as having no module to describe.
    ranked = [(path, fan_in.get(path, 0) + fan_out.get(path, 0))
              for path in sorted(known, key=order)]

    reasons = {}
    for path, _count in ranked[:top]:
        reasons.setdefault(path, []).append("connected")
    # `known` is already restricted to files that define something, so an entry point
    # that defines nothing is skipped here too rather than added back.
    for entry in index.get("entry_points", ()):
        path = entry.get("path") if isinstance(entry, dict) else entry
        if path in set(known):
            reasons.setdefault(path, []).append("entry_point")
    return sorted(reasons), reasons, ranked


def warnings_for(index, ranked, selected):
    """The ways this selection is weaker than its size suggests."""
    notes = []
    if ranked and ranked[0][1] == 0:
        notes.append("no module in this repository imports or is imported by another, so "
                     "the ranking carries no information -- the cutoff below is arbitrary. "
                     "Choose the units by hand and say in the document that you did.")
    entries = [e.get("path") if isinstance(e, dict) else e
               for e in index.get("entry_points", ())]
    files = len(index.get("files", ()))
    if files and len(entries) * 2 >= files:
        notes.append("the entry-point heuristic matched %d of %d scanned files; these are "
                     "candidates for a way in, not a list of them."
                     % (len(entries), files))
    return notes


def budget_note(selected, top):
    """Said when the selection is much larger than the cutoff that was asked for.

    Every entry point is added whatever the cutoff, which is right on a repository with
    two or three ways in and wrong on one where every file carries a `__main__` guard --
    a tree of standalone scripts, which is a shape this skill meets often. There `--top 8`
    selects sixty, and the number that decides the cost of the run is not the one that was
    typed. The proportion of entry points to files does not catch it: just under half of
    them can still be six times the cutoff.
    """
    if top and len(selected) > top * 2:
        return ("--top %d was asked for and %d unit(s) were selected: every entry point "
                "is added whatever the cutoff, and this repository has many. That is "
                "%.1fx the budget, so decide it deliberately -- raise --top and mean it, "
                "or name the units by hand." % (top, len(selected), len(selected) / float(top)))
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--index", required=True, help="path to structure.json")
    parser.add_argument("--out", default=".docs-build/units.txt")
    parser.add_argument("--top", type=int, default=25,
                        help="how many modules to keep by connections (default 25)")
    args = parser.parse_args()

    if args.top < 0:
        return fail("--top must not be negative")
    if not os.path.isfile(args.index):
        return fail("no such index: %s" % args.index)
    try:
        with open(args.index, encoding="utf-8") as fh:
            index = json.load(fh)
    except (OSError, ValueError) as exc:
        return fail("cannot read %s: %s" % (args.index, exc))
    if index.get("schema_version") not in (2, 3):
        return fail("unsupported index schema_version %r" % index.get("schema_version"))

    paths, reasons, ranked = select(index, args.top)
    if not paths:
        return fail("the index holds no file to describe")

    directory = os.path.dirname(args.out)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(paths) + "\n")

    # The same counts the ranking used, or the columns would explain a different order
    # than the one on the page.
    fan_in, fan_out, order = connections(index)
    print("in   out  %-22s path" % "why")
    for path in sorted(paths, key=order):
        print("%-4d %-4d %-22s %s" % (fan_in.get(path, 0), fan_out.get(path, 0),
                                      "+".join(reasons[path]), path))
    print("wrote %d unit(s) to %s -- top %d by connections (fan-in + fan-out) plus every "
          "entry point" % (len(paths), args.out, args.top))
    for note in warnings_for(index, ranked, paths):
        print("WARN  %s" % note)
    overrun = budget_note(paths, args.top)
    if overrun:
        print("WARN  %s" % overrun)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write("ERROR %s\n" % exc)
        sys.exit(3)
