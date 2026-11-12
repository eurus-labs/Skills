"""Fail when a public function in the given package has no docstring."""

import ast
import os
import sys


def main(package):
    missing = []
    for name in sorted(os.listdir(package)):
        if not name.endswith(".py"):
            continue
        path = os.path.join(package, name)
        with open(path, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                if ast.get_docstring(node) is None:
                    missing.append("%s:%d %s" % (path, node.lineno, node.name))
    for item in missing:
        print("missing docstring: " + item)
    print("%d public function(s) without a docstring" % len(missing))
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
