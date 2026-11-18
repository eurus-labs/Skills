#!/usr/bin/env python3
# GENERATED FILE -- DO NOT EDIT.
# Source: shared/scripts/survey/scope_record.py
# Regenerate: python3 tools/materialize.py
"""What this run promised to document, and what it did with every file it found.

`scope.json` is the denominator. Coverage measured against the units a run chose to read
is a measure of whether it finished its own to-do list; coverage measured against this is
a measure of whether the document covers the product. The difference is the whole reason
the file exists: a fan-in cutoff may order the work, but it may not quietly decide which
features are in the manual.

Every inventoried file gets a disposition and a reason. **`excluded` is a claim that
needs grounds** -- "the path contains `test`" is not one, because `src/latest/` and
`contest.py` are product source. The run says which rule excluded each file so a reader
can disagree with it.

    product     first-party source the manual is about
    test        tests and test support: readable as evidence, never documented as product
    generated   written by a tool, documented as output rather than as source
    vendor      third-party code vendored in
    asset       README, packaging, CI, configuration, examples

Reading state is tracked apart from classification, because they answer different
questions -- "is this ours?" and "did anyone look at it?" -- and a run that conflates
them cannot report an unread product file at all.

    unread | read | analyzed | excluded

Standard library only. No I/O except `load`: callers own the files.
"""

import hashlib
import json

SCOPE_VERSION = 1

DISPOSITIONS = ("product", "test", "generated", "vendor", "asset")
DOCUMENTED = ("product",)
READING_STATES = ("unread", "read", "analyzed", "excluded")

REQUIRED = ("scope_version", "index_hash", "product_roots", "required_topics", "files")


def scope_hash(scope):
    """The identity a review binds to, over what was promised and what was classified.

    Reading state is deliberately *not* in it. Reading a file is progress against the
    scope, not a change to it -- if it moved the hash, every review would stale each time
    the run read one more file, which is the opposite of what freshness is for.
    """
    payload = {
        "product_roots": sorted(scope.get("product_roots", ()) or ()),
        "required_topics": sorted(scope.get("required_topics", ()) or ()),
        "files": sorted((row.get("path"), row.get("disposition"))
                        for row in scope.get("files", ()) or ()),
    }
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def load(path):
    """The scope written at `path`, or None when there is none or it cannot be read.

    A missing file is the ordinary state of a run that predates the scope record, and every
    consumer has a defined behaviour for it. A file that is there and unreadable is not
    quietly the same thing, so callers that must tell the two apart check `malformed` on
    what they get back -- and `None` here never means "nothing is in scope".
    """
    try:
        with open(path, encoding="utf-8") as fh:
            scope = json.load(fh)
    except (OSError, ValueError):
        return None
    return scope if isinstance(scope, dict) and malformed(scope) is None else None


def why(path):
    """Why `path` is not a usable scope, for the message a caller prints after `load`.

    The rows are meant to be read and, at P1, edited by a person; "not a valid scope" with
    no reason sends them hunting through a file for a typo.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            scope = json.load(fh)
    except OSError as exc:
        return "cannot be read (%s)" % exc.strerror
    except ValueError as exc:
        return "is not JSON (%s)" % exc
    return malformed(scope) or "is not a scope"


def malformed(scope):
    """Why this scope cannot be read, or None."""
    if not isinstance(scope, dict):
        return "scope must be an object"
    if scope.get("scope_version") != SCOPE_VERSION:
        return "scope_version %r is not %d" % (scope.get("scope_version"), SCOPE_VERSION)
    missing = [f for f in REQUIRED if scope.get(f) in (None, "")]
    if missing:
        return "missing %s" % ", ".join(missing)
    seen = set()
    for row in scope.get("files", ()) or ():
        if not isinstance(row, dict) or not row.get("path"):
            return "every file row needs a path"
        if row["path"] in seen:
            return "%s is listed twice" % row["path"]
        seen.add(row["path"])
        if row.get("disposition") not in DISPOSITIONS:
            return "%s has disposition %r" % (row["path"], row.get("disposition"))
        if row.get("reading") not in READING_STATES:
            return "%s has reading state %r" % (row["path"], row.get("reading"))
        # The rule that makes an exclusion arguable instead of a fait accompli.
        if row["disposition"] != "product" and not str(row.get("reason", "")).strip():
            return ("%s is %s and gives no reason; an exclusion a reader cannot "
                    "disagree with is not a decision" % (row["path"], row["disposition"]))
    return None


def coverage(scope):
    """Reading progress against the promised scope, not against a chosen shortlist."""
    product = [r for r in scope.get("files", ()) or ()
               if r.get("disposition") in DOCUMENTED]
    counted = {state: len([r for r in product if r.get("reading") == state])
               for state in READING_STATES}
    return {"product_files": len(product),
            "by_reading": counted,
            "unread": sorted(r["path"] for r in product if r.get("reading") == "unread"),
            "excluded_kinds": {d: len([r for r in scope.get("files", ()) or ()
                                       if r.get("disposition") == d])
                               for d in DISPOSITIONS if d not in DOCUMENTED}}


def documented_paths(scope):
    """The one product view every consumer shares.

    Class graph, component inventory, module pages, diagram completeness and coverage all
    read this. They used to each decide what counted, which is how a test class reached a
    product diagram while the module pages had already dropped it.
    """
    return {row["path"] for row in scope.get("files", ()) or ()
            if row.get("disposition") in DOCUMENTED}


def symbol_free(scope):
    """Product files the scanner found no symbol in: entry scripts, side-effect modules.

    They are in scope -- a way into the system earns a paragraph whether or not it defines
    anything -- and no derived claim can anchor a statement to them, so the checks that ask a
    module for four kinds of statement ask these for one that says what the file does.
    """
    return {row["path"] for row in scope.get("files", ()) or ()
            if row.get("disposition") in DOCUMENTED and row.get("symbols") == 0}


def sync_reading(scope, analysed):
    """`scope` with each product file's reading state brought up to date; a new dict.

    `analysed` is the set of paths that have a row in `module-analysis.jsonl`. A file a
    row exists for is `analyzed`; one that was `analyzed` and has lost its row goes back to
    `unread`, because that state is derived from the ledger and not accumulated beside it.
    A file marked `read` by hand keeps that mark. Non-product rows are never touched. Pure:
    nothing is written, so `status` can call it.
    """
    synced = dict(scope)
    rows = []
    for row in scope.get("files", ()) or ():
        row = dict(row)
        if row.get("disposition") in DOCUMENTED:
            if row.get("path") in analysed:
                row["reading"] = "analyzed"
            elif row.get("reading") == "analyzed":
                row["reading"] = "unread"
        rows.append(row)
    synced["files"] = rows
    return synced


def narrowed(scope):
    """Rows a person moved out of the product at P1, each with the note they gave.

    The classification is mechanical; a row carrying `override` is one somebody changed.
    A report that lists them is how a deliberately partial draft stays honest about being
    one, instead of reading as a run that forgot those files.
    """
    return sorted(({"path": row["path"], "disposition": row.get("disposition"),
                    "override": row["override"]}
                   for row in scope.get("files", ()) or () if row.get("override")),
                  key=lambda item: item["path"])


def product_view(index, scope):
    """`index` restricted to the documented paths, for the builders that draw the product.

    Files, edges, entry points and the fan maps are cut to the product, so a test class
    never becomes a diagram node or a module page. The caller keeps the whole index for
    anything that resolves evidence: a test may still be cited, and must still resolve.
    """
    keep = documented_paths(scope)
    view = dict(index)
    view["files"] = [r for r in index.get("files", ()) if r.get("path") in keep]
    edges = [e for e in index.get("edges", ()) or ()
             if e.get("from") in keep and e.get("to") in keep]
    if "edges" in index:
        view["edges"] = edges
        fan_in, fan_out = {}, {}
        for edge in edges:
            fan_in[edge["to"]] = fan_in.get(edge["to"], 0) + 1
            fan_out[edge["from"]] = fan_out.get(edge["from"], 0) + 1
        view["fan_in"], view["fan_out"] = fan_in, fan_out
    view["entry_points"] = [e for e in index.get("entry_points", ()) or ()
                            if (e.get("path") if isinstance(e, dict) else e) in keep]
    return view
