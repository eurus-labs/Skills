"""Turn titles into URL slugs."""

import re


def slugify(title):
    """Lowercase `title`, replace each run of characters that are not letters or digits with a single
    dash, and strip dashes from both ends: slugify("Hello,  World!") == "hello-world".
    """
    return re.sub(r"[^a-z0-9]", "-", title.lower()).strip("-")
