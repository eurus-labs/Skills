#!/usr/bin/env python3
"""Plan 14 end to end: the scope fixture taken through survey, check, document, render,
review and publish with the pipeline driver.

What the unit tests cannot show is that the pieces join: a symbol-free entry module and an
empty package marker are units now, so every stage between the survey and the seal has to
accept them, and a run whose batch is smaller than the product has to say so and refuse to
seal rather than publish a manual that does not cover the product.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

from component_scripts import script
import scope_fixture

PIPELINE = script("pipeline.py")

# Distinct on purpose: the analysis checker rejects a set of readings that differ only in
# their nouns. Each names something in the file it describes.
TEXT = {
    "src/shop/invoice.py": {
        "responsibility": "render turns a basket into the printed total using show from money.",
        "state": "render keeps nothing between calls and reads only the basket it is given.",
        "interface": "render is the single public function and takes one basket argument.",
        "failure": "render raises AttributeError when the basket lacks a total method."},
    "src/shop/money.py": {
        "responsibility": "to_cents converts a price into whole cents and show prints cents again.",
        "state": "to_cents and show hold no module state at all, both are pure functions.",
        "interface": "to_cents and show are the two functions the cart and invoice import.",
        "failure": "to_cents silently rounds half cents, and show never raises on negative cents."},
    "src/shop/cart.py": {
        "responsibility": "Cart collects lines with add and sums them in total using to_cents.",
        "state": "Cart keeps its lines list on the instance and nothing else survives a call.",
        "interface": "Cart exposes add with sku price quantity, and total returning cents.",
        "failure": "add fails with a TypeError when price is not a number."},
    "src/shop/contest.py": {
        "responsibility": "enter strips whitespace from a contestant name before use.",
        "state": "contest has no state, enter is a pure function over its argument.",
        "interface": "enter is the one public function and takes a single name string.",
        "failure": "enter raises AttributeError when the name is not a string."},
    "src/latest/feed.py": {
        "responsibility": "newest sorts the items and returns the first count of them as the feed.",
        "state": "feed holds no state, newest works on the list it receives only.",
        "interface": "newest takes items and count and returns a list slice.",
        "failure": "newest raises TypeError when the items cannot be compared with each other."},
    # No symbol in these three: one statement each, saying what the file does.
    "src/shop/runner.py": {
        "responsibility": "Entry point: runs the invoice printer from the command line."},
    "src/latest/__init__.py": {
        "responsibility": "Package marker for the latest feed package, empty by design."},
    "src/shop/__init__.py": {
        "responsibility": "Package marker that makes shop importable and defines nothing itself."},
}


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


class Run(object):
    def __init__(self, top):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = scope_fixture.write(self.tmp.name)
        self.build = os.path.join(self.root, ".docs-build")
        self.top = top

    def pl(self, *argv):
        done = subprocess.run([sys.executable, PIPELINE] + list(argv) + ["--root", self.root],
                              cwd=self.root, capture_output=True, text=True)
        return done

    def survey(self):
        """`survey` with the `--top` this run was given; `None` is the default, no flag."""
        return self.pl("survey", *(["--top", self.top] if self.top is not None else []))

    def decide(self, checkpoint, note):
        done = self.pl("decide", "--checkpoint", checkpoint, "--note", note)
        assert done.returncode == 0, done.stdout + done.stderr

    def write_analysis(self, units):
        index = json.loads(read(os.path.join(self.build, "structure.json")))
        records = {r["path"]: r for r in index["files"]}
        claims = [json.loads(l) for l in read(os.path.join(self.build, "claims.jsonl")).split("\n")
                  if l.strip()]
        rows, fragments, number = [], [], 0
        for unit in units:
            record = records[unit]
            statements = []
            for kind, text in TEXT[unit].items():
                number += 1
                statements.append({
                    "id": "s%d" % number, "kind": kind, "status": "observed", "text": text,
                    "evidence": [{"path": unit, "line_start": 1,
                                  "line_end": min(record["loc"], 3),
                                  "source_hash": record["source_hash"]}]})
            rows.append({"analysis_version": 1, "path": unit,
                         "source_hash": record["source_hash"],
                         "index_hash": index["index_hash"], "role": "role of " + unit,
                         "statements": statements})
            # A symbol-free file has no derived claim to cite, so its fragment cites none.
            own = [] if not record["symbols"] else [c["id"] for c in claims if unit in c["id"]][:2]
            fragments.append({"fragment_id": "fragment:" + unit, "source": unit,
                              "role": "role of " + unit, "claim_ids": own,
                              "status": "candidate", "index_hash": index["index_hash"]})
        for name, items in (("module-analysis.jsonl", rows), ("fragments.jsonl", fragments)):
            with open(os.path.join(self.build, name), "w", encoding="utf-8") as fh:
                fh.write("".join(json.dumps(i) + "\n" for i in items))

    def through_review(self, after_survey=None):
        steps = []
        steps.append(self.survey())
        if after_survey:
            after_survey(self)
        self.decide("P1", "the scope and its classification look right to the user")
        steps.append(self.pl("template", "--use", "onboarding", "--note",
                             "the user chose the onboarding preset"))
        steps.append(self.pl("analyze"))
        self.units = read(os.path.join(self.build, "units.txt")).split()
        self.write_analysis(self.units)
        self.decide("P2", "the roles match the repository as the user sees it")
        steps.append(self.pl("check"))
        self.decide("P3", "the boundaries are where the user expects them")
        steps.append(self.pl("document"))
        steps.append(self.pl("render", "--docs", "docs"))
        steps.append(self.pl("review"))
        return steps


class WholeProduct(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.run_ = Run(None)
        cls.steps = cls.run_.through_review()
        cls.report = json.loads(read(os.path.join(cls.run_.build, "generation-report.json")))

    @classmethod
    def tearDownClass(cls):
        cls.run_.tmp.cleanup()

    def test_every_stage_accepts_the_symbol_free_units(self):
        for step in self.steps:
            self.assertEqual(step.returncode, 0, step.stdout[-1500:] + step.stderr[-1500:])
        self.assertIn("src/shop/runner.py", self.run_.units)
        self.assertIn("src/shop/__init__.py", self.run_.units)
        self.assertEqual(len(self.run_.units), 8)

    def test_a_default_run_reads_every_product_file_in_one_batch(self):
        scope = json.loads(read(os.path.join(self.run_.build, "scope.json")))
        product = sorted(r["path"] for r in scope["files"] if r["disposition"] == "product")
        self.assertEqual(sorted(self.run_.units), product)
        self.assertEqual({r.get("batch") for r in scope["files"]
                          if r["disposition"] == "product"}, {1})
        options = json.loads(read(os.path.join(self.run_.build, "selection-options.json")))
        self.assertIsNone(options["top"])

    def test_the_gate_passes_and_the_scope_is_complete(self):
        self.assertEqual(self.report["status"], "passed", self.report["reasons"])
        self.assertTrue(self.report["scope"]["complete"])
        self.assertEqual(self.report["scope"]["unread"], [])
        self.assertEqual(self.report["editions"]["status"], "passed")

    def test_reading_state_followed_the_ledger(self):
        scope = json.loads(read(os.path.join(self.run_.build, "scope.json")))
        states = {r["reading"] for r in scope["files"] if r["disposition"] == "product"}
        self.assertEqual(states, {"analyzed"})

    def test_publish_promotes_one_tree_with_the_audit_blocks_in_it(self):
        done = self.run_.pl("publish", "--docs", "docs")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        docs = os.path.join(self.run_.root, "docs")
        self.assertIn(".. only:: audit", read(os.path.join(docs, "modules.rst")))
        every = [n.lower() for _root, dirs, files in os.walk(self.run_.root)
                 for n in dirs + files]
        self.assertFalse([n for n in every if "audit" in n], every)
        self.assertNotIn("docs-audit", os.listdir(self.run_.root))
        for page in os.listdir(docs):
            if page.endswith(".rst"):
                text = read(os.path.join(docs, page))
                self.assertNotIn("tests/test_cart.py", text, page)
                self.assertNotIn("schema_pb2", text, page)


class FirstBatchOnly(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.run_ = Run("2")
        cls.steps = cls.run_.through_review()
        cls.report = json.loads(read(os.path.join(cls.run_.build, "generation-report.json")))

    @classmethod
    def tearDownClass(cls):
        cls.run_.tmp.cleanup()

    def test_the_run_says_incomplete_and_names_what_is_unread(self):
        self.assertEqual(self.report["status"], "partial")
        self.assertFalse(self.report["scope"]["complete"])
        self.assertIn("src/latest/feed.py", self.report["scope"]["unread"])
        self.assertTrue(any(r.startswith("incomplete: 5 product file(s) unread")
                            for r in self.report["reasons"]), self.report["reasons"])

    def test_a_draft_that_leaves_the_product_unread_is_not_sealed(self):
        review = self.steps[-1]
        self.assertEqual(review.returncode, 1)
        self.assertIn("not passed", review.stdout + review.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.run_.build, "publish-seal.json")))

    def test_status_names_the_unread_files(self):
        done = self.run_.pl("status")
        self.assertIn("incomplete: 5 product file(s) unread", done.stdout)
        self.assertIn("src/latest/feed.py", done.stdout)


class NarrowedAtP1(unittest.TestCase):
    """The one way a run that reads less than the whole product may still be sealed."""

    @staticmethod
    def narrow(run):
        path = os.path.join(run.build, "scope.json")
        scope = json.loads(read(path))
        for row in scope["files"]:
            if row["disposition"] == "product" and row.get("batch", 1) > 1:
                row.update(disposition="asset", reading="excluded",
                           reason="left out of this edition",
                           override="the user narrowed the scope at P1")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(scope, fh)
        # Editing the scope changes what P1 asks about, so the survey is run again; the
        # rows a person changed are kept, and P1 reopens on the narrower material.
        again = run.survey()
        assert again.returncode == 0, again.stdout + again.stderr

    def test_a_deliberately_narrower_draft_passes_and_records_the_change(self):
        run = Run("2")
        self.addCleanup(run.tmp.cleanup)
        steps = run.through_review(after_survey=self.narrow)
        self.assertEqual(steps[-1].returncode, 0, steps[-1].stdout[-1500:])
        report = json.loads(read(os.path.join(run.build, "generation-report.json")))
        self.assertEqual(report["status"], "passed", report["reasons"])
        self.assertTrue(report["scope"]["complete"])
        self.assertEqual(len(report["scope"]["narrowed"]), 5)
        self.assertTrue(any("scope narrowed by a person" in r for r in report["reasons"]))
        status = run.pl("status").stdout
        self.assertIn("narrowed src/latest/feed.py -> asset", status)


if __name__ == "__main__":
    unittest.main()
