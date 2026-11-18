#!/usr/bin/env python3
# GENERATED FILE -- DO NOT EDIT.
# Source: shared/scripts/render/snapshot_revision.py
# Regenerate: python3 tools/materialize.py
"""Keep each distinct rendered draft as an immutable revision under drafts/rev-NNNN/."""

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from draft_artifact import (read_revision, revision_dir, revision_meta_dir,  # noqa: E402
                            tree_hash)

REVISION = re.compile(r"^rev-(\d{4,})$")
MIN_KEEP = 3


def revision_numbers(drafts):
    found = []
    if os.path.isdir(drafts):
        for name in os.listdir(drafts):
            match = REVISION.match(name)
            if match and os.path.isdir(os.path.join(drafts, name)):
                found.append(int(match.group(1)))
    return sorted(found)


def load_json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
        fh.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--draft", required=True, help="the rendered staging tree")
    parser.add_argument("--manifest", required=True, help="render-manifest.json to update")
    parser.add_argument("--drafts", required=True, help="the revisions directory")
    parser.add_argument("--seal", help="publish-seal.json; the revision it names is "
                                       "never pruned")
    parser.add_argument("--keep", type=int, default=5,
                        help="how many recent revisions to keep (minimum %d)" % MIN_KEEP)
    args = parser.parse_args()
    if args.keep < MIN_KEEP:
        sys.stderr.write("FAIL  --keep-revisions must be at least %d, so two review "
                         "rounds' findings survive\n" % MIN_KEEP)
        return 2
    manifest = load_json(args.manifest)
    if not os.path.isdir(args.draft) or not isinstance(manifest, dict):
        sys.stderr.write("FAIL  rendered draft or render manifest is missing\n")
        return 2
    draft_hash = tree_hash(args.draft)
    if manifest.get("draft_hash") != draft_hash:
        sys.stderr.write("FAIL  the render manifest does not describe the staged tree\n")
        return 1

    os.makedirs(args.drafts, exist_ok=True)
    counter_path = os.path.join(args.drafts, "counter.json")
    counter = load_json(counter_path)
    used = counter.get("highest", 0) if isinstance(counter, dict) else 0
    numbers = revision_numbers(args.drafts)
    latest = "rev-%04d" % numbers[-1] if numbers else None
    previous = read_revision(args.drafts, latest) if latest else None

    if previous and previous.get("draft_hash") == draft_hash:
        revision = latest
        print("rendered draft is unchanged; reusing %s" % revision)
    else:
        # Never reuse a number, even after pruning: a review row that names `rev-0002`
        # must not later mean another tree.
        number = max([used] + numbers) + 1
        revision = "rev-%04d" % number
        pending = os.path.join(args.drafts, ".%s.tmp" % revision)
        if os.path.exists(pending):
            shutil.rmtree(pending)
        shutil.copytree(args.draft, pending, ignore=shutil.ignore_patterns("_build"))
        meta = revision_meta_dir(args.drafts, revision)
        if os.path.exists(meta):
            shutil.rmtree(meta)
        os.makedirs(meta)
        write_json(os.path.join(meta, "revision.json"), {
            "revision_version": 1, "revision": revision, "draft_hash": draft_hash,
            "doc_hash": manifest.get("doc_hash"),
            "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "previous": latest})
        os.replace(pending, revision_dir(args.drafts, revision))
        write_json(counter_path, {"highest": number})
        print("minted %s (%s)" % (revision, draft_hash))

    manifest["render_manifest_version"] = 2
    manifest["revision"] = revision
    write_json(args.manifest, manifest)

    protected = {revision}
    seal = load_json(args.seal) if args.seal else None
    if isinstance(seal, dict) and isinstance(seal.get("revision"), str):
        protected.add(seal["revision"])
    numbers = revision_numbers(args.drafts)
    for number in (numbers[:-args.keep] if len(numbers) > args.keep else []):
        name = "rev-%04d" % number
        if name in protected:
            continue
        shutil.rmtree(revision_dir(args.drafts, name))
        shutil.rmtree(revision_meta_dir(args.drafts, name), ignore_errors=True)
        print("pruned %s (keeping the %d most recent revisions)" % (name, args.keep))
    return 0


if __name__ == "__main__":
    sys.exit(main())
