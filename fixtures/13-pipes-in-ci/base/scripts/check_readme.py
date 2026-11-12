"""Run every `$ python3 -m textkit ...` example in README.md and compare its output."""

import shlex
import subprocess
import sys


def main():
    with open("README.md", encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    stale = 0
    for i, line in enumerate(lines):
        if line.startswith("$ python3 -m textkit"):
            expected = lines[i + 1]
            got = subprocess.run([sys.executable] + shlex.split(line[2:])[1:], capture_output=True,
                                 text=True).stdout.strip()
            if got != expected:
                print("README line %d: expected %r, got %r" % (i + 1, expected, got))
                stale += 1
    print("%d stale example(s)" % stale)
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
