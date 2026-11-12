#!/usr/bin/env python3
"""Each plugin must carry the manifest Claude Code reads, identical to the Copilot one.

`claude plugin eval` resolves a plugin from plugin.json or .claude-plugin/plugin.json. This
repository's manifests live at .github/plugin/plugin.json, so before the copy existed every
eval ran against "none resolved": Claude Code with no plugin, scoring nothing.

    python3 tools/test_claude_manifest.py
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import validate  # noqa: E402

MANIFEST = {"name": "demo", "description": "A demo.", "version": "0.1.0", "skills": ["./skills/demo/"]}


class ClaudeManifest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.plugin = root / "plugins" / "demo"
        (self.plugin / ".github" / "plugin").mkdir(parents=True)
        (self.plugin / "skills" / "demo").mkdir(parents=True)
        (self.plugin / "skills" / "demo" / "SKILL.md").write_text("---\nname: demo\ndescription: x\n---\n")
        (self.plugin / ".github" / "plugin" / "plugin.json").write_text(json.dumps(MANIFEST))
        for target, value in (("REPO", str(root)), ("PLUGINS", str(root / "plugins")),
                              ("FAILURES", []), ("WARNINGS", [])):
            patcher = patch.object(validate, target, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def run_check(self):
        validate.check_plugin("demo")
        return "\n".join(validate.FAILURES)

    def mirror(self, data):
        (self.plugin / ".claude-plugin").mkdir(exist_ok=True)
        (self.plugin / ".claude-plugin" / "plugin.json").write_text(json.dumps(data))

    def test_a_missing_claude_manifest_fails(self):
        self.assertIn(".claude-plugin/plugin.json", self.run_check())

    def test_an_identical_copy_passes(self):
        self.mirror(MANIFEST)
        self.assertNotIn("claude-plugin", self.run_check())

    def test_a_copy_that_drifted_fails(self):
        self.mirror(dict(MANIFEST, version="0.2.0"))
        self.assertIn("differs from .github/plugin/plugin.json", self.run_check())

    def test_every_real_plugin_has_the_copy(self):
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for name in sorted(os.listdir(os.path.join(repo, "plugins"))):
            github = os.path.join(repo, "plugins", name, ".github", "plugin", "plugin.json")
            claude = os.path.join(repo, "plugins", name, ".claude-plugin", "plugin.json")
            if os.path.isfile(github):
                self.assertTrue(os.path.isfile(claude), "%s has no .claude-plugin/plugin.json" % name)
                with open(github) as a, open(claude) as b:
                    self.assertEqual(json.load(a), json.load(b), name)


if __name__ == "__main__":
    unittest.main()
