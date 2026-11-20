#!/usr/bin/env python3
# GENERATED FILE -- DO NOT EDIT.
# Source: shared/scripts/migrate_build.py
# Regenerate: python3 tools/materialize.py
"""Carry an older `.docs-build/` forward without carrying its approvals forward.

Three artifacts of an older build are refused by the current scripts, each with a message
that says to migrate and nothing to migrate with:

    manual-analysis.json   `manual_version` 1   refused by `manual.py`
    prose-review.jsonl     v1 review rows       refused by `review_records.py`
    publish-seal.json      `seal_version` 1     refused by `promote_docs.py`

This module decides what each becomes. It is pure where it can be: `migrate_manual` and
`migrate_reviews` take what a file holds and return what the new file should hold, and
`plan` reads a build directory and returns the list of changes without making any. The
driver (`pipeline.py migrate`) prints that plan and, with `--apply`, performs it.

**Nothing here approves anything.** A v1 `confirmed` answer becomes a `partial`, `observed`
answer whose review is `pending`; a v1 review row is set aside and no v2 row is written in
its place, so every block it named reads as unreviewed. A v2 row asserts that someone
looked at a bound piece of content, and a v1 row was bound to nothing.

**Nothing is dropped and nothing is weakened.** Answer text, evidence and verified ids are
carried byte for byte. An answer that would not pass `read_answer()` -- a verified id this
run no longer knows, evidence beyond the end of a file that has changed -- is migrated as it
is and reported with `read_answer()`'s own message.

Standard library only.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

MANUAL_FILE = "manual-analysis.json"
REVIEW_FILE = "prose-review.jsonl"
SEAL_FILE = "publish-seal.json"
RENDER_MANIFEST = "render-manifest.json"
RENDER_MANIFEST_VERSION = 2

# v1 `status` -> (v2 `basis`, v2 `completeness`).
#
# `confirmed` -> `observed` because v1 required a `confirmed` answer to name a verified id,
# which is the bar v2 sets for `observed`. Never `complete`: v1 did not record which facets
# an answer covered, so no migrated answer can claim to cover them all.
STATUS_MAP = {
    "confirmed": ("observed", "partial"),
    "inferred": ("inferred", "partial"),
    "unknown": ("unknown", "unanswered"),
    "not_applicable": ("not_applicable", "unanswered"),
}

# Required by `read_answer()` on a `partial` answer, and v1 never listed facets.
FACETS_MARKER = ("not recorded in manual_version 1: the facets this answer covers were "
                 "never listed")


def v1_name(path):
    """`manual-analysis.json` -> `manual-analysis.v1.json`."""
    stem, extension = os.path.splitext(path)
    return stem + ".v1" + extension


def migrate_manual(content, validate=None):
    """A `manual_version` 1 answer file as version 2, and a report of what was done.

    `validate(qid, answer)` returns `read_answer()`'s message for an answer that would not
    pass, or None; it is optional so the mapping can be checked without a repository.
    Returns `(migrated, report)`; `migrated` is None when `content` is not version 1.
    """
    report = {"answers": 0, "by_status": {}, "problems": [], "left": []}
    if not isinstance(content, dict) or content.get("manual_version") != 1:
        return None, report
    migrated = dict(content)
    migrated["manual_version"] = 2
    answers = content.get("answers")
    if isinstance(answers, dict):
        result = {}
        for qid, answer in answers.items():
            if not isinstance(answer, dict) or answer.get("status") not in STATUS_MAP \
                    or "basis" in answer:
                # Not something the mapping is defined for. Left exactly as found, and
                # named, so it fails where it always would have and the reader knows why.
                result[qid] = answer
                report["left"].append(qid)
                continue
            basis, completeness = STATUS_MAP[answer["status"]]
            moved = {}
            for key, value in answer.items():
                if key == "status":
                    moved["basis"] = basis
                    moved["completeness"] = completeness
                    moved["content_review"] = "pending"
                else:
                    moved[key] = value
            if completeness == "partial":
                moved["facets_missing"] = [FACETS_MARKER]
            result[qid] = moved
            report["answers"] += 1
            report["by_status"][answer["status"]] = \
                report["by_status"].get(answer["status"], 0) + 1
            problem = validate(qid, moved) if validate else None
            if problem:
                report["problems"].append(problem)
        migrated["answers"] = result
    return migrated, report


def _row(line):
    """The JSON object on a review-file line, or None."""
    try:
        row = json.loads(line)
    except ValueError:
        return None
    return row if isinstance(row, dict) else None


def migrate_reviews(lines):
    """Split a review file's lines into `(kept, legacy, unknown)`.

    A row whose `review_version` is missing or 1 is `legacy`. Everything else stays in
    `kept`, in its order, byte for byte -- including a row that is not valid and a row
    `review_records` will refuse for another reason, because deciding what those mean is
    not this module's job. `unknown` counts the rows that name a version this module does
    not know: they stay, and are reported.
    """
    kept, legacy, unknown = [], [], 0
    for line in lines:
        row = _row(line) if line.strip() else None
        if row is None:
            kept.append(line)
        elif row.get("review_version") in (None, 1):
            legacy.append(line)
        else:
            kept.append(line)
            if row.get("review_version") != 2:
                unknown += 1
    return kept, legacy, unknown


def _read_json(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def _read_bytes(path):
    try:
        with open(path, "rb") as handle:
            return handle.read()
    except OSError:
        return None


def _rows(path):
    rows = []
    try:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if isinstance(row, dict):
                    rows.append(row)
    except OSError:
        pass
    return rows


class _Statements(object):
    """The statements of a module analysis by id: all `manual.confirmable` reads of one."""

    def __init__(self, rows):
        self.by_id = {}
        for row in rows:
            for statement in row.get("statements", ()) or ():
                if isinstance(statement, dict):
                    self.by_id[statement.get("id")] = dict(statement,
                                                           path=row.get("path", ""))


def answer_validator(build, root):
    """`validate(qid, answer)` that applies `manual.read_answer()` against this run.

    Returns None when `manual.py` cannot be imported (a partial install), in which case the
    report says answers were not checked rather than saying they passed.
    """
    from pathlib import Path
    sys.path.insert(0, os.path.join(HERE, "document"))
    try:
        import manual
    except Exception:                                    # noqa: BLE001 -- see docstring
        return None
    finally:
        sys.path.pop(0)
    index = _read_json(os.path.join(build, "structure.json")) or {}
    extra = {}
    for key, name in (("architecture", "architecture-analysis.json"),
                      ("flows", "flow-analysis.json"),
                      ("operations", "operations-analysis.json"),
                      ("config", "config-analysis.json")):
        loaded = _read_json(os.path.join(build, name))
        # A file from an earlier scan names real things and proves nothing about this one;
        # the document builder refuses it, so it cannot have verified anything either.
        if isinstance(loaded, dict) and loaded.get("index_hash") == index.get("index_hash"):
            extra[key] = loaded
    origins = manual.confirmable(
        _rows(os.path.join(build, "claims.verified.jsonl")),
        _Statements(_rows(os.path.join(build, "module-analysis.jsonl"))), extra)
    resolved = Path(root).resolve()

    def validate(qid, answer):
        try:
            manual.read_answer(qid, answer, resolved, origins)
        except (ValueError, OSError, UnicodeError) as exc:
            return str(exc)
        return None

    return validate


def plan(build, review=None, root="."):
    """What `migrate` would change in `build`, without changing it.

    Returns a dict:

        items      one per legacy artifact: `path`, `version`, `summary`, and for one that
                   can be migrated `writes` ({path: bytes}), `moves` ([(src, dst)]) and
                   `originals` ([dst]) that `--apply` would create
        unknown    artifacts that name a version this module does not know, never touched
        problems   `read_answer()` messages for migrated answers that would not pass
        notes      what is regenerated by a rerun, with the command to run
        conflicts  `.v1` files that already exist with different content
        answers    how many answers were migrated
        validated  False when `manual.py` could not check them
    """
    result = {"items": [], "unknown": [], "problems": [], "notes": [], "conflicts": [],
              "answers": 0, "validated": True}
    manual_path = os.path.join(build, MANUAL_FILE)
    content = _read_json(manual_path)
    version = content.get("manual_version") if isinstance(content, dict) else None
    if version == 1:
        validate = answer_validator(build, root)
        result["validated"] = validate is not None
        migrated, report = migrate_manual(content, validate)
        original = _read_bytes(manual_path)
        text = json.dumps(migrated, indent=2, ensure_ascii=False) + "\n"
        result["items"].append({
            "path": manual_path, "version": 1, "kind": "manual",
            "summary": "write manual_version 2 (%d answer(s), every one `content_review: "
                       "pending`); original kept as %s"
                       % (report["answers"], os.path.basename(v1_name(manual_path))),
            "writes": {manual_path: text.encode("utf-8"),
                       v1_name(manual_path): original},
            "originals": [v1_name(manual_path)]})
        result["answers"] = report["answers"]
        result["problems"] = report["problems"]
        result["left"] = report["left"]
    elif content is not None and version != 2 and os.path.isfile(manual_path):
        result["unknown"].append((manual_path, version))

    review_path = review or os.path.join(build, REVIEW_FILE)
    if os.path.isfile(review_path):
        try:
            with open(review_path, encoding="utf-8") as handle:
                lines = handle.read().splitlines(True)
        except (OSError, UnicodeError):
            lines = []
        kept, legacy, unknown_rows = migrate_reviews(lines)
        if legacy:
            archive = v1_name(review_path)
            result["items"].append({
                "path": review_path, "version": 1, "kind": "review",
                "summary": "move %d v1 row(s) to %s; %d row(s) stay. No v2 row is written, "
                           "so every block they named is unreviewed"
                           % (len(legacy), os.path.basename(archive), len(kept)),
                "writes": {review_path: "".join(kept).encode("utf-8"),
                           archive: "".join(legacy).encode("utf-8")},
                "originals": [archive]})
        if unknown_rows:
            result["unknown"].append((review_path, "%d row(s)" % unknown_rows))

    seal_path = os.path.join(build, SEAL_FILE)
    seal = _read_json(seal_path)
    if isinstance(seal, dict) and seal.get("seal_version") == 1:
        result["items"].append({
            "path": seal_path, "version": 1, "kind": "seal",
            "summary": "rename to %s; run `review` again to seal a draft"
                       % os.path.basename(v1_name(seal_path)),
            "writes": {}, "moves": [(seal_path, v1_name(seal_path))],
            "originals": [v1_name(seal_path)]})
    elif isinstance(seal, dict) and seal.get("seal_version") != 2:
        result["unknown"].append((seal_path, seal.get("seal_version")))

    # A second run: an original that is already there with the same bytes is the earlier
    # migration's own, and is not a conflict; different bytes are somebody's file.
    for item in result["items"]:
        for destination in item["originals"]:
            if not os.path.exists(destination):
                continue
            wanted = item["writes"].get(destination)
            if wanted is None:
                wanted = _read_bytes(item["path"])
            if _read_bytes(destination) != wanted:
                result["conflicts"].append(destination)

    # What a rerun regenerates. Named, not edited.
    if os.path.isfile(os.path.join(build, "structure.json")):
        if not os.path.isfile(os.path.join(build, "scope.json")):
            result["notes"].append(
                "no scope.json: this build predates the scope record; run `survey`")
        manifest = _read_json(os.path.join(build, RENDER_MANIFEST))
        rendered = isinstance(manifest, dict) \
            or os.path.isdir(os.path.join(build, "rendered-docs"))
        if rendered and not os.path.isdir(os.path.join(build, "drafts")):
            result["notes"].append(
                "rendered output but no drafts/: this build predates draft revisions; "
                "run `render`")
        elif isinstance(manifest, dict) and \
                manifest.get("render_manifest_version") != RENDER_MANIFEST_VERSION:
            result["notes"].append(
                "render-manifest.json is version %r, not %d; run `render`"
                % (manifest.get("render_manifest_version"), RENDER_MANIFEST_VERSION))
    return result


def legacy_count(build, review=None):
    """How many files `migrate` would rewrite: what `status` and `resume` point at."""
    changes = 0
    content = _read_json(os.path.join(build, MANUAL_FILE))
    if isinstance(content, dict) and content.get("manual_version") == 1:
        changes += 1
    review_path = review or os.path.join(build, REVIEW_FILE)
    if os.path.isfile(review_path):
        try:
            with open(review_path, encoding="utf-8") as handle:
                if migrate_reviews(handle.read().splitlines(True))[1]:
                    changes += 1
        except (OSError, UnicodeError):
            pass
    seal = _read_json(os.path.join(build, SEAL_FILE))
    if isinstance(seal, dict) and seal.get("seal_version") == 1:
        changes += 1
    return changes
