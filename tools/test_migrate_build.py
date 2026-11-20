#!/usr/bin/env python3
"""Behavioural tests for `pipeline.py migrate` and shared/scripts/migrate_build.py.

Stdlib only, no test framework.

The v1 fixtures below are built from what `shared/scripts/document/manual.py` wrote before
commit a6b0733 (`git show a6b0733^:shared/scripts/document/manual.py`): `scaffold()` made
`{"manual_version": 1, "index_hash", "prefilled", "answers", "pages"}`, and each answer was
`{status, text, evidence, verified_ids, next_check, reviewer}` with `status` one of
`confirmed`, `inferred`, `unknown`, `not_applicable`. Where git can show that commit, the
fixture answers are also run through the v1 `read_answer()` so the fixture cannot drift from
what v1 accepted; where it cannot (a shallow clone), that one check is skipped.

    python3 tools/test_migrate_build.py
"""

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from component_scripts import component_paths, script

sys.path[:0] = component_paths()
import manual
import migrate_build
import review_records

FAILURES = []
MARKER = migrate_build.FACETS_MARKER


def check(name, condition, detail=""):
    if condition:
        print("ok   %s" % name)
    else:
        print("FAIL %s %s" % (name, detail))
        FAILURES.append(name)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def read(path):
    with open(path, "rb") as fh:
        return fh.read()


def migrate(root, build, *extra):
    proc = subprocess.run([sys.executable, script("pipeline.py"), "migrate", "--root", root,
                           "--build", build] + list(extra), capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def snapshot(build):
    """{relative path: (bytes hash, mtime_ns)} of every file under the build."""
    out = {}
    for directory, _dirs, files in os.walk(build):
        for name in files:
            path = os.path.join(directory, name)
            out[os.path.relpath(path, build)] = (
                hashlib.sha256(read(path)).hexdigest(), os.stat(path).st_mtime_ns)
    return out


EVIDENCE = [{"path": "README.md", "line_start": 1, "line_end": 2}]

V1_ANSWERS = {
    "1.1.1": {"status": "confirmed", "text": "It parses configuration.  Exactly so.",
              "evidence": EVIDENCE, "verified_ids": ["claim:ok"]},
    "1.1.2": {"status": "inferred", "text": "Probably a CLI.", "evidence": EVIDENCE,
              "verified_ids": []},
    "1.1.3": {"status": "unknown", "text": "TODO — not yet answered.",
              "next_check": "Look in the repository.", "evidence": []},
    "1.1.4": {"status": "not_applicable", "text": "There is no server.",
              "reviewer": "Sam", "evidence": []},
    # Valid under v1 when it was written; this run no longer knows the id.
    "1.1.5": {"status": "confirmed", "text": "Names a retired id.", "evidence": EVIDENCE,
              "verified_ids": ["claim:gone"]},
    # Valid under v1; the file has since shrunk below the cited range.
    "1.1.6": {"status": "inferred", "text": "Cites past the end.",
              "evidence": [{"path": "README.md", "line_start": 1, "line_end": 99}],
              "verified_ids": []},
}
V1_PAGES = {"overview": {"sections": [
    {"heading": "What it is", "body": "A tool.", "answers": ["1.1.1"],
     "evidence": EVIDENCE, "verified_ids": ["claim:ok"]}]}}

V2_ROW = {"review_version": 2, "review_id": "r1", "target_id": "block:b",
          "draft_revision": "rev-0001", "verdict": "confirmed", "review_mode": "independent",
          "reviewer": "Sam", "content_hash": "sha256:abc"}
V1_ROWS = [{"page": "overview", "block": "block:a", "verdict": "ok"},
           {"review_version": 1, "page": "overview", "block": "block:c", "verdict": "ok"}]


def legacy_build(tmp, name="legacy"):
    root = os.path.join(tmp, name)
    build = os.path.join(root, ".docs-build")
    write(os.path.join(root, "README.md"), "line one\nline two\nline three\n")
    write(os.path.join(build, "structure.json"), json.dumps({"index_hash": "sha256:s"}))
    write(os.path.join(build, "claims.verified.jsonl"),
          json.dumps({"id": "claim:ok", "status": "verified", "index_hash": "sha256:s"}) + "\n")
    write(os.path.join(build, "scope.json"), "{}")
    write(os.path.join(build, "manual-analysis.json"), json.dumps(
        {"manual_version": 1, "index_hash": "sha256:s", "template": "manual",
         "prefilled": ["1.1.1"], "answers": V1_ANSWERS, "pages": V1_PAGES}, indent=2))
    write(os.path.join(build, "prose-review.jsonl"),
          "\n".join([json.dumps(V1_ROWS[0]), json.dumps(V2_ROW),
                     json.dumps(V1_ROWS[1]), json.dumps(dict(V2_ROW, review_id="r2"))]) + "\n")
    write(os.path.join(build, "publish-seal.json"),
          json.dumps({"seal_version": 1, "revision": "rev-0001"}))
    write(os.path.join(build, "timings.jsonl"), '{"stage": "x"}\n')
    return root, build


def v1_fixture_matches_v1_reader():
    """The fixture answers pass the v1 `read_answer()`, when git can show that commit."""
    here = os.path.dirname(os.path.abspath(__file__))
    shown = subprocess.run(["git", "show", "a6b0733^:shared/scripts/document/manual.py"],
                           capture_output=True, cwd=here)
    if shown.returncode != 0:
        print("skip v1 reader comparison (commit a6b0733 is not available)")
        return
    tmp = tempfile.mkdtemp(prefix="v1-manual-")
    try:
        path = os.path.join(tmp, "manual_v1.py")
        with open(path, "wb") as fh:
            fh.write(shown.stdout)
        # v1 loads its question list from beside itself.
        shutil.copy(os.path.join(os.path.dirname(script("manual.py")),
                                 "manual_questions.json"), tmp)
        spec = importlib.util.spec_from_file_location("manual_v1", path)
        v1 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(v1)
        write(os.path.join(tmp, "README.md"), "line one\nline two\nline three\n")
        origins = {"claim:ok": "claim", "claim:gone": "claim"}
        bad = []
        for qid, answer in V1_ANSWERS.items():
            if qid == "1.1.6":
                continue                      # cites past the end of a 3-line file by design
            try:
                v1.read_answer(qid, answer, Path(tmp).resolve(), origins)
            except (ValueError, OSError) as exc:
                bad.append("%s: %s" % (qid, exc))
        check("fixture answers are what v1 read_answer accepted", not bad, "; ".join(bad))
    except Exception as exc:                                # noqa: BLE001
        print("skip v1 reader comparison (%s)" % exc)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def dry_run_tests(tmp):
    root, build = legacy_build(tmp)
    before = snapshot(build)
    code, out, err = migrate(root, build)
    check("dry run exits 0", code == 0, out + err)
    lines = [l for l in out.splitlines() if l.startswith("would")]
    check("dry run prints one line per legacy artifact", len(lines) == 3, out)
    for name in ("manual-analysis.json", "prose-review.jsonl", "publish-seal.json"):
        check("dry run names %s with its version" % name,
              any(name in l and "(version 1)" in l for l in lines), out)
    check("dry run changes no byte or mtime, and appends no timings",
          snapshot(build) == before)
    check("dry run says nothing was written", "nothing was written" in out, out)
    check("dry run reports the answer that would not pass, with read_answer's message",
          "1.1.5: cites claim:gone, which nothing in this run verified" in out
          and "1.1.6: evidence line range exceeds file" in out, out)


def mapping_tests(tmp):
    root, build = legacy_build(tmp, "mapping")
    code, out, err = migrate(root, build, "--apply")
    check("apply exits 0", code == 0, out + err)
    path = os.path.join(build, "manual-analysis.json")
    new = json.loads(read(path))
    old = json.loads(read(os.path.join(build, "manual-analysis.v1.json")))
    check("manual_version becomes 2", new["manual_version"] == 2)
    check("index_hash, template and prefilled are carried",
          all(new[k] == old[k] for k in ("index_hash", "template", "prefilled")))
    check("no template_hash is invented", "template_hash" not in new)
    check("pages are unchanged", new["pages"] == old["pages"])
    expected = {"confirmed": ("observed", "partial"), "inferred": ("inferred", "partial"),
                "unknown": ("unknown", "unanswered"),
                "not_applicable": ("not_applicable", "unanswered")}
    for qid, answer in old["answers"].items():
        moved = new["answers"][qid]
        basis, completeness = expected[answer["status"]]
        check("%s maps %s to %s/%s" % (qid, answer["status"], basis, completeness),
              (moved["basis"], moved["completeness"]) == (basis, completeness)
              and "status" not in moved)
        check("%s keeps text, evidence, verified_ids, next_check and reviewer" % qid,
              all(moved.get(k) == answer.get(k) for k in
                  ("text", "evidence", "verified_ids", "next_check", "reviewer")))
        check("%s is pending review and not complete" % qid,
              moved["content_review"] == "pending" and moved["completeness"] != "complete")
        partial = moved["completeness"] == "partial"
        check("%s carries the facets marker exactly when partial" % qid,
              (moved.get("facets_missing") == [MARKER]) if partial
              else "facets_missing" not in moved)
        check("%s adds no other field" % qid,
              set(moved) - set(answer) <= {"basis", "completeness", "content_review",
                                           "facets_missing"})
    resolved = Path(root).resolve()
    origins = {"claim:ok": "claim"}
    for qid in ("1.1.1", "1.1.2", "1.1.3", "1.1.4"):
        try:
            manual.read_answer(qid, new["answers"][qid], resolved, origins)
            ok = True
        except ValueError as exc:
            ok = False
            print(exc)
        check("read_answer accepts migrated %s" % qid, ok)
    # Failure case: nothing is dropped, nothing is weakened to make it pass.
    gone = new["answers"]["1.1.5"]
    check("an answer that no longer validates is kept as it was",
          gone["basis"] == "observed" and gone["verified_ids"] == ["claim:gone"]
          and gone["text"] == "Names a retired id." and gone["evidence"] == EVIDENCE)
    check("the report names it with read_answer's message",
          "1.1.5: cites claim:gone, which nothing in this run verified" in out, out)
    check("the report counts the migrated answers", "6 answer(s) migrated" in out, out)
    try:
        manual.build({"index_hash": "sha256:s"}, old, None, root)
        refused = ""
    except ValueError as exc:
        refused = str(exc)
    check("manual.build still refuses the v1 original, naming the command",
          "pipeline.py migrate" in refused, refused)


def review_tests(tmp):
    root, build = legacy_build(tmp, "reviews")
    original = read(os.path.join(build, "prose-review.jsonl")).decode().splitlines(True)
    code, out, err = migrate(root, build, "--apply")
    check("review apply exits 0", code == 0, out + err)
    legacy = read(os.path.join(build, "prose-review.v1.jsonl")).decode()
    check("v1 rows are in prose-review.v1.jsonl exactly as they were, in order",
          legacy == original[0] + original[2], legacy)
    kept = read(os.path.join(build, "prose-review.jsonl")).decode()
    check("the review file keeps only the v2 rows, in their order",
          kept == original[1] + original[3], kept)
    rows = [json.loads(l) for l in kept.splitlines()]
    check("review_records reads every remaining row without error",
          all(review_records.malformed(r) is None for r in rows))
    named = {r.get("target_id") for r in rows}
    check("no block a v1 row named counts as reviewed",
          not ({"block:a", "block:c"} & named))
    root2, build2 = legacy_build(tmp, "only-v2")
    write(os.path.join(build2, "prose-review.jsonl"), json.dumps(V2_ROW) + "\n")
    migrate(root2, build2, "--apply")
    check("a review file with no v1 rows is not touched",
          not os.path.exists(os.path.join(build2, "prose-review.v1.jsonl")))
    # --review picks another file, and the moved rows sit beside it.
    root3, build3 = legacy_build(tmp, "review-flag")
    other = os.path.join(root3, "my-review.jsonl")
    write(other, json.dumps(V1_ROWS[0]) + "\n" + json.dumps(V2_ROW) + "\n")
    os.remove(os.path.join(build3, "prose-review.jsonl"))
    code, out, err = migrate(root3, build3, "--review", other, "--apply")
    check("--review migrates the named file",
          code == 0 and os.path.exists(os.path.join(root3, "my-review.v1.jsonl"))
          and json.loads(read(other).decode().splitlines()[0])["review_id"] == "r1", out + err)


def seal_tests(tmp):
    root, build = legacy_build(tmp, "seal")
    migrate(root, build, "--apply")
    check("a v1 seal is renamed and nothing is written in its place",
          not os.path.exists(os.path.join(build, "publish-seal.json"))
          and json.loads(read(os.path.join(build, "publish-seal.v1.json")))["seal_version"] == 1)
    # `publish`'s own gate still refuses a v1 seal with its existing message.
    seal = os.path.join(root, "seal.json")
    write(seal, json.dumps({"seal_version": 1, "revision": "rev-0001"}))
    for name in ("draft", "drafts"):
        os.makedirs(os.path.join(root, name), exist_ok=True)
    for name in ("doc.json", "report.json"):
        write(os.path.join(root, name), "{}")
    proc = subprocess.run(
        [sys.executable, script("promote_docs.py"), "--draft", os.path.join(root, "draft"),
         "--doc", os.path.join(root, "doc.json"), "--report", os.path.join(root, "report.json"),
         "--seal", seal, "--drafts", os.path.join(root, "drafts"),
         "--target", os.path.join(root, "out")], capture_output=True, text=True)
    check("promote_docs refuses a v1 seal with its `run review again` message",
          proc.returncode == 1 and "run review again" in proc.stderr, proc.stderr)


def originals_tests(tmp):
    root, build = legacy_build(tmp, "orig")
    manual_bytes = read(os.path.join(build, "manual-analysis.json"))
    seal_bytes = read(os.path.join(build, "publish-seal.json"))
    migrate(root, build, "--apply")
    check("the manual original is kept byte for byte",
          read(os.path.join(build, "manual-analysis.v1.json")) == manual_bytes)
    check("the seal original is kept byte for byte",
          read(os.path.join(build, "publish-seal.v1.json")) == seal_bytes)
    code, out, _err = migrate(root, build)
    check("a second migrate prints `nothing to migrate` and exits 0",
          code == 0 and "nothing to migrate" in out, out)
    code, out, _err = migrate(root, build, "--apply")
    check("a second --apply changes nothing", code == 0 and "nothing to migrate" in out, out)
    leftovers = [n for n in os.listdir(build) if ".migrating" in n]
    check("no temporary file is left behind", not leftovers, str(leftovers))
    check("timings.jsonl is not appended",
          read(os.path.join(build, "timings.jsonl")) == b'{"stage": "x"}\n')

    # A pre-existing .v1 with different content refuses the whole migration.
    root, build = legacy_build(tmp, "conflict")
    write(os.path.join(build, "prose-review.v1.jsonl"), "someone else's file\n")
    before = snapshot(build)
    code, out, err = migrate(root, build, "--apply")
    check("a conflicting .v1 file exits non-zero and names the file",
          code != 0 and "prose-review.v1.jsonl" in err, out + err)
    check("a conflicting .v1 file changes nothing", snapshot(build) == before)

    # A failure part-way through putting files in place leaves the build as it was.
    root, build = legacy_build(tmp, "rollback")
    before = snapshot(build)
    blocker = os.path.join(build, "publish-seal.v1.json.migrating")
    os.makedirs(blocker)                                  # a directory cannot become a file
    code, out, err = migrate(root, build, "--apply")
    shutil.rmtree(blocker)
    check("a failure part-way leaves the build as it was",
          code != 0 and snapshot(build) == before, out + err)


def unknown_version_tests(tmp):
    root, build = legacy_build(tmp, "unknown")
    write(os.path.join(build, "manual-analysis.json"), json.dumps({"manual_version": 7}))
    write(os.path.join(build, "publish-seal.json"), json.dumps({"seal_version": 9}))
    os.remove(os.path.join(build, "prose-review.jsonl"))
    before = snapshot(build)
    code, out, err = migrate(root, build, "--apply")
    check("an unrecognised version is listed as not migrated and left untouched",
          code == 0 and out.count("unknown version: not migrated") == 2
          and snapshot(build) == before, out + err)


def notes_tests(tmp):
    root, build = legacy_build(tmp, "notes")
    os.remove(os.path.join(build, "scope.json"))
    write(os.path.join(build, "render-manifest.json"),
          json.dumps({"render_manifest_version": 1}))
    code, out, _err = migrate(root, build)
    check("no scope.json names `survey`", "run `survey`" in out, out)
    check("rendered output with no drafts/ names `render`",
          "no drafts/" in out and "run `render`" in out, out)
    migrate(root, build, "--apply")
    check("neither file is created",
          not os.path.exists(os.path.join(build, "scope.json"))
          and not os.path.exists(os.path.join(build, "drafts")))
    os.makedirs(os.path.join(build, "drafts"))
    code, out, _err = migrate(root, build)
    check("an older render manifest names `render`",
          "render-manifest.json is version 1" in out, out)
    check("a build with nothing legacy says nothing to migrate", "nothing to migrate" in out)


def no_build_tests(tmp):
    root = os.path.join(tmp, "empty")
    os.makedirs(root)
    code, out, err = migrate(root, os.path.join(root, ".docs-build"))
    check("no build exits 0 with the `no scan yet` line",
          code == 0 and "no scan yet" in out, out + err)
    check("no build creates no directory", not os.path.exists(os.path.join(root, ".docs-build")))


def pure_tests():
    migrated, _report = migrate_build.migrate_manual({"manual_version": 2})
    check("migrate_manual leaves a v2 file alone", migrated is None)
    migrated, report = migrate_build.migrate_manual(
        {"manual_version": 1, "answers": {"q": {"status": "mystery", "text": "t"},
                                          "r": "not an object"}})
    check("an answer with an unknown status is left as found and named",
          migrated["answers"]["q"] == {"status": "mystery", "text": "t"}
          and sorted(report["left"]) == ["q", "r"])
    kept, legacy, unknown = migrate_build.migrate_reviews(
        [json.dumps({"page": "p"}) + "\n", "not json\n", json.dumps(V2_ROW) + "\n",
         json.dumps({"review_version": 3}) + "\n"])
    check("migrate_reviews keeps what it does not know, in order",
          len(legacy) == 1 and len(kept) == 3 and unknown == 1 and kept[0] == "not json\n")


def main():
    tmp = tempfile.mkdtemp(prefix="migrate-test-")
    try:
        v1_fixture_matches_v1_reader()
        pure_tests()
        dry_run_tests(tmp)
        mapping_tests(tmp)
        review_tests(tmp)
        seal_tests(tmp)
        originals_tests(tmp)
        unknown_version_tests(tmp)
        notes_tests(tmp)
        no_build_tests(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print()
    if FAILURES:
        print("FAILED %d check(s): %s" % (len(FAILURES), ", ".join(FAILURES)))
        return 1
    print("all migrate checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
