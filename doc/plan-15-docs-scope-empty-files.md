# Plan 15 — `document-codebase`: an empty source file is not an unread product file

Status: implemented
Date: 2026-11-20
Branch: `fix/docs-scope-empty-files`
Baseline: `origin/main` at `48371e031b17e39a9c27c2a7177ebea09f76c101` (eurus-labs/Skills#85 merged)
Target: `shared/scripts/survey/build_scope.py`, `shared/scripts/survey/scope_record.py`, their plugin copies,
`plugins/docs/skills/document-codebase/` (references), the `docs` plugin version, tests

## Goal

Since plan 14, `survey` makes every source file that is not a test, vendored, generated or an asset a
`product` file with `reading: unread`. An empty `__init__.py`, which almost every Python package has, is one
of them. An empty file has nothing to read and no line that says anything, so an honest Analyst cannot write
the one statement a symbol-free file owes. The draft then stays `partial` ("4 of 10 modules unread") unless
the user narrows the scope by hand.

This was seen on 2026-11-20 in the `docs` behavior eval on `tests/contracts/layered-repo`, which has four
empty `__init__.py` files (`doc/eval-results.md`).

A dishonest workaround also passes today. The scanner counts an empty file as one line
(`scan_repo.py`: `"loc": text.count("\n") + 1`), so evidence citing line 1 of an empty file passes `A007`.
`tools/test_scope_pipeline.py` relies on that: it writes "Package marker …" statements for two empty
`__init__.py` files.

When this is done:

- an empty source file gets its own disposition, `empty`, with a reason;
- it is owed no reading, appears on no page and in no diagram, and never makes a run `partial`;
- a file that holds anything at all is still `product`.

## Decisions

1. **A sixth disposition, `empty`** (the user's choice, 2026-11-20).
   - `scope_record.DISPOSITIONS` becomes `("product", "test", "generated", "vendor", "asset", "empty")`.
   - `DOCUMENTED` stays `("product",)`, so `empty` is excluded everywhere `documented_paths()` and
     `coverage()` are used, with no change to those functions.
   - An `empty` row has `reading: "excluded"` and the reason `empty file: nothing to read or cite`.

   Rejected:
   - `asset` with an "empty file" reason, because `asset` means README, CI, packaging and configuration,
     and the row would mislead the person reading it at P1;
   - keeping `product` and marking the file `read`, because it would still become a module node and a
     module page, and several checks would need an exception for it.
2. **What counts as empty** (the user's choice). A file is empty when its whole content is zero bytes, or
   only whitespace: spaces, tabs and line breaks, which is what `bytes.strip()` removes. A file holding
   anything else is not empty and stays `product`: a comment, a docstring, a license header, an import. It
   owes its one statement as today.

   Rejected: also treating comment-only files as empty, because that needs a per-language comment parser,
   and a comment can say what a file is for.
3. **Where the rule applies.** `classify()` in `build_scope.py` checks for empty **last, only for a file that
   would otherwise be `product`**. A file the earlier rules place stays where it is, even when empty:
   - under `tests/` it stays `test`;
   - under `vendor/` it stays `vendor`;
   - under `examples/` it stays `asset`.

   Read the file once, contained in the root as `read_header` does today. A file larger than the bytes read
   is never empty. A file that cannot be read is not `empty`: it stays `product`, as today.

   Rejected: checking empty first, because it would change the reason on rows that are already correctly
   excluded.
4. **Rows that are kept across reruns.**
   - A row a person changed at P1 (`override`) keeps its disposition as today, including a person who sets
     an empty file back to `product`.
   - An earlier `product` row for a file that is now empty becomes `empty` on the next survey. The
     existing reading-state carry-over applies only to `product` rows.
5. **`scope_version` stays 1.**
   - No field is added or renamed, and every scope written before this stays valid.
   - The scope hash covers dispositions, so a repository with empty files gets a new scope hash once. Reviews
     bound to the old hash go stale and are redone, which is the correct outcome for a changed scope.

   Rejected: bumping to 2, which would refuse every existing build for a change that only adds a value.
6. **Names, not new rules, everywhere else.** Every place that lists the dispositions says `empty` too:
   - the `scope_record.py` module docstring table;
   - the `build_scope.py` docstring rule list;
   - the P1 `show` text in `pipeline.py` (`CHECKPOINTS`);
   - `references/schemas.md` (`scope.json` section);
   - `references/survey.md`;
   - any status or resume output that names dispositions by hand rather than through `DISPOSITIONS`.

   Find them with:

   ```bash
   grep -rn "generated, vendor\|vendor, asset\|vendor\` or \`asset\|DISPOSITIONS" shared plugins/docs/skills
   ```

   The `build_scope.py` summary line (`scope: …`) already loops over `DISPOSITIONS`.
7. **Version.** `docs` 1.7.0 → 1.7.1. Update both `plugin.json` copies and both `marketplace.json` entries,
   and add a `### Fixed` entry under `[Unreleased]` in `CHANGELOG.md`. Edit `shared/scripts/` only, and run
   `tools/materialize.py`.

## Scope

In:

- `shared/scripts/survey/build_scope.py`: `classify()` and its docstring.
- `shared/scripts/survey/scope_record.py`: `DISPOSITIONS` and its docstring.
- `shared/scripts/pipeline.py`: the P1 `show` text, and any by-hand list of dispositions (Decision 6).
- The regenerated plugin copies.
- `references/schemas.md` and `references/survey.md`.
- The `docs` version, `.github/plugin/marketplace.json`, `.claude-plugin/marketplace.json` and
  `CHANGELOG.md`.
- Tests:
  - `tools/test_product_scope.py`;
  - `tools/scope_fixture.py`, its docstring line for `src/shop/__init__.py` and any new file;
  - `tools/test_scope_pipeline.py`.

Out:

- **The scanner's `loc` for an empty file.** It stays 1. Changing what the index says about every file is a
  larger change, and an `empty` file is never cited after this.
- **Comment-only and docstring-only files.** They stay `product` (Decision 2).
- **The no-scope path of `select_units.py`.** Its `__init__.py` handling is unchanged, and so is the check at
  `tools/test_pipeline.py:105`.
- **`fixtures/`.**
- **Released `CHANGELOG.md` sections.**
- **The eval case.** The planner reruns it during review.

## Baseline

| Existing | Keep, change, or remove |
| --- | --- |
| `build_scope.py:108` `classify()`: test, vendor, generated name, generated marker, example or doc tooling asset, else `product` | Change per Decision 3 |
| `build_scope.py:91` `read_header()`: contained read of the first 2 KiB | Reuse its containment; reading for emptiness may share the one read |
| `build_scope.py:196` `build()`: `product` rows get `unread`, `symbols`, `source_hash`, features; others get `excluded` and `reason`; override rows kept | Keep; an `empty` row takes the non-product branch |
| `scope_record.py:35` `DISPOSITIONS`, `DOCUMENTED`, `malformed()` requiring a reason for every non-product row | Change `DISPOSITIONS`; keep the rest |
| `scope_record.py` `coverage()`, `documented_paths()`, `symbol_free()` | Keep unchanged; they already key on `DOCUMENTED` |
| `pipeline.py:813` P1 `show` text naming "product, test, generated, vendor, asset" | Add `empty` |
| `tools/scope_fixture.py`: `src/shop/__init__.py` and `src/latest/__init__.py` are `""` | Keep the files; they now become `empty` |
| `tools/test_scope_pipeline.py`: `TEXT` statements for both empty `__init__.py` files; `assertIn("src/shop/__init__.py", units)`; `len(units) == 8` | Change: both files leave `units.txt`, so 6 units; drop their `TEXT` entries |
| `tools/test_product_scope.py:122`: `src/shop/__init__.py` asserted `product` | Change: assert `empty`, with the reason |
| `tools/test_product_scope.py:551`: `src/latest/__init__.py` asserted to carry `task: feature:latest-feed` | Change: an `empty` row carries no task; keep the assertion for `src/latest/feed.py` |
| `tests/contracts/layered-repo/src/app/**/__init__.py`: four zero-byte files | Read only; the end-to-end check below uses a copy |

The test changes in the last four rows are the expected consequence of Decision 1, not weakened checks.
Each one must assert the new behaviour, not only stop asserting the old.

## Tech stack and constraints

Default: stdlib-only Python 3.9+. Canonical scripts are in `shared/scripts/`, and the plugin copies are
regenerated by `tools/materialize.py`.

## Acceptance criteria

All criteria are tests in `tools/test_product_scope.py`, unless noted.

- [ ] **Empty files.** A zero-byte file and a whitespace-only file (spaces, tabs and blank lines) that would
      otherwise be product are `empty`, with `reading: excluded` and the reason
      `empty file: nothing to read or cite`.
- [ ] **Files that are not empty stay product.** One holding only a comment and one holding only a docstring
      are `product` and `unread`.
- [ ] **Rule order.** An empty file under `tests/` is `test`, and one under `examples/` is `asset`, each with
      its existing reason (Decision 3).
- [ ] **Coverage.** With every non-empty product file analysed and the empty files untouched,
      `scope_record.coverage()` lists no unread file. The `quality_docs.py` gate, via the test that already
      runs its CLI, does not report `incomplete`.
- [ ] **Not documented.** `documented_paths()` does not contain the empty files, and the document model lists
      no page or node for them. Checked in the existing `OneProductView` style.
- [ ] **Reruns.** A `scope.json` whose row for an empty file is `product`/`unread` (as written before this
      change) becomes `empty` after `build()` with it as `previous`. The same row with an `override` keeps the
      person's disposition.
- [ ] **Failure case: unreadable file.** A product-candidate file that cannot be read (removed between scan
      and scope, or a symlink leaving the root) stays `product`, and `build()` does not raise.
- [ ] **End to end on the contract repo.** In `tools/test_scope_pipeline.py`, or a new test there, run
      `survey` on a copy of `tests/contracts/layered-repo`. Its `scope.json` has 4 `empty` rows (the
      `__init__.py` files) and 6 `product` rows, and `units.txt` holds the 6 product files.
- [ ] **The existing scope pipeline test** still runs every stage to exit 0, with 6 units and no `TEXT` entry
      for an empty file.
- [ ] **Docs.** `schemas.md` and `survey.md` name `empty` and its rule, and no reference lists the
      dispositions without it. Checked by reading the output of
      `grep -rn "vendor" plugins/docs/skills/document-codebase/references/schemas.md plugins/docs/skills/document-codebase/references/survey.md`.
- [ ] **Required checks pass:** `python3 tools/validate.py`, `python3 tools/materialize.py --check`, and
      `for t in tools/test_*.py; do python3 "$t" || break; done`.

## Risks

| Risk | How it is handled |
| --- | --- |
| A repository's empty files become `empty`, so its scope hash changes and earlier reviews go stale | Expected and stated in the CHANGELOG entry: the scope did change. Nothing else stales, because reading state is not in the hash |
| A large whitespace-only file is read whole | Read at most a bounded number of bytes. A file longer than that is not empty (Decision 3), so the cost is bounded |
| Another consumer hard-codes the five dispositions and now refuses `empty` | Decision 6's grep, and the end-to-end test that runs every stage on a scope holding `empty` rows |
| A person meant an empty file to be documented | They set it back to `product` with an `override` at P1, which survives reruns (Decision 4) |
| The eval keeps failing for another reason | The planner reruns the `docs` behavior case after review and reports the result in the PR; this plan does not change the case |
| The coder run is cut off | Push after Decisions 1–3 with their tests, then after 4–7 |

## Open questions

None.
