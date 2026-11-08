import os
import subprocess
import sys
import tempfile
import unittest


def tally(*args, path):
    env = dict(os.environ, TALLY_FILE=path)
    return subprocess.run([sys.executable, "-m", "tally", *args], env=env,
                          capture_output=True, text=True)


class CliTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "tally.json")

    def tearDown(self):
        self.dir.cleanup()

    def test_add_then_total(self):
        self.assertEqual(tally("add", "12.50", "food", path=self.path).stdout, "added 12.50 food\n")
        self.assertEqual(tally("total", path=self.path).stdout, "12.50\n")

    def test_rejects_a_negative_amount(self):
        result = tally("add", "-3", "food", path=self.path)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(os.path.exists(self.path))
