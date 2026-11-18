#!/usr/bin/env python3
"""Behavioral contract for isolated render, final review, and publication."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from component_scripts import script


class PublishWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.docs = self.root / "docs"
        self.draft = self.root / "build/rendered-docs"
        self.build = self.root / "build"
        self.drafts = self.build / "drafts"
        self.docs.mkdir()
        (self.docs / "authored.rst").write_text("keep me\n")
        self.doc = self.build / "doc.json"
        self.report = self.build / "generation-report.json"
        self.seal = self.build / "publish-seal.json"
        self.render_manifest = self.build / "render-manifest.json"
        self.build.mkdir(exist_ok=True)
        self.doc.write_text(json.dumps({"format_version": 2, "pages": []}))
        self.report.write_text(json.dumps({"status": "passed"}))

    def invoke(self, name, *args):
        return subprocess.run([sys.executable, script(name), *map(str, args)],
                              capture_output=True, text=True)

    def snapshot(self):
        """snapshot_draft then snapshot_revision, as `render` runs them."""
        first = self.invoke("snapshot_draft.py", "--draft", self.draft, "--doc", self.doc,
                            "--out", self.render_manifest)
        self.assertEqual(first.returncode, 0, first.stderr)
        second = self.invoke("snapshot_revision.py", "--draft", self.draft,
                             "--manifest", self.render_manifest, "--drafts", self.drafts)
        self.assertEqual(second.returncode, 0, second.stderr)

    def seal_draft(self):
        return self.invoke("seal_draft.py", "--draft", self.draft, "--doc", self.doc,
                           "--report", self.report,
                           "--render-manifest", self.render_manifest,
                           "--drafts", self.drafts, "--out", self.seal)

    def promote(self):
        return self.invoke("promote_docs.py", "--draft", self.draft,
                           "--target", self.docs, "--doc", self.doc,
                           "--report", self.report, "--seal", self.seal,
                           "--drafts", self.drafts)

    def test_draft_is_isolated_and_only_a_sealed_revision_is_promoted(self):
        prepared = self.invoke("prepare_stage.py", "--source", self.docs,
                            "--out", self.draft)
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        (self.draft / "generated.rst").write_text("reviewed draft\n")
        self.snapshot()
        self.assertFalse((self.docs / "generated.rst").exists())
        self.assertEqual((self.draft / "authored.rst").read_text(), "keep me\n")

        refused = self.promote()
        self.assertEqual(refused.returncode, 2)
        self.assertFalse((self.docs / "generated.rst").exists())

        sealed = self.seal_draft()
        self.assertEqual(sealed.returncode, 0, sealed.stderr)
        self.assertEqual(json.loads(self.seal.read_text())["revision"], "rev-0001")
        self.assertEqual(json.loads(self.seal.read_text())["seal_version"], 2)
        published = self.promote()
        self.assertEqual(published.returncode, 0, published.stderr)
        self.assertEqual((self.docs / "generated.rst").read_text(), "reviewed draft\n")
        self.assertEqual((self.docs / "authored.rst").read_text(), "keep me\n")

    def test_edit_after_review_invalidates_publication(self):
        self.invoke("prepare_stage.py", "--source", self.docs, "--out", self.draft)
        self.snapshot()
        self.seal_draft()
        (self.draft / "authored.rst").write_text("changed after review\n")
        result = self.promote()
        self.assertEqual(result.returncode, 1)
        self.assertEqual((self.docs / "authored.rst").read_text(), "keep me\n")

    def test_nonpassing_review_cannot_be_sealed(self):
        self.invoke("prepare_stage.py", "--source", self.docs, "--out", self.draft)
        self.snapshot()
        self.report.write_text(json.dumps({"status": "review_required"}))
        result = self.seal_draft()
        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.seal.exists())

    def test_manual_edit_between_render_and_review_is_refused(self):
        self.invoke("prepare_stage.py", "--source", self.docs, "--out", self.draft)
        self.snapshot()
        (self.draft / "authored.rst").write_text("patched directly\n")
        result = self.invoke("validate_draft.py", "--draft", self.draft,
                             "--doc", self.doc, "--manifest", self.render_manifest)
        self.assertEqual(result.returncode, 1)

    def test_tampering_with_a_revision_blocks_promotion(self):
        self.invoke("prepare_stage.py", "--source", self.docs, "--out", self.draft)
        self.snapshot()
        self.assertEqual(self.seal_draft().returncode, 0)
        (self.drafts / "rev-0001" / "authored.rst").write_text("edited in the snapshot\n")
        result = self.promote()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("rev-0001", result.stderr)
        self.assertEqual((self.docs / "authored.rst").read_text(), "keep me\n")

    def test_tampering_with_a_revision_blocks_sealing(self):
        self.invoke("prepare_stage.py", "--source", self.docs, "--out", self.draft)
        self.snapshot()
        (self.drafts / "rev-0001" / "authored.rst").write_text("edited in the snapshot\n")
        result = self.seal_draft()
        self.assertEqual(result.returncode, 1)
        self.assertIn("rev-0001", result.stderr)
        self.assertFalse(self.seal.exists())

    def test_a_draft_rendered_after_review_cannot_be_published(self):
        self.invoke("prepare_stage.py", "--source", self.docs, "--out", self.draft)
        (self.draft / "generated.rst").write_text("first draft\n")
        self.snapshot()
        self.assertEqual(self.seal_draft().returncode, 0)
        # A repair and a second render: a new revision, which holds no seal.
        (self.draft / "generated.rst").write_text("second draft\n")
        self.snapshot()
        self.assertEqual(json.loads(self.render_manifest.read_text())["revision"],
                         "rev-0002")
        result = self.promote()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.docs / "generated.rst").exists())
        self.assertEqual((self.docs / "authored.rst").read_text(), "keep me\n")

    def test_a_version_1_seal_is_refused_with_a_pointer_to_review(self):
        self.invoke("prepare_stage.py", "--source", self.docs, "--out", self.draft)
        self.snapshot()
        self.assertEqual(self.seal_draft().returncode, 0)
        seal = json.loads(self.seal.read_text())
        seal["seal_version"] = 1
        del seal["revision"]
        self.seal.write_text(json.dumps(seal))
        result = self.promote()
        self.assertEqual(result.returncode, 1)
        self.assertIn("run review again", result.stderr)

    def test_sealing_requires_a_revision_in_the_manifest(self):
        self.invoke("prepare_stage.py", "--source", self.docs, "--out", self.draft)
        self.invoke("snapshot_draft.py", "--draft", self.draft, "--doc", self.doc,
                    "--out", self.render_manifest)
        result = self.seal_draft()
        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.seal.exists())


if __name__ == "__main__":
    unittest.main()
