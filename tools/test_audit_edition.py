#!/usr/bin/env python3
"""Plan 14, group C: citations live in `evidence`; one source builds a reader edition and an
audit edition."""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from component_scripts import component_paths, script
sys.path[:0] = component_paths()
import check_prose
import citations
import editions
import render_docs

CART = {"path": "src/shop/cart.py", "line_start": 4, "line_end": 9}
MONEY = {"path": "src/shop/money.py", "line_start": 2, "line_end": 2}
RUNNER = {"path": "src/shop/runner.py", "line_start": 3, "line_end": 3}

DOC = {
    "format_version": 2, "preset": "onboarding", "index_hash": "sha256:x",
    "claims": [{"id": "claim:imports:a", "status": "verified", "kind": "imports",
                "evidence": [RUNNER]}],
    "statements": [{"id": "stmt:money", "kind": "responsibility", "status": "observed",
                    "text": "Money is held in cents.", "evidence": [MONEY]}],
    "pages": [{"id": "overview", "title": "Overview", "order": 1, "blocks": [
        {"id": "block:intro", "type": "prose",
         "text": "The cart adds lines and totals them.", "evidence": [CART]},
        {"id": "block:plain", "type": "prose", "text": "Nothing here cites anything."},
        {"id": "block:generated", "type": "prose",
         "text": "src/shop/money.py -- Money is held in cents. (Read at "
                 "src/shop/money.py:2)", "analysis_refs": ["stmt:money"]},
        {"id": "block:composed", "type": "prose", "manual_block": True,
         "text": "Orders are totalled in cents.\n\nSource code: src/shop/cart.py:4-9",
         "evidence": [CART]},
        {"id": "block:edges", "type": "table", "columns": ["From", "Imports", "At"],
         "rows": [["src/shop/runner.py", "src/shop/invoice.py", "src/shop/runner.py:3"],
                  ["src/shop/invoice.py", "src/shop/cart.py", "src/shop/invoice.py:1"]],
         "claim_refs": ["claim:imports:a"]},
        {"id": "block:next", "type": "ref", "target": "details"}]},
        {"id": "details", "title": "Details", "order": 2, "blocks": [
            {"id": "block:d", "type": "prose", "text": "No citations on this page."}]}],
}

SPHINX = shutil.which("sphinx-build") is not None


def render(root, fmt, doc=None):
    doc_path = os.path.join(root, "doc.json")
    with open(doc_path, "w", encoding="utf-8") as fh:
        json.dump(doc or DOC, fh)
    out = os.path.join(root, "stage-" + fmt)
    done = subprocess.run(
        [sys.executable, script("render_docs.py"), "--doc", doc_path, "--out", out,
         "--format", fmt, "--assume-parser"] + (["--write-conf"] if SPHINX else []),
        capture_output=True, text=True)
    return done, out


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


class Rendering(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.rst_done, cls.rst = render(cls.tmp.name, "rst")
        cls.md_done, cls.md = render(cls.tmp.name, "myst")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_both_formats_render(self):
        self.assertEqual(self.rst_done.returncode, 0, self.rst_done.stderr)
        self.assertEqual(self.md_done.returncode, 0, self.md_done.stderr)

    def test_the_reader_source_cites_nothing_in_either_format(self):
        for out, ext in ((self.rst, ".rst"), (self.md, ".md")):
            reader, audit = editions.split_editions(read(os.path.join(out, "overview" + ext)),
                                                    ext)
            self.assertEqual(citations.inline_in(reader), [], ext)
            self.assertNotIn("Source", reader, ext)
            self.assertEqual(len(audit), 4, ext)

    def test_the_audit_blocks_use_the_sphinx_only_directive(self):
        self.assertIn(".. only:: audit", read(os.path.join(self.rst, "overview.rst")))
        self.assertIn("```{only} audit", read(os.path.join(self.md, "overview.md")))

    def test_every_blocks_evidence_is_in_its_audit_block(self):
        text = read(os.path.join(self.rst, "overview.rst"))
        _, audit = editions.split_editions(text, ".rst")
        joined = "\n".join(audit)
        for expected in ("src/shop/cart.py:4-9", "src/shop/money.py:2",
                         "src/shop/runner.py:3", "src/shop/invoice.py:1"):
            self.assertIn("``%s``" % expected, joined)
        # A claim the block refers to is cited through it.
        self.assertIn("src/shop/runner.py:3", audit[-1])

    def test_a_table_keeps_its_rows_and_drops_the_location_column_for_the_reader(self):
        text = read(os.path.join(self.rst, "overview.rst"))
        reader, audit = editions.split_editions(text, ".rst")
        self.assertIn("src/shop/runner.py", reader)
        self.assertNotIn("   * - At", reader)
        self.assertNotIn("\n     - At", reader)
        # The audit edition says which row each location belongs to.
        self.assertIn("src/shop/runner.py / src/shop/invoice.py: ``src/shop/runner.py:3``",
                      "\n".join(audit))

    def test_generated_parentheticals_and_the_source_paragraph_are_moved_not_lost(self):
        reader, _ = editions.split_editions(read(os.path.join(self.rst, "overview.rst")),
                                            ".rst")
        self.assertIn("Money is held in cents.", reader)
        self.assertNotIn("Read at", reader)
        self.assertIn("Orders are totalled in cents.", reader)
        self.assertNotIn("Source code", reader)

    def test_a_block_with_nothing_to_cite_renders_as_it_always_did(self):
        reader, _ = editions.split_editions(read(os.path.join(self.rst, "overview.rst")),
                                            ".rst")
        self.assertIn("Nothing here cites anything.\n", reader)
        self.assertEqual(read(os.path.join(self.rst, "details.rst")).count("only"), 0)

    def test_no_second_tree_is_written(self):
        entries = os.listdir(self.tmp.name)
        self.assertFalse([e for e in entries if "audit" in e.lower()], entries)
        self.assertEqual(sorted(e for e in entries if e.startswith("stage-")),
                         ["stage-myst", "stage-rst"])


class EditionCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        _, self.out = render(self.tmp.name, "rst")
        self.context = {"claims": {c["id"]: c for c in DOC["claims"]},
                        "statements": {s["id"]: s for s in DOC["statements"]}}

    def verdict(self, build=False):
        return editions.check(self.out, DOC, ".rst", (), self.context, build=build)

    def test_the_rendered_tree_passes(self):
        verdict = self.verdict()
        self.assertEqual(verdict["problems"], [])
        self.assertEqual(verdict["status"], "passed")

    def test_a_citation_in_the_readers_text_is_a_leak(self):
        path = os.path.join(self.out, "overview.rst")
        Path(path).write_text(read(path).replace(
            "Nothing here cites anything.", "See src/shop/cart.py:30 for this."))
        verdict = self.verdict()
        self.assertEqual(verdict["status"], "failed")
        self.assertTrue(any("src/shop/cart.py:30" in p and "reader edition" in p
                            for p in verdict["problems"]), verdict)

    def test_a_cited_block_without_its_audit_block_is_found(self):
        path = os.path.join(self.out, "overview.rst")
        text = read(path)
        start = text.index(".. only:: audit")
        end = text.index("\n\n", text.index("   - ", start))
        Path(path).write_text(text[:start] + text[end:])
        verdict = self.verdict()
        self.assertEqual(verdict["status"], "failed")
        self.assertTrue(any("audit block" in p for p in verdict["problems"]), verdict)

    def test_an_authored_scaffold_is_not_held_to_it(self):
        Path(self.out, "troubleshooting.rst").write_text(
            "Troubleshooting\n===============\n\nSee src/shop/cart.py:4 for the cart.\n")
        self.assertEqual(self.verdict()["problems"], [])

    @unittest.skipUnless(SPHINX, "sphinx-build is not installed")
    def test_real_builds_agree_with_the_source(self):
        verdict = self.verdict(build=True)
        self.assertEqual(verdict["problems"], [], verdict)
        self.assertIn("reader build and an audit build", verdict["detail"])

    @unittest.skipUnless(SPHINX, "sphinx-build is not installed")
    def test_a_reader_build_shows_no_path_and_line_and_an_audit_build_shows_all(self):
        import sphinx_support
        reader = sphinx_support.build_text(self.out, ())
        audit = sphinx_support.build_text(self.out, (), ("audit",))
        self.assertEqual(citations.inline_in(reader["overview.txt"]), [])
        self.assertNotIn("Source:", reader["overview.txt"])
        for expected in ("src/shop/cart.py:4-9", "src/shop/money.py:2",
                         "src/shop/runner.py:3"):
            self.assertIn(expected, audit["overview.txt"])
            self.assertNotIn(expected, reader["overview.txt"])

    @unittest.skipUnless(SPHINX, "sphinx-build is not installed")
    def test_the_render_check_runs_the_editions_check(self):
        done = subprocess.run(
            [sys.executable, script("render_docs.py"), "--doc",
             os.path.join(self.tmp.name, "doc.json"), "--out", self.out + "-checked",
             "--format", "rst", "--write-conf", "--check"],
            capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("editions: passed", done.stdout)


class PublishWritesNoSecondTree(unittest.TestCase):
    def test_promotion_carries_the_audit_blocks_in_the_one_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build, docs, draft = root / "build", root / "docs", root / "build/rendered-docs"
            build.mkdir()
            docs.mkdir()
            doc_path = build / "doc.json"
            doc_path.write_text(json.dumps(DOC))

            def invoke(name, *args):
                return subprocess.run([sys.executable, script(name), *map(str, args)],
                                      capture_output=True, text=True)

            self.assertEqual(invoke("prepare_stage.py", "--source", docs,
                                    "--out", draft).returncode, 0)
            rendered = invoke("render_docs.py", "--doc", doc_path, "--out", draft)
            self.assertEqual(rendered.returncode, 0, rendered.stderr)
            manifest, report, seal = (build / "render-manifest.json",
                                      build / "generation-report.json",
                                      build / "publish-seal.json")
            report.write_text(json.dumps({"status": "passed"}))
            self.assertEqual(invoke("snapshot_draft.py", "--draft", draft, "--doc", doc_path,
                                    "--out", manifest).returncode, 0)
            self.assertEqual(invoke("snapshot_revision.py", "--draft", draft, "--manifest",
                                    manifest, "--drafts", build / "drafts").returncode, 0)
            sealed = invoke("seal_draft.py", "--draft", draft, "--doc", doc_path, "--report",
                            report, "--render-manifest", manifest, "--drafts",
                            build / "drafts", "--out", seal)
            self.assertEqual(sealed.returncode, 0, sealed.stderr)
            done = invoke("promote_docs.py", "--draft", draft, "--target", docs, "--doc",
                          doc_path, "--report", report, "--seal", seal, "--drafts",
                          build / "drafts")
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertIn(".. only:: audit", (docs / "overview.rst").read_text())
            names = [p.name.lower() for p in root.rglob("*")]
            self.assertFalse([n for n in names if "audit" in n], names)
            self.assertEqual(sorted(p.name for p in root.iterdir()), ["build", "docs"])


class ProseCheck(unittest.TestCase):
    def findings(self, text, **extra):
        doc = {"claims": [], "statements": [], "pages": [{"id": "p", "blocks": [
            dict({"id": "b", "type": "prose", "text": text}, **extra)]}]}
        checker = check_prose.Checker(doc)
        checker.check(doc)
        return [f for f in checker.findings if f["code"] == "P009"]

    def test_a_block_with_path_and_line_in_its_text_is_flagged_as_advisory(self):
        found = self.findings("The cart is totalled at src/shop/cart.py:4 in cents.")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["severity"], "advisory")
        self.assertIn("evidence", found[0]["message"])

    def test_clean_prose_is_not(self):
        self.assertEqual(self.findings("The cart is totalled in cents.",
                                       evidence=[CART]), [])

    def test_what_the_renderer_moves_out_is_not_the_writers_fault(self):
        self.assertEqual(self.findings("Money is held in cents. (Read at "
                                       "src/shop/money.py:2)"), [])
        self.assertEqual(self.findings("Totalled in cents.\n\nSource code: "
                                       "src/shop/cart.py:4-9"), [])

    def test_a_host_and_port_is_not_a_citation(self):
        self.assertEqual(self.findings("It listens on example.com:8080 by default."), [])

    def test_the_code_is_in_the_catalog(self):
        import findings
        self.assertIn('"P009"', read(findings.__file__))


class Patterns(unittest.TestCase):
    def test_what_counts_as_a_citation(self):
        for text in ("src/a.py:12", "a/b/c.go:3-9", "setup.py:1", "docs/x.cfg:7"):
            self.assertTrue(citations.CITATION.search(text), text)
        for text in ("example.com:8080", "at 12:30", "step:4", "http://x.org/path:3x"):
            self.assertIsNone(citations.CITATION.search(text), text)

    def test_evidence_formats(self):
        self.assertEqual(citations.format_item(CART), "src/shop/cart.py:4-9")
        self.assertEqual(citations.format_item(MONEY), "src/shop/money.py:2")

    def test_the_review_hash_is_untouched_by_rendering(self):
        import review_records
        before = review_records.content_hash(DOC["pages"][0]["blocks"][0])
        copy.deepcopy(DOC)
        render_docs.render_page(DOC["pages"][0], {"details": "Details"}, render_docs.Rst(),
                                {"claims": {}, "statements": {}})
        self.assertEqual(before, review_records.content_hash(DOC["pages"][0]["blocks"][0]))


if __name__ == "__main__":
    unittest.main()
