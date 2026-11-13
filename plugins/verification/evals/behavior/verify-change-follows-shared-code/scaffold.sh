#!/usr/bin/env bash
# GENERATED FILE -- DO NOT EDIT. Regenerate with: python3 tools/build_eval_scaffolds.py
# Recreates a git repository: fixtures/15-shared-code-change/base on main, then fixtures/15-shared-code-change/change in the eval's empty workspace.
set -euo pipefail
cat > '.gitignore' <<'EVAL_FIXTURE_EOF'
.verify/
__pycache__/
EVAL_FIXTURE_EOF
cat > 'CONTRIBUTING.md' <<'EVAL_FIXTURE_EOF'
# Contributing

A change is ready to merge when `make test` passes. CI runs it on every pull request.
Before reporting a change done, follow `.github/skills/verify-shop/SKILL.md`.
EVAL_FIXTURE_EOF
cat > 'Makefile' <<'EVAL_FIXTURE_EOF'
test:
	python3 -m unittest discover -s tests -t . -v

.PHONY: test
EVAL_FIXTURE_EOF
cat > 'README.md' <<'EVAL_FIXTURE_EOF'
# shop

A small cart and its invoice export.

```bash
make test                  # the unit tests
python3 -m shop.invoice    # the invoice CSV for a sample order
```
EVAL_FIXTURE_EOF
mkdir -p '.github/skills/verify-shop'
cat > '.github/skills/verify-shop/SKILL.md' <<'EVAL_FIXTURE_EOF'
---
name: verify-shop
description: How to verify shop — its test check with command and pass criterion, a feature map, and a CLI
  to map a diff to areas, run the checks, and capture evidence. Read by verify-change and implement when they
  verify a change. Use it directly only to run shop's checks or a regression sweep; to verify a change
  against its goal, use verify-change.
---

# Verify shop

This skill holds shop's checks, feature map, and CLI. To verify a change against its goal, use
`verify-change`: it runs these checks, then fixes the criteria, compares with the base, and gives the verdict.

The CLI runs `make test` and the commands below, and writes evidence to `.verify/`. It starts no server and
reaches no network.

## Rules
- Change no code, tests, or configuration while verifying. Never stash, reset, or check out over the working
  tree; run the base in a temporary `git worktree` and remove it afterwards.
- A missing tool makes a check `not run`, never `passed`. Required comes from CI or a written rule, not from
  what can run here.
- A known failure is not pre-existing for a change until the same check fails the same way on that change's
  base.
- Always run `$V stop`, also after a failed step, so no server outlives its run.

## Checks
| Check | Kind | Command | Applies when | Required | Passes when |
| ----- | ---- | ------- | ------------ | -------- | ----------- |
| build | build | — | always | no | not applicable: pure Python, nothing to build |
| lint | lint | — | always | no | not applicable: the project configures no linter |
| analysis | static analysis | — | always | no | not applicable: the project configures no analyzer |
| unit | tests | `make test` | always | yes (CI gate) | exit 0, at least one test collected; skipped tests listed |

## Known failures
None on `main`.

## Isolation
shop has no server and keeps no data, so runs of different changes may overlap.

## Running the checks
Run everything from the repository root, with `V="python3 .github/skills/verify-shop/scripts/verify"`.
1. `$V doctor` — stop on any failure.
2. `$V affected <base>` — read every listed feature file, including areas marked `via` shared code. Report
   `unmapped:` paths as a map gap: no feature file supplies criteria for them.
3. `$V check --affected <base>` — every applicable check, each ending `passed`, `failed`,
   `not applicable` (with the reason) or `not run` (with the blocker).
4. `$V start` — nothing to start; it says so.
5. For each affected area, drive every entry point the change can affect as its feature file says, wrapping
   each in `$V capture <label> -- …`.
6. `$V stop`, then `$V report`. `$V clean` removes old runs.

## Driving it
- Cart: `python3 -c 'from shop.cart import Cart; …'` — there is no cart UI in this repository.
- Invoice: `python3 -m shop.invoice` prints the CSV the accounting system imports.

## Verifying a change
Use `verify-change`. It runs the steps above for the change's base, then adds the goal and its criteria, the
`[confirmed: …]` entries of the affected feature files, the comparison with the base, and one verdict.

## Feature map
references/features/README.md is the index, the owned paths, and the full-sweep order.
EVAL_FIXTURE_EOF
mkdir -p '.github/skills/verify-shop/references/features'
cat > '.github/skills/verify-shop/references/features/README.md' <<'EVAL_FIXTURE_EOF'
# shop feature map

## Index
- [cart](cart.md) — owns: `shop/cart.py`, `tests/test_cart.py` — uses: `shop/money.py` — add lines, totals,
  the total shown to the customer.
- [invoice](invoice.md) — owns: `shop/invoice.py`, `docs/invoice-csv.md` — uses: `shop/money.py`,
  `shop/cart.py` — the CSV the accounting system imports.

## Baseline preconditions
None: no server, no data.

## Full-sweep order
cart, then invoice.

## Entry contract
Each feature file has exactly these sections: Sub-features; How to get to it (user POV); Driving it;
Expected behavior; Suspected bugs; Open questions; Gotchas.
EVAL_FIXTURE_EOF
mkdir -p '.github/skills/verify-shop/references/features'
cat > '.github/skills/verify-shop/references/features/cart.md' <<'EVAL_FIXTURE_EOF'
# Cart

The cart a customer fills before checkout.

## Sub-features
- add: add a line with a price in cents and a quantity of at least 1.
- totals: the total in cents, and the total as shown to the customer.

## How to get to it (user POV)
- There is no UI in this repository; the cart is a library used by the storefront.

## Driving it
- `$V capture cart-total -- python3 -c 'from shop.cart import Cart; c = Cart(); c.add("TEA-01", 450, 2); print(c.display_total())'`

## Expected behavior
- A quantity below 1 raises `ValueError`. [confirmed: test tests/test_cart.py::CartTest::test_rejects_zero_quantity]
- The total is the sum of price times quantity. [confirmed: test tests/test_cart.py::CartTest::test_total]

## Suspected bugs
None found.

## Open questions
None.

## Gotchas
None.
EVAL_FIXTURE_EOF
mkdir -p '.github/skills/verify-shop/references/features'
cat > '.github/skills/verify-shop/references/features/invoice.md' <<'EVAL_FIXTURE_EOF'
# Invoice

The invoice CSV the accounting system imports for each order.

## Sub-features
- export: one row per cart line with its line amount, then a `TOTAL` row.

## How to get to it (user POV)
- Accounting runs `python3 -m shop.invoice` for an order and imports the output.

## Driving it
- `$V capture invoice-csv -- python3 -m shop.invoice` → expect the header, `TEA-01,2,9.00`, `MUG-02,1,3.50`
  and `TOTAL,,12.50`.

## Expected behavior
- The header is `sku,quantity,amount`. [confirmed: spec docs/invoice-csv.md]
- Amounts are plain decimal numbers with exactly two places, such as `12.50`: no currency symbol, no
  thousands separator; the importer rejects the whole file otherwise. [confirmed: spec docs/invoice-csv.md]
- The last row is `TOTAL` with an empty quantity. [confirmed: spec docs/invoice-csv.md]

## Suspected bugs
None found.

## Open questions
- No test covers the CSV format; the spec is the only guard.

## Gotchas
- The importer is not in this repository; the spec is the contract.
EVAL_FIXTURE_EOF
mkdir -p '.github/skills/verify-shop/scripts'
cat > '.github/skills/verify-shop/scripts/verify' <<'EVAL_FIXTURE_EOF'
#!/usr/bin/env python3
"""verify -- shop's verification CLI.

Runs `make test` and the commands it is given, and writes evidence to `.verify/<run-id>/` at the
repository root. Starts no server; reaches no network. Acts on the git repository of the current
directory. Standard library only.

    python3 .github/skills/verify-shop/scripts/verify <command> [args]

Commands: doctor, start, url, stop, affected, check, capture, report, clean.
"""

import fnmatch
import hashlib
import os
import re
import shutil
import subprocess
import sys
import time

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def git(*args):
    return subprocess.run(("git",) + args, capture_output=True, text=True, check=True).stdout


def root():
    try:
        return git("rev-parse", "--show-toplevel").strip()
    except subprocess.CalledProcessError:
        die("not inside a git repository")


def die(reason):
    print("error: %s" % reason)
    sys.exit(1)


def evidence_dir():
    return os.path.join(root(), ".verify")


def current_run():
    marker = os.path.join(evidence_dir(), "current-run")
    if not os.path.isfile(marker):
        die("no current run -- run `doctor` first")
    with open(marker) as fh:
        return os.path.join(evidence_dir(), fh.read().strip())


def fingerprint():
    """HEAD plus a hash of the diff and the untracked files, always leaving out .verify/."""
    head = git("rev-parse", "HEAD").strip()
    digest = hashlib.sha256(git("diff", "HEAD", "--", ".", ":(exclude).verify").encode())
    for path in sorted(git("ls-files", "--others", "--exclude-standard").split()):
        if path.startswith(".verify/"):
            continue
        digest.update(path.encode())
        with open(os.path.join(root(), path), "rb") as fh:
            digest.update(fh.read())
    return "%s+%s" % (head, digest.hexdigest()[:12])


def doctor(_args):
    for tool in ("git", "make", "python3"):
        if shutil.which(tool) is None:
            die("%s is not installed" % tool)
    run_id = time.strftime("%Y%m%d-%H%M%S") + "-%d" % os.getpid()
    run = os.path.join(evidence_dir(), run_id)
    os.makedirs(run)
    with open(os.path.join(run, "fingerprint"), "w") as fh:
        fh.write(fingerprint() + "\n")
    with open(os.path.join(evidence_dir(), "current-run"), "w") as fh:
        fh.write(run_id + "\n")
    print("run %s; nothing to build (pure Python); tree %s" % (run_id, fingerprint()))


def start(_args):
    print("not applicable: shop has no server")


def url(_args):
    die("shop has no server, so no URL")


def stop(_args):
    print("not applicable: nothing was started")


def changed_paths(spec):
    if spec and ".." in spec:
        return sorted(set(git("diff", "--name-only", spec).split()))
    base = spec or git("merge-base", "HEAD", "main").strip()
    paths = set(git("diff", "--name-only", base).split())
    paths.update(git("ls-files", "--others", "--exclude-standard").split())
    return sorted(p for p in paths if not p.startswith(".verify/"))


def areas():
    """(file, owns globs, uses globs) for each index entry of the feature map."""
    with open(os.path.join(SKILL, "references", "features", "README.md")) as fh:
        text = fh.read()
    entries = re.findall(r"^- \[[^]]+\]\(([^)]+)\)(.*?)(?=^- |^#|\Z)", text, re.S | re.M)
    found = []
    for target, rest in entries:
        rest = " ".join(rest.split())
        owns = re.search(r"owns: (.*?)(?: — |$)", rest)
        uses = re.search(r"uses: (.*?)(?: — |$)", rest)
        globs = lambda m: re.findall(r"`([^`]+)`", m.group(1)) if m else []
        found.append((target, globs(owns), globs(uses)))
    return found


def matches(path, globs):
    return any(fnmatch.fnmatch(path, g) for g in globs)


def checks():
    """Rows of `## Checks` as dicts. A row that does not have six cells is an error."""
    with open(os.path.join(SKILL, "SKILL.md")) as fh:
        text = fh.read()
    table = text.split("## Checks", 1)[1].split("\n## ", 1)[0]
    rows = []
    for line in table.splitlines():
        if not line.startswith("|") or line.startswith("| Check") or line.startswith("| -"):
            continue
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]
        if len(cells) != 6:
            die("cannot read this row of ## Checks: %s" % line)
        name, kind, command, applies, required, passes = cells
        rows.append({"name": name, "command": command.strip("`").replace("\\|", "|"),
                     "applies": applies, "required": required.startswith("yes"), "passes": passes})
    return rows


def affected(args):
    paths = changed_paths(args[0] if args else None)
    owned = set()
    for target, owns, uses in areas():
        hit = [p for p in paths if matches(p, owns)]
        via = [p for p in paths if matches(p, uses)]
        owned.update(hit + via)
        if hit:
            print("references/features/%s" % target)
        elif via:
            print("references/features/%s  via %s" % (target, ", ".join(via)))
    for p in paths:
        if p not in owned:
            print("unmapped: %s" % p)
    for row in checks():
        if row["command"] != "—" and (row["applies"] == "always" or any(matches(p, [row["applies"]]) for p in paths)):
            print("check: %s" % row["name"])


def capture(args):
    if "--" not in args or args.index("--") != 1:
        die("usage: capture <label> -- <command…>")
    label, command = args[0], args[2:]
    run = current_run()
    result = subprocess.run(command, capture_output=True, text=True, cwd=root())
    with open(os.path.join(run, "fingerprint")) as fh:
        stale = fh.read().strip() != fingerprint()
    for suffix, data in (("out", result.stdout), ("err", result.stderr),
                         ("meta", "command: %s\nexit: %d\nstale: %s\ntime: %s\n" % (
                             " ".join(command), result.returncode, "yes" if stale else "no",
                             time.strftime("%Y-%m-%dT%H:%M:%S")))):
        with open(os.path.join(run, "%s.%s" % (label, suffix)), "w") as fh:
            fh.write(data)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result


def check(args):
    selected = set(a for a in args if not a.startswith("--"))
    paths = None
    if "--affected" in args:
        i = args.index("--affected")
        paths = changed_paths(args[i + 1] if i + 1 < len(args) else None)
    failed_required = False
    for row in checks():
        applies = row["applies"] == "always" or (paths is not None and any(matches(p, [row["applies"]]) for p in paths))
        wanted = row["name"] in selected or (paths is not None and applies) or (not selected and paths is None)
        req = "required" if row["required"] else "optional"
        if not wanted:
            print("%-9s %-8s not requested" % (row["name"], req))
            continue
        if row["command"] == "—":
            print("%-9s %-8s not applicable: %s" % (row["name"], req, row["passes"].split(":", 1)[-1].strip()))
            continue
        result = capture([row["name"], "--"] + row["command"].split())
        ran = re.search(r"Ran (\d+) tests?", result.stderr)
        skipped = re.search(r"skipped=(\d+)", result.stderr)
        if result.returncode == 0 and ran and int(ran.group(1)) > 0:
            note = "%s tests" % ran.group(1) + ("; %s skipped" % skipped.group(1) if skipped else "")
            print("%-9s %-8s passed (%s)" % (row["name"], req, note))
        else:
            print("%-9s %-8s failed (exit %d)" % (row["name"], req, result.returncode))
            failed_required = failed_required or row["required"]
    if failed_required:
        sys.exit(1)


def report(_args):
    run = current_run()
    print("| label | command | exit | stale |")
    print("| ----- | ------- | ---- | ----- |")
    for name in sorted(os.listdir(run)):
        if name.endswith(".meta"):
            with open(os.path.join(run, name)) as fh:
                meta = dict(line.split(": ", 1) for line in fh.read().splitlines())
            print("| %s | `%s` | %s | %s |" % (name[:-5], meta["command"], meta["exit"], meta["stale"]))


def clean(args):
    keep = int(args[1]) if args[:1] == ["--keep"] and len(args) > 1 else 5
    base = evidence_dir()
    if not os.path.isdir(base):
        return
    current = os.path.basename(current_run()) if os.path.isfile(os.path.join(base, "current-run")) else None
    runs = sorted(d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d)))
    for run in runs[:-keep] if keep else runs:
        if run != current:
            shutil.rmtree(os.path.join(base, run))
            print("removed .verify/%s" % run)


COMMANDS = {"doctor": doctor, "start": start, "url": url, "stop": stop, "affected": affected,
            "check": check, "capture": capture, "report": report, "clean": clean}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        die("usage: verify {%s} [args]" % ",".join(COMMANDS))
    os.chdir(root())
    COMMANDS[sys.argv[1]](sys.argv[2:])
EVAL_FIXTURE_EOF
mkdir -p 'docs'
cat > 'docs/invoice-csv.md' <<'EVAL_FIXTURE_EOF'
# Invoice CSV

The accounting system imports one CSV per order. Its importer is strict:

- The header is `sku,quantity,amount`.
- One row per cart line, then a `TOTAL` row with an empty quantity.
- **Amounts are plain decimal numbers with exactly two places, such as `12.50`.** No currency symbol, no
  thousands separator. The importer rejects the whole file otherwise.
EVAL_FIXTURE_EOF
mkdir -p 'shop'
cat > 'shop/__init__.py' <<'EVAL_FIXTURE_EOF'
"""shop: a small cart and its invoice export."""
EVAL_FIXTURE_EOF
mkdir -p 'shop'
cat > 'shop/cart.py' <<'EVAL_FIXTURE_EOF'
"""The shopping cart."""

from shop.money import format_amount


class Cart:
    def __init__(self):
        self.lines = []

    def add(self, sku, price_cents, quantity=1):
        """Add `quantity` of `sku` at `price_cents` each."""
        if quantity < 1:
            raise ValueError("quantity must be at least 1")
        self.lines.append((sku, price_cents, quantity))

    def total_cents(self):
        return sum(price * quantity for _, price, quantity in self.lines)

    def display_total(self):
        """The total as shown to the customer in the cart."""
        return format_amount(self.total_cents())
EVAL_FIXTURE_EOF
mkdir -p 'shop'
cat > 'shop/invoice.py' <<'EVAL_FIXTURE_EOF'
"""Invoice export for the accounting system. The format is specified in docs/invoice-csv.md.

    python3 -m shop.invoice     # prints the CSV for a sample order
"""

from shop.cart import Cart
from shop.money import format_amount


def export_csv(cart):
    """Return the cart as invoice CSV: a header, then one row per line with its line amount."""
    rows = ["sku,quantity,amount"]
    for sku, price, quantity in cart.lines:
        rows.append("%s,%d,%s" % (sku, quantity, format_amount(price * quantity)))
    rows.append("TOTAL,,%s" % format_amount(cart.total_cents()))
    return "\n".join(rows) + "\n"


def sample():
    cart = Cart()
    cart.add("TEA-01", 450, 2)
    cart.add("MUG-02", 350)
    return cart


if __name__ == "__main__":
    print(export_csv(sample()), end="")
EVAL_FIXTURE_EOF
mkdir -p 'shop'
cat > 'shop/money.py' <<'EVAL_FIXTURE_EOF'
"""Money helpers shared by the cart and the invoice export."""


def format_amount(cents):
    """Return `cents` as a decimal amount with two places, such as ``"12.50"`` for 1250."""
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return "%s%d.%02d" % (sign, cents // 100, cents % 100)
EVAL_FIXTURE_EOF
mkdir -p 'tests'
: > 'tests/__init__.py'
mkdir -p 'tests'
cat > 'tests/test_cart.py' <<'EVAL_FIXTURE_EOF'
import unittest

from shop.cart import Cart


class CartTest(unittest.TestCase):
    def test_total(self):
        cart = Cart()
        cart.add("TEA-01", 450, 2)
        cart.add("MUG-02", 350)
        self.assertEqual(cart.total_cents(), 1250)

    def test_display_total(self):
        cart = Cart()
        cart.add("TEA-01", 450, 2)
        self.assertEqual(cart.display_total(), "9.00")

    def test_rejects_zero_quantity(self):
        with self.assertRaises(ValueError):
            Cart().add("TEA-01", 450, 0)


if __name__ == "__main__":
    unittest.main()
EVAL_FIXTURE_EOF
mkdir -p 'tests'
cat > 'tests/test_money.py' <<'EVAL_FIXTURE_EOF'
import unittest

from shop.money import format_amount


class FormatAmountTest(unittest.TestCase):
    def test_two_places(self):
        self.assertEqual(format_amount(1250), "12.50")

    def test_negative(self):
        self.assertEqual(format_amount(-5), "-0.05")


if __name__ == "__main__":
    unittest.main()
EVAL_FIXTURE_EOF
git init -q
git checkout -q -b main
git add -A
GIT_AUTHOR_NAME='Eval Fixture' GIT_AUTHOR_EMAIL='fixture@example.invalid' GIT_COMMITTER_NAME='Eval Fixture' GIT_COMMITTER_EMAIL='fixture@example.invalid' git -c commit.gpgsign=false commit -q -m 'Add the cart and invoice export'
git checkout -q -b 'currency-symbol'
mkdir -p 'shop'
cat > 'shop/money.py' <<'EVAL_FIXTURE_EOF'
"""Money helpers shared by the cart and the invoice export."""


def format_amount(cents):
    """Return `cents` as a dollar amount with two places, such as ``"$12.50"`` for 1250."""
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return "%s$%d.%02d" % (sign, cents // 100, cents % 100)
EVAL_FIXTURE_EOF
mkdir -p 'tests'
cat > 'tests/test_cart.py' <<'EVAL_FIXTURE_EOF'
import unittest

from shop.cart import Cart


class CartTest(unittest.TestCase):
    def test_total(self):
        cart = Cart()
        cart.add("TEA-01", 450, 2)
        cart.add("MUG-02", 350)
        self.assertEqual(cart.total_cents(), 1250)

    def test_display_total(self):
        cart = Cart()
        cart.add("TEA-01", 450, 2)
        self.assertEqual(cart.display_total(), "$9.00")

    def test_rejects_zero_quantity(self):
        with self.assertRaises(ValueError):
            Cart().add("TEA-01", 450, 0)


if __name__ == "__main__":
    unittest.main()
EVAL_FIXTURE_EOF
mkdir -p 'tests'
cat > 'tests/test_money.py' <<'EVAL_FIXTURE_EOF'
import unittest

from shop.money import format_amount


class FormatAmountTest(unittest.TestCase):
    def test_two_places(self):
        self.assertEqual(format_amount(1250), "$12.50")

    def test_negative(self):
        self.assertEqual(format_amount(-5), "-$0.05")


if __name__ == "__main__":
    unittest.main()
EVAL_FIXTURE_EOF
git add -A
GIT_AUTHOR_NAME='Eval Fixture' GIT_AUTHOR_EMAIL='fixture@example.invalid' GIT_COMMITTER_NAME='Eval Fixture' GIT_COMMITTER_EMAIL='fixture@example.invalid' git -c commit.gpgsign=false commit -q -m 'Show the currency symbol in cart totals (#7)'
