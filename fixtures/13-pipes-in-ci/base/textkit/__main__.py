"""Command line: python3 -m textkit slugify <title>."""

import sys

from textkit.slug import slugify


def main(argv):
    if len(argv) != 2 or argv[0] != "slugify":
        print("usage: python3 -m textkit slugify <title>", file=sys.stderr)
        return 2
    print(slugify(argv[1]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
