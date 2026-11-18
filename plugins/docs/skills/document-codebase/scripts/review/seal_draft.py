#!/usr/bin/env python3
# GENERATED FILE -- DO NOT EDIT.
# Source: shared/scripts/review/seal_draft.py
# Regenerate: python3 tools/materialize.py
"""Seal the exact rendered tree after the final quality gate passes."""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from draft_artifact import file_hash, read_revision, tree_hash, verify_revision  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--draft", required=True)
    parser.add_argument("--doc", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--render-manifest", required=True)
    parser.add_argument("--drafts", required=True, help="the revisions directory")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    for path, label in ((args.draft, "draft"), (args.doc, "document model"),
                        (args.report, "generation report"),
                        (args.render_manifest, "render manifest")):
        if not os.path.exists(path):
            sys.stderr.write("FAIL  no such %s: %s\n" % (label, path))
            return 2
    with open(args.report, encoding="utf-8") as fh:
        report = json.load(fh)
    with open(args.render_manifest, encoding="utf-8") as fh:
        rendered = json.load(fh)
    if report.get("status") != "passed":
        sys.stderr.write("FAIL  generation report is %r, not passed\n" % report.get("status"))
        return 1
    current_draft, current_doc = tree_hash(args.draft), file_hash(args.doc)
    if (rendered.get("draft_hash") != current_draft
            or rendered.get("doc_hash") != current_doc):
        sys.stderr.write("FAIL  draft or document model changed after render\n")
        return 1
    # A seal names the one revision it vouches for, and that revision has to still be the
    # tree on disk: a render that changed nothing reuses its revision, one that changed
    # something mints a new revision that has no seal.
    revision = rendered.get("revision")
    if not revision:
        sys.stderr.write("FAIL  the render manifest names no revision; render again\n")
        return 1
    problem = verify_revision(args.drafts, revision)
    if problem:
        sys.stderr.write("FAIL  %s\n" % problem)
        return 1
    if read_revision(args.drafts, revision).get("draft_hash") != current_draft:
        sys.stderr.write("FAIL  the staged draft is not revision %s; render again\n" % revision)
        return 1
    seal = {"seal_version": 2, "revision": revision, "draft_hash": current_draft,
            "doc_hash": current_doc, "report_hash": file_hash(args.report)}
    parent = os.path.dirname(os.path.abspath(args.out))
    os.makedirs(parent, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(seal, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print("sealed reviewed draft: %s" % seal["draft_hash"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
