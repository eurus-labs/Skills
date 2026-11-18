#!/usr/bin/env python3
# GENERATED FILE -- DO NOT EDIT.
# Source: shared/scripts/publish/promote_docs.py
# Regenerate: python3 tools/materialize.py
"""Atomically promote a sealed documentation draft into the target directory."""

import argparse
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from draft_artifact import file_hash, read_revision, tree_hash, verify_revision  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--draft", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--doc", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--seal", required=True)
    parser.add_argument("--drafts", required=True, help="the revisions directory")
    args = parser.parse_args()
    for path, label in ((args.draft, "draft"), (args.doc, "document model"),
                        (args.report, "generation report"), (args.seal, "publish seal")):
        if not os.path.exists(path):
            sys.stderr.write("FAIL  no such %s: %s\n" % (label, path))
            return 2
    with open(args.report, encoding="utf-8") as fh:
        report = json.load(fh)
    with open(args.seal, encoding="utf-8") as fh:
        seal = json.load(fh)
    if seal.get("seal_version") != 2 or not seal.get("revision"):
        sys.stderr.write("FAIL  the publish seal is version %r and names no draft revision; "
                         "run review again\n" % seal.get("seal_version"))
        return 1
    revision = seal["revision"]
    problem = verify_revision(args.drafts, revision)
    if problem:
        sys.stderr.write("FAIL  %s\n" % problem)
        return 1
    actual = {"draft_hash": tree_hash(args.draft), "doc_hash": file_hash(args.doc),
              "report_hash": file_hash(args.report)}
    if report.get("status") != "passed" or any(seal.get(k) != v for k, v in actual.items()):
        sys.stderr.write("FAIL  draft, document model, or review report changed after final review\n")
        return 1

    if read_revision(args.drafts, revision).get("draft_hash") != actual["draft_hash"]:
        sys.stderr.write("FAIL  the staged draft is not the sealed revision %s; render and "
                         "review again\n" % revision)
        return 1

    target = os.path.abspath(args.target)
    parent = os.path.dirname(target)
    os.makedirs(parent, exist_ok=True)
    temporary = tempfile.mkdtemp(prefix=".%s.publish-" % os.path.basename(target), dir=parent)
    backup = None
    try:
        shutil.rmtree(temporary)
        shutil.copytree(args.draft, temporary, ignore=shutil.ignore_patterns("_build"))
        if os.path.exists(target):
            backup = tempfile.mkdtemp(prefix=".%s.backup-" % os.path.basename(target), dir=parent)
            os.rmdir(backup)
            os.replace(target, backup)
        try:
            os.replace(temporary, target)
        except Exception:
            if backup and not os.path.exists(target):
                os.replace(backup, target)
            raise
        if backup:
            shutil.rmtree(backup)
        print("published sealed documentation to %s" % args.target)
        return 0
    finally:
        if os.path.exists(temporary):
            shutil.rmtree(temporary)


if __name__ == "__main__":
    sys.exit(main())
