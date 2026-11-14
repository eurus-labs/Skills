#!/usr/bin/env python3
"""Claude Code must be able to install every plugin from this marketplace, as Copilot can.

Claude Code reads its marketplace only from .claude-plugin/marketplace.json and refuses a plugin
whose `source` does not start with "./". Before this file existed, `claude plugin marketplace add`
failed with "Marketplace file not found"; with a copy using "plugins/<name>", install failed with
"source: must start with './'". Copilot accepts "./plugins/<name>" too, so both files are identical.

    python3 tools/test_claude_marketplace.py
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import validate  # noqa: E402


class ClaudeMarketplace(unittest.TestCase):
    def test_the_two_marketplace_files_are_identical(self):
        with open(validate.MARKETPLACE, "rb") as a, open(validate.CLAUDE_MARKETPLACE, "rb") as b:
            self.assertEqual(a.read(), b.read())

    def test_every_source_starts_with_dot_slash(self):
        with open(validate.CLAUDE_MARKETPLACE) as fh:
            catalog = json.load(fh)
        for entry in catalog["plugins"]:
            self.assertEqual(entry["source"], "./plugins/%s" % entry["name"])

    def _check(self, content):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        path = os.path.join(tmp, "marketplace.json")
        if content is not None:
            with open(path, "w") as fh:
                fh.write(content)
        failures = []
        with patch.object(validate, "CLAUDE_MARKETPLACE", path), patch.object(validate, "FAILURES", failures), \
                patch.object(validate, "rel", lambda p: p):
            validate.check_claude_marketplace()
        return failures

    def test_a_missing_copy_fails(self):
        self.assertTrue(self._check(None))

    def test_a_drifted_copy_fails(self):
        with open(validate.MARKETPLACE) as fh:
            text = fh.read()
        self.assertFalse(self._check(text))
        self.assertTrue(self._check(text.replace('"./plugins/', '"plugins/')))


if __name__ == "__main__":
    unittest.main(verbosity=1)
