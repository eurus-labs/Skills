"""Command line: python3 -m tally {add,total,undo}."""

import argparse
import os
import sys

from tally import core


def main(argv=None):
    parser = argparse.ArgumentParser(prog="tally", description="A tiny expense log.")
    commands = parser.add_subparsers(dest="command", required=True)
    add = commands.add_parser("add", help="record an expense")
    add.add_argument("amount")
    add.add_argument("category")
    total = commands.add_parser("total", help="print the sum of the expenses")
    total.add_argument("--category")
    commands.add_parser("undo", help="remove the most recent entry")
    args = parser.parse_args(argv)

    path = os.environ.get("TALLY_FILE", "tally.json")
    entries = core.load(path)
    if args.command == "add":
        try:
            entry = core.add(entries, args.amount, args.category)
        except ValueError as exc:
            print("error: %s" % exc, file=sys.stderr)
            return 2
        core.save(path, entries)
        print("added %s %s" % (entry["amount"], entry["category"]))
    elif args.command == "total":
        print(core.total(entries, args.category))
    else:
        entry = core.undo(entries)
        if entry is None:
            print("nothing to undo")
            return 0
        core.save(path, entries)
        print("removed %s %s" % (entry["amount"], entry["category"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
