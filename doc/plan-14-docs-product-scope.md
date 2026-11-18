# Plan 14 — product scope, feature-map cross-check and the audit edition (plan 4, W2)

Status: draft
Date: 2026-11-18
Branch: `feat/docs-product-scope`
Baseline: `origin/main` at `2cf65aa34c15c9452be44540ec40def1ecdab631`, with plans 12 and 13 merged. Any
line numbers below for `pipeline.py` predate them, so read the code, not the numbers.
Target: `shared/scripts/` (`survey/`, `pipeline.py`, `publish/render_docs.py`, `publish/quality_docs.py`),
their plugin copies, `plugins/docs/skills/document-codebase/` (`SKILL.md`, references), tests

## Goal

`document-codebase` should cover the **whole product**, not the 25 best-connected modules. Every documented
sentence should also be traceable to the code lines it rests on, without making the reader's pages hard to
read.

Today three things fall short:

1. **The scope is never written.**
   - `scope_record.py` defines `scope.json` (the list of what the run promised to document) and
     `documented_paths()`, the single product view.
   - No script writes `scope.json`. `pipeline.py:1026` only reads it into the checkpoint identity.
   - `select_units.py` picks units by fan-in with `--top 25` and drops symbol-free modules
     (`select_units.py:88-132`). A low-fan-in feature or a symbol-free entry module can therefore vanish
     from the manual, and nothing reports it.
2. **No outside list of features to check against.**
   - A repository set up with the `verification` plugin's `setup-verification` has a project-local
     `verify-<app>` skill. Its feature map (`references/features/<area>.md`, with `owns:` and `uses:` path
     globs) lists the product's features by user-visible behavior.
   - `document-codebase` does not read it, so a feature missing from the docs goes unnoticed.
3. **Citations sit inside the reader's prose.**
   - Every block already carries structured `evidence` (path and line range). `review_records.content_hash`
     hashes it.
   - But `render_docs.py` prints only the block `text`, so the model writes `path:line` into the sentences
     themselves.
   - Readers get cluttered prose, and an auditor gets citations of uneven quality.

This plan covers the three as separate groups. The coder pushes after each group.

## Decisions

### Group A — the product scope (plan 4, W2)

1. **`survey` writes `scope.json`.** A new stage, `survey/build_scope.py`, runs after `select_units.py`.
   - It gives every file in `structure.json` a disposition (`product`, `test`, `generated`, `vendor`,
     `asset`) and a reason.
   - It uses the scanner's metadata (`is_test`, generated and vendored markers) and repository conventions,
     never a bare substring match on `test` (`scope_record.py` docstring).
   - `product_roots` default to the directories that hold the selected entry points and product modules.
   - `required_topics` come from the chosen template's questions when a template is recorded; otherwise
     they are empty.
   - Every file starts as `unread`, and `excluded` for non-product files.
   - The P1 scope checkpoint already binds `scope.json`, so the user reviews this classification at P1.

   Rejected: having the model write `scope.json` by hand, because the classification is mechanical and must
   be the same on every run.
2. **The cutoff orders reading; it does not decide scope.**
   - `select_units.py` takes `--scope` and lists **every** `product` file as a unit, including symbol-free
     entry and side-effect modules.
   - It orders units by fan-in as today.
   - `--top` becomes the size of the next reading batch, written to `units.txt` with the full list kept in
     `scope.json`. It no longer bounds what is promised.
   - A symbol-free module gets a reading task whose analysis may say "entry point: runs X" without the
     four-statement minimum. `validate_analysis.py` and `assemble.py` accept such a row for a file that
     `scope.json` marks `product` with no symbols.

   Rejected: raising the default `--top`, because any fixed number silently drops features in a large
   repository (plan 4, "Source scope and reading coverage").
3. **One product view everywhere.** These all filter through `scope_record.documented_paths()`, replacing
   their own `is_test` checks:
   - the class graph, the component inventory, the document model and diagrams;
   - the coverage in `quality_docs.py`.

   Tests can still be cited as evidence, but they never appear as product pages, components or diagram
   nodes.
4. **Coverage is measured against the scope.**
   - `pipeline.py analyze` updates each file's `reading` from `module-analysis.jsonl` (`analyzed` when a row
     exists).
   - `quality_docs.py` reports `scope_record.coverage()`.
   - A run with unread `product` files cannot claim complete-product coverage: the generation report says
     "incomplete: N product files unread" and lists them.
   - Delivering a partial draft stays allowed when the user narrowed scope at P1, and the report records the
     narrowing as a scope change.
   - `status` prints the unread count.

### Group B — the feature map as a cross-check

5. **Read a feature map when the repository has one.**
   - `survey/read_feature_map.py` looks for `verify-*/references/features/*.md` under `.github/skills/`,
     `.claude/skills/` and `.agents/skills/` in the repository being documented.
   - It parses each area's name and its `owns:` and `uses:` globs into `.docs-build/feature-map.json`.
   - With no feature map, it writes nothing and prints `no feature map found`.
   - **No feature map: offer to create one** (the user's decision).
     - At checkpoint P1, if the `setup-verification` skill is available in the session, `SKILL.md` tells the
       Coordinator to ask the user whether to run it now.
     - Before asking, say what it does: it writes `<skills-dir>/verify-<app>/` into the user's repository,
       trial-runs the project's own build and test commands, and may start the app.
     - On yes, run `setup-verification`, then run `survey` again so the new map is read.
     - On no, or when the skill is not available, continue without a map and say so in the final report.
     - Name the skill in plain text, never as a link, because plugins install standalone (`AGENTS.md`).
       `document-codebase` must still work when the `verification` plugin is not installed.

     Rejected: running `setup-verification` without asking, because it writes files into the user's
     repository and runs their commands (`.github/instructions/universal/safety.instructions.md`).
6. **The map is a checklist, never evidence.**
   - Each area becomes a required topic in `scope.json` (`feature:<area>`).
   - The product files it owns are grouped into one reading task, so tasks follow user journeys (plan 4).
   - `quality_docs.py` lists any area with no section that cites a file it owns.
   - A sentence never cites the feature map. It cites source.
   - Where the map's expected behavior disagrees with the code, the Analyst records the disagreement as an
     open question for the user, never as documented behavior. The map was also written by an agent and can
     be wrong.
7. **Running the app is out of this plan.** Using the verify CLI to observe behavior (`basis: observed`)
   has side effects and needs its own permission rules, so it goes in a later plan.

### Group C — reader edition and audit edition

8. **Citations live in `evidence`, not in the text, one list per block** (the user's choice: per block, not
   per sentence).
   - The Writer puts `path:line` only in each block's `evidence` list and writes clean prose.
   - Rejected: per-sentence citations, because the Writer would tag every sentence and the Reviewer check
     every one, for little gain over a block's list.
   - `check_prose.py` adds an advisory finding when a block's text contains a `path:line` pattern.
9. **One source, two builds.**
   - `render_docs.py` emits each block's citations inside a Sphinx `only` block: `.. only:: audit` in RST,
     `{only} audit` in MyST.
   - A normal Sphinx build is the **reader edition**. It shows **no source reference at all**: no line
     numbers, and no "Source: module X" line (the user's choice).
   - `sphinx-build -t audit` is the **audit edition**, where every cited block is followed by its
     `path:line` list.
   - **The audit edition is built on demand, never stored** (the user's choice).
     - No `docs-audit/` directory, no second site, and no `publish` step for it.
     - The citations travel inside the published RST or MyST source, in the `only` blocks. Anyone can
       build the audit edition from `docs/` whenever it is needed.
     - `rendering.md` gives the exact command.
   - Both come from the same reviewed revision, so they cannot disagree and need one review, not two.

   Rejected: rendering two separate trees, because two trees could drift apart and would each need review.
10. **A quality check keeps the two editions honest.** `quality_docs.py` (or the existing Sphinx check in
    `render_docs.py --check`) confirms both of these:
    - the reader build's output contains no `path:line` pattern;
    - every block with evidence has a matching `only:: audit` block in the source.

### All groups

11. **Docs and version.**
    - Update `SKILL.md` rule 2 ("Give every claim a `path:line` citation") to say where citations go.
    - Update `workflow.md`, `analyst.md`, `writer.md`, `pipeline.md`, `schemas.md` (`scope.json` fields and
      `feature-map.json`), and `rendering.md` (the two editions).
    - Plan 4's W2 row becomes "Done by plan 14".
    - `docs` gets a minor version bump over whatever is current, plus a `### Changed` entry under
      `[Unreleased]`.
    - Edit only `shared/scripts/`, register new scripts in `plugins/docs/shared.manifest`, and run
      `tools/materialize.py`.

## Scope

In:

- New: `shared/scripts/survey/build_scope.py` and `shared/scripts/survey/read_feature_map.py`.
- Changed:
  - `survey/select_units.py`;
  - `check/validate_analysis.py` and `check/assemble.py` (symbol-free product rows);
  - `pipeline.py` (survey and analyze stages, `status`);
  - `document/build_class_graph.py`, `build_document_model.py` and the diagram builders (product view);
  - `publish/quality_docs.py` (coverage, feature areas);
  - `publish/render_docs.py` and `publish/check_prose.py` (Group C).
- The references in Decision 11, the `docs` version, and `CHANGELOG.md`.
- Tests: extend the existing `tools/test_*.py` for these scripts. Use a fixture repository with:
  - a low-fan-in feature outside the top 25;
  - a symbol-free entry module;
  - tests;
  - a generated file;
  - a `verify-<app>` feature map.

Out:

- Running the app through the verify CLI (Decision 7).
- Resume (plan 13) and migration of old artifacts (W6).
- Changing `review_records.BOUND_INPUTS` or the review row schema.
- Editing `fixtures/` used by other plugins' evals; add a new fixture under `tools/` test data instead.

## Baseline

| Existing | Keep, change, or remove |
| --- | --- |
| `survey/scope_record.py`: `scope_hash`, `malformed`, `coverage`, `documented_paths` | Keep; now used by the pipeline, not only by its test |
| `pipeline.py:1026` reads `scope.json` into the checkpoint identity | Keep; `build_scope.py` now writes the file it reads |
| `survey/select_units.py:88-132`: `--top 25`, symbols required, `is_test` excluded | Change per Decision 2 |
| `is_test` checks in `scan_repo.py`, `extract_config.py`, `quality_docs.py`, `select_units.py` | Scanner keeps setting it; consumers move to `documented_paths()` (Decision 3) |
| `references/schemas.md:601` `scope.json` schema v1 | Keep the version; document the new `feature:<area>` topics |
| `publish/render_docs.py:194` `render_block` emits only `text` | Change per Decision 9 |
| Block `evidence` hashed in `review_records.content_hash` | Keep unchanged; citations stay part of what a review approves |
| `SKILL.md` rule 2: "Give every claim a `path:line` citation" | Change per Decisions 8 and 11 |
| `verification` plugin's generated layout: `<skills-dir>/verify-<app>/references/features/<area>.md` with `owns:` and `uses:` | Read only; never require it |

## Tech stack and constraints

Default: stdlib-only Python 3.9+. The Sphinx `only` directive and `-t` tags are standard Sphinx features
already within the renderer's markup. No new dependency.

## Acceptance criteria

- [ ] On the fixture, `survey` writes a valid `scope.json`: `scope_record.malformed()` returns None, tests
      are `test` with a reason, the generated file is `generated`, and `src/latest/` stays `product`.
- [ ] The low-fan-in feature and the symbol-free entry module are both in `scope.json` as `product` and get
      reading tasks, with `--top 2`. With `--top 2`, `units.txt` holds the first batch only.
- [ ] Failure case: with one product file unread, `quality_docs.py` reports incomplete coverage naming that
      file, and `status` prints the unread count.
- [ ] No test file appears in the class graph, component inventory, product diagrams, or module pages. A
      test cited as evidence still resolves.
- [ ] With the feature map, each area is a `feature:<area>` required topic. An area with no citing section
      is listed by `quality_docs.py`. Without a feature map, the run's outputs are unchanged.
- [ ] Group C, on the same staged tree:
      - a reader build contains no `path:line` and no "Source:" line;
      - an audit build (`-t audit`) contains every block's evidence;
      - nothing is written to any `docs-audit/` or second output by `publish`.
- [ ] No feature map: the `survey` output says `no feature map found`, and `SKILL.md` tells the Coordinator
      to offer `setup-verification` at P1, ask before running it, and continue without a map on a no.
      Checked by a test of the survey output and by reading `SKILL.md`.
- [ ] `check_prose.py` flags a block whose text contains `path:line`.
- [ ] Required checks pass: `python3 tools/validate.py`, `python3 tools/materialize.py --check`, and
      `for t in tools/test_*.py; do python3 "$t" || break; done`.

## Risks

| Risk | How it is handled |
| --- | --- |
| Listing every product file makes a large repository's reading far longer | `--top` still sets the batch, and coverage reports what is left. Plan 13's resume continues the next batch |
| A feature map is stale or wrong | It only adds topics to check. It is never cited, and disagreements go to the user (Decision 6) |
| Symbol-free rows weaken the analysis checks | Accepted only for `product` files with no symbols, and they still need one statement saying what the file does |
| Group C is large next to Groups A and B | Separate group with its own push |
| `setup-verification` runs the user's build and may start their app | Only after the user says yes at P1, with what it does stated first (Decision 5) |
| Plan 12 and this plan both edit `pipeline.py` | The second to land rebases. Neither plan changes the other's functions |

## Open questions

None. The three Group C questions and the missing-map case were answered by the user on 2026-11-18
and are recorded in Decisions 5, 8 and 9.
