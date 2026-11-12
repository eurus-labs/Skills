import unittest

from textkit.slug import slugify


class SlugifyTest(unittest.TestCase):
    def test_lowercases_and_joins_words(self):
        self.assertEqual(slugify("Release Notes"), "release-notes")

    def test_docstring_example(self):
        self.assertEqual(slugify("Hello,  World!"), "hello-world")
