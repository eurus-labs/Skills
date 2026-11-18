"""Stable hashes shared by final review and publication."""

import hashlib
import json
import os


def file_hash(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def tree_hash(root):
    digest = hashlib.sha256()
    for directory, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d != "_build")
        for name in sorted(files):
            path = os.path.join(directory, name)
            relative = os.path.relpath(path, root).replace(os.sep, "/")
            digest.update(relative.encode("utf-8") + b"\0")
            with open(path, "rb") as fh:
                for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                    digest.update(chunk)
            digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


# Revisions: `drafts/rev-NNNN/` is a copy of the rendered tree and nothing else; its records
# sit beside it in `drafts/rev-NNNN.meta/` because anything written inside would change the
# tree hash the snapshot is checked against.

def revision_dir(drafts, rev):
    return os.path.join(drafts, rev)


def revision_meta_dir(drafts, rev):
    return os.path.join(drafts, rev + ".meta")


def read_revision(drafts, rev):
    """The revision's `revision.json`, or None when it is missing or unreadable."""
    try:
        with open(os.path.join(revision_meta_dir(drafts, rev), "revision.json"),
                  encoding="utf-8") as fh:
            record = json.load(fh)
    except (OSError, ValueError):
        return None
    return record if isinstance(record, dict) else None


def verify_revision(drafts, rev):
    """Recompute the snapshot's tree hash. None when it matches, else a message naming it."""
    snapshot = revision_dir(drafts, rev)
    if not os.path.isdir(snapshot):
        return "revision %s has no snapshot directory under %s" % (rev, drafts)
    record = read_revision(drafts, rev)
    if record is None or not record.get("draft_hash"):
        return "revision %s has no readable revision.json" % rev
    actual = tree_hash(snapshot)
    if actual != record["draft_hash"]:
        return ("revision %s was modified after it was rendered (its files hash to %s, "
                "revision.json says %s)" % (rev, actual, record["draft_hash"]))
    return None
