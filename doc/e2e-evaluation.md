# End-to-end evaluation of `document-codebase` (plan 17)

Plan: [`plan-17-docs-end-to-end-run.md`](plan-17-docs-end-to-end-run.md). This is the coder's record. Grading is
the planner's and is added later in a "Grading" section.

## Setup common to both runs

- **Repository state.** The branch `test/docs-end-to-end-run` was rebased onto `origin/main` at `49e213d`
  (plan 15 merged, `fix/docs-scope-empty-files`). `plugins/docs/.github/plugin/plugin.json` says `docs`
  **1.7.1**. Plan 16 (`feat/docs-migrate-legacy-build`) is not on `main`.
- **Versions.** Both runs used the plugin as it stood at the checkout they started on: `docs` 1.7.1 at `main`
  `49e213d`. After the runs `main` moved to `0a8ff05` (plans 16 and 18, `docs` 1.8.0). The branch was rebased
  onto it before the last push, and the runs were not repeated on 1.8.0.
- **Host.** Claude Code, model `claude-sonnet-5-5`, Linux cloud container, running as root. No subagent tool
  was available to this session, so every role (Analyst, Writer, Reviewer) ran as a sequential pass in one
  context and every review is `self_review`. The run is explicitly unattended (Decision 3): P1 to P3 and the
  template choice were recorded by the coder.
- **Local tools.** `python3` 3.13.18, `git`, `ruff` (`/root/.local/bin/ruff`), `plantuml` (`/usr/bin/plantuml`),
  `dot`, `java` present. `sphinx` and `docutils` are **not** installed, so Sphinx checks are expected to be
  `skipped`. Nothing was installed.
- **Prior knowledge (stated as the plan asks).** The coder (this session's model) had seen both codebases
  before: they are this repository's `tests/contracts/layered-repo` and `shared/scripts`, and the coder read
  this plan and the skill's references first. Analysis rows were meant to be written from the packets and
  source read during the run, and `validate_analysis.py` requires evidence lines; the planner's grading
  checks claims against the source.
- **Skill invocation.** Every command was run from the copied codebase as the working directory, calling
  `pipeline.py` by its path in the plugin folder:
  `P=/home/user/Skills/.claude/worktrees/agent-ae2cef2c66bc1786e/plugins/docs/skills/document-codebase/scripts/pipeline.py`
  (shown as `$P` below).
- **`setup-verification`** is not available in this session, and neither copy has a feature map, so the P1
  offer in `SKILL.md` was skipped and the runs continued without a map.

## Copy and commit commands

```bash
mkdir -p /root/e2e-runs
cp -r <checkout>/tests/contracts/layered-repo /root/e2e-runs/layered-repo
cp -r <checkout>/shared/scripts               /root/e2e-runs/shared-scripts
find /root/e2e-runs -name __pycache__ -prune -exec rm -rf {} \;      # shared-scripts only had them
cd /root/e2e-runs/layered-repo && git init -q -b main && git add -A && git commit -q -m "chore: import layered-repo snapshot"
cd /root/e2e-runs/shared-scripts && git init -q -b main && git add -A && git commit -q -m "chore: import shared-scripts snapshot"
```

Both commits set author and committer to `Eurus <56497078+Eurus7895@users.noreply.github.com>` through the
four `GIT_*` variables, and no git config was changed.

| Copy | Commit | Python files |
| --- | --- | --- |
| `/root/e2e-runs/layered-repo` | `cee2af7` | 10 |
| `/root/e2e-runs/shared-scripts` | `642c1db` | 48 |

Build directories (left in place for grading):

- `/root/e2e-runs/layered-repo/.docs-build`
- `/root/e2e-runs/shared-scripts/.docs-build`

## Run 1 — `layered-repo`

- **Working copy:** `/root/e2e-runs/layered-repo` at commit `cee2af7`. Build directory:
  `/root/e2e-runs/layered-repo/.docs-build`.
- **`docs` version and `main` commit:** 1.7.1, `49e213d`.
- **Template (the plan does not set one, so this was the coder's unattended choice):** the `manual` question
  template cut to 7 of its 26 sections: `getting_started/introduction`, `architecture/overview`,
  `architecture/data_flow`, `architecture/module_reference`, `usage/invoking`, `usage/configuration`,
  `usage/errors_and_recovery` (57 questions). Reason recorded in the note: these are the sections that let a
  reader answer purpose, a traced operation, configuration and a failure. The same selection is used for
  run 2.
- **Review mode:** `self_review` (no subagents). The reviewed pass (`review --review`) is held by P4, so
  `prose-review.jsonl` holds 28 `self_review` `confirmed` rows that the gate has not consumed.
- **Where it ended:** at P4, open, with the draft at `rev-0004`. `publish` was not run, P4 was not answered,
  and no `docs/` directory exists in the copy.

### Commands, in order

`$P` is the `pipeline.py` path given above; each ran from `/root/e2e-runs/layered-repo`. Exit codes are as
observed.

| # | Command | Exit | The line that matters |
| --- | --- | --- | --- |
| 1 | `survey --root .` | 0 | `scope: 6 product, 3 asset, 4 empty`; `index_hash sha256:2e72ceb4...`; `no feature map found`; P1 open |
| 2 | `template` | 0 | lists presets, `manual` (26 sections) |
| 3 | `decide --checkpoint P1 --note ...` | 0 | P1 decided |
| 4 | `template --use manual --sections <7 ids> --note ...` | 0 | `template manual: 7 page(s), 57 question(s)` |
| 5 | `measure --step source_reading --state start`, then `analyze` | 0 | 13 derived claims, 6 packets; P2 open |
| 6 | `measure ... stop`, `decide --checkpoint P2` | 0 | source reading measured at 65 s of tool time (writing the rows is not in it) |
| 7 | `check` | 1 | `V015 claim:calls:record-order a 'calls' claim joins ... not 'method' to 'class'` |
| 8 | `check` (after a `sed` that also changed a derived claim) | 1 | `V015 claim:inherits:...:Order:Record ... not 'symbol' to 'class'` |
| 9 | `check` (both repaired) | 0 | `claims: 18 verified`; P3 open |
| 10 | `resume` (deliberate stop test, see below) | 0 | `next ... pipeline.py render --root .` |
| 11 | `render --root .` | 1 | `render is held at checkpoint P3` |
| 12 | `decide --checkpoint P3` (after writing the 3 analyses) | 1 | `P3 material changed since the checkpoint opened; rerun check` |
| 13 | `check`; `decide --checkpoint P3`; `document` | 0; 0; 1 | `wrote manual-analysis.json: 57 unanswered question(s) ... 53 verified fact(s)`; exit 1 is the documented first run |
| 14 | `document` (answers and pages written) | 1 | `validate_flows: F005 id used more than once` (step ids of two flows) |
| 15 | `document` (after renaming the steps) | 1 | held at P3 again, because editing a flow file changed the P3 input |
| 16 | `check`; `decide --checkpoint P3`; `document` | 0; 0; 2 | `build_document_model: FAIL 1.1.3: evidence line range exceeds file` |
| 17 | `document` (evidence ranges corrected) | 0 | `wrote doc.json: 7 page(s), 70 block(s)` |
| 18 | `render --docs docs` | 0 | `minted rev-0001`; `build check: skipped -- neither sphinx-build nor docutils`; `editions: passed` |
| 19 | `readability.py .docs-build/rendered-docs --for-review` | 0 | one 29-word sentence; split it, rerun `document` and `render` (`rev-0002`, `rev-0003`) |
| 20 | `review` | 1 | gate `failed`; 28 blocks queued; P4 opened; 2 `P003` errors |
| 21 | `document`; `render`; `review` (two `P003` wordings repaired) | 0; 0; 1 | `rev-0004`; prose errors 0; gate still `failed` |
| 22 | `review --review .docs-build/prose-review.jsonl` | 1 | `review is held at checkpoint P4` |
| 23 | `resume` | 0 | `next ... decide --root . --checkpoint P4 --user-response ...` |

### Checkpoint notes recorded

- **P1:** "Unattended run: scope of 6 product files accepted; 4 empty init files and 3 assets excluded by rule; no
  feature map found and setup-verification unavailable, so continuing without one".
- **Template:** "Unattended choice by the coder: manual subset covering purpose, key operation, configuration
  and failure for a reader".
- **P2:** "Unattended: accepted six module roles; unknowns are cli rationale, models failure and store failure
  which the repository does not state".
- **P3** (decided three times, because its input changed twice): "Unattended: three components entry,
  workflow and storage accepted; two flows traced through objects, none absent, README promise of reports not
  found in code".

### Counts

- **`scope.json` by disposition** (run in the build directory):
  `Counter({'product': 6, 'empty': 4, 'asset': 3})`. By `reading`: 6 `analyzed`, 7 `excluded`.
- **Unread product files at the end:** 0.
- **Analysis:** 6 module rows, 30 statements (21 observed, 5 declared, 1 inferred, 3 unknown), 18 claims
  verified (5 hand-written `calls`), 3 components, 2 flows (4 steps, all validated), 3 operations rows.
- **Manual:** 51 of 57 questions answered (`answer_mode: partial`), 28 sections composed, 1,407 prose words.
  Six questions are `unknown` with a stated `next_check`: 1.1.7, 2.1.7, 2.2.5, 2.3.7, 3.1.8, 3.4.6.

### Gate outcome (`generation-report.json`)

- `analysis_mode`: `per_module`. `status`: `failed`.
- Reasons, after the prose repair:
  1. "manual leaves 6 of 57 question(s) unanswered: 1.1.7, 2.1.7, 2.2.5, 2.3.7, 3.1.8" (the message names five
     ids for a count of six);
  2. "detector B: components and directories agree on 100% of module pairs; 67% of components carry
     something a path cannot give";
  3. "28 block(s) have no fresh confirmed model review" (held behind P4).
- Before the repair there was a further reason: two `P003` errors ("says 'needs' ... imports claim" in
  `getting_started/introduction:3`, and "says 'calls' ... statement http-s3" in `usage/invoking:1`).
- Advisory only: `A014` on statement `cli-s5`, `A016` on `config.py`, and `P005` on six generated gap blocks.

### Revisions, rounds and open findings (P4)

- Revisions `rev-0001` to `rev-0004`; `rev-0004` is the one at P4. `rev-0002` and `rev-0003` were minted by
  readability repairs, `rev-0004` by the `P003` repair.
- Review rounds: `review` ran without `--review` for `rev-0003` and `rev-0004` (round 01 each). No reviewed
  round has run, because it is behind P4.
- `resume` at P4: "28 block(s) queued, 28 unreviewed, 0 stale"; open findings "none recorded: rev-0004 has
  no review file"; no seal.

### The stop and resume test

Run 1 did not need to stop, so a deliberate stop was tested after `check`, as the plan requires:

- **Stop:** `.docs-build/continuation.md` was written (iteration, budget used, findings, next actions) with P3
  open and no draft revision.
- **`resume`:** exit 0 and wrote nothing. It printed "no revisions: this build predates revision snapshots;
  run render" and the continuation note, flagged as unchecked. Its one suggested command was
  `pipeline.py render --root .`.
- **Was the suggestion right? No.** `render` was held at P3 (command 11). The right next step was to write the
  three analyses, rerun `check`, decide P3 and run `document`. The cause is `resume_step` in
  `plugins/docs/skills/document-codebase/scripts/pipeline.py` lines 1637-1638 (`if not latest or matches is not
  True: return command("render")`), which looks only at draft revisions and not at checkpoints or missing
  stages. Line 1679 also calls a build that is merely early one that "predates revision snapshots". `resume`
  is documented for the draft-review loop (`workflow.md`), so this is a gap in scope, not a regression.
- **Later `resume`, at P4 (command 23):** correct. It named `decide --checkpoint P4` and no earlier step.

### Problems found

Each was recorded and, where noted, worked around. None was fixed in the skill.

1. **`resume` suggests `render` before any draft exists** (above). Cause: `pipeline.py:1637-1638`, `1679`.
   Not worked around; the coder ignored the suggestion and followed `SKILL.md`.
2. **P3 is bound to the three analyses, but `SKILL.md` and `three-analyses.md` tell the agent to write them
   after `check` and before deciding P3.** Command 12: `P3 material changed since the checkpoint opened; rerun
   check`. Writing or editing any of the three files reopens P3 (it happened twice, commands 12 and 15), so
   the order the documents give needs a `check` rerun between writing and deciding. Worked around by
   rerunning `check` and deciding P3 again. No document says so.
3. **Flow step ids must be unique across flows.** `validate_flows: F005 id used more than once` for
   `flow:record-order-cli / step:1`. The example in `schemas.md` (`"id": "step:1"`) and its text do not say so.
   Worked around by naming the second flow's steps `step:cli-1`, `step:cli-2`.
4. **A `calls` claim cannot name a class as its object, and the schema's entity list does not say how to cite
   instantiation.** `V015 ... not 'method' to 'class'`. The message is clear, and one repair (`symbol:` form)
   fixed it. The second V015 was the coder's own `sed` also rewriting a derived `inherits` claim, which `check`
   caught.
5. **`loc` counts one line more than the file has, and the two validators disagree.** `scan_repo.py` returns
   `newlines + 1` (around line 309), so `cli.py` (15 lines) is indexed as 16, and `validate_analysis.py` (A007,
   around line 205) accepts evidence on line 16. The manual builder checks real file lines and refuses it
   (command 16). The module-analysis rows kept evidence the manual builder would refuse: `cli-s5` cites
   `cli.py:1-16`, `http-s1` cites `http.py:1-14` (13 lines), `store-s1` and `store-s4` cite `store.py:1-14`
   (13 lines). Worked around in the manual answers only; the analysis rows stand as `check` accepted them.
6. **Detector B fails an honest architecture on a layered repository.** The repository's directories are its
   layers, so components equal directories on 100% of module pairs and the gate reports `failed`. The
   components were not changed to avoid it, because splitting by something other than the layers would have
   been false.
7. **The "unanswered" reason lists five ids for a count of six** (`3.4.6` is missing from the list).
8. **Generated gap blocks name no gap.** Six of seven reader pages end with "The available repository evidence
   does not yet establish 1 detail(s) covered by this page." (P005 advisory). The reader cannot tell which
   detail, and the sentence is pipeline language in the reader edition.
9. **`data_flow.rst` shows only one of the two sequence diagrams.** `flow-record-order-http.puml` is on the
   page; `flow-record-order-cli.puml` was built and validated but is not placed.
10. **No Sphinx here.** `build check: skipped`; `editions: passed ... no Sphinx build was run`. The reader and
    audit editions were checked by text only.
11. **`manual-grounding.json` was not written by the coder.** `SKILL.md` rule 5 and `manual.md` say to map
    every question to sources first. No script reads, requires or checks the file, and the gate ran without it.
    The coder wrote each answer with its evidence directly. This is a deviation from the skill's instructions,
    and a point where the pipeline cannot tell.
12. **The coder wrote rows from small Python scripts.** The module analysis, the 57 answers, the 28 composed
    sections and the 28 `self_review` rows were each written by a script holding text typed by the coder, not
    generated from the packets. Each reading came from the packets and from running the code (next paragraph).
    This is how an agent appends JSONL, but the grader should know the files were not edited line by line.
13. **README versus code.** The README says orderlog "reports on" orders and "prints them back". No module does
    either, and `Store` has only `put`. The draft records this as a limit and does not describe it as behavior
    (`SKILL.md`: a README is data about the code).

Code behavior was also checked by running the copy with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src` (CLI exit
0, `Handler().post` return values, the `ValueError`, the `TypeError` after partial storage, `load()` with an
empty variable). That did not change the copy (`git status` clean).

### Time and turns

About 70 tool calls in one session. The only measured step is `source_reading` (65 s); the rest is an
estimate, and no wall time was taken for the whole run.

### For the grader

The drafts are in `/root/e2e-runs/layered-repo/.docs-build/rendered-docs/` (reader edition; audit blocks sit in
`.. only:: audit`), the kept revisions are under `.docs-build/drafts/`, and the answers are in
`.docs-build/manual-analysis.json`. The scope check from the plan, run in the build directory:
`python3 -c 'import json,collections;s=json.load(open("scope.json"));print(collections.Counter(r["disposition"] for r in s["files"]))'`.

## Run 2 — `shared/scripts`

- **Working copy:** `/root/e2e-runs/shared-scripts` at commit `642c1db`. Build directory:
  `/root/e2e-runs/shared-scripts/.docs-build`. `docs` version 1.7.1, `main` commit `49e213d` (the checkout the
  run started on; `main` has moved since, see the note at the end).
- **Prior knowledge, stated as the plan asks:** the coder had seen this codebase before. It is this
  repository's own `shared/scripts`, which the plugin's skill and the plan describe by name. The analysis rows
  were written from the packets, outlines and the source the coder read in this run (next section), not from
  memory, but some of the wording of roles (for example the component grouping) follows what the coder already
  knew.
- **Template and review mode:** the same 7-section `manual` selection as run 1; `self_review` throughout.
- **Where it ended:** at P4, open, with the draft at `rev-0003`. No `publish`, no P4 answer, no `docs/` in the
  copy. The run did not stop for budget reasons, so `continuation.md` was not written for this run (the
  deliberate stop was tested in run 1).

### How much source was read (the report's most important caveat)

`scope.json` ends with 0 unread product files, because a module with a row in `module-analysis.jsonl` counts
as `analyzed`. That count does not say how much of each file was read. The coder's own ledger
(`.docs-build/depth.tsv`) says:

| Depth | Files | What it means |
| --- | --- | --- |
| `full` | 10 | The body was read: `survey/scope_record.py`, `survey/build_scope.py` (from line 125), `analyze/derive_claims.py`, `build_dir.py`, `render/prepare_stage.py`, `render/snapshot_draft.py`, `review/validate_draft.py`, `review/seal_draft.py`, `publish/promote_docs.py`, `publish/editions.py` |
| `targeted` | 4 | One or two functions read: `survey/select_units.py`, `publish/quality_docs.py` (`detector_b`), `detect_stack.py` (`detect`, `main`), `pipeline.py` (`run`, the flag list, `resume_step`) |
| `outline` | 34 | Module docstring, imports, constants, function names with their line ranges and first docstring lines, and argparse and `raise` lines. The bodies were not read |

For the 34 `outline` files the coder lowered every statement the body would have to support (responsibility,
interface, interaction, failure) from `observed` to `inferred`; only constants stay `observed`. The result is
256 statements (87 observed, 51 declared, 114 inferred, 4 unknown). The gate reflects it as far as it can:
`analysis_mode: partial`, 25 of 48 modules answer all four kinds. The gate does not see reading depth, and it
would have passed the same files had the coder written them from docstrings alone. The 4 low-fan-in
checks: `detect_stack.py` (line 7 of `units.txt`, `analyzed`, `targeted`) and `publish/editions.py` (line 26,
`analyzed`, `full`) are both in `units.txt` and `analyzed` in `scope.json`.

### Commands, in order

| # | Command | Exit | The line that matters |
| --- | --- | --- | --- |
| 1 | `survey --root .` | 0 | `scope: 48 product, 1 asset`; `files 48 loc 21919`; `unresolved imports: 236`; `WARN the entry-point heuristic matched 33 of 48`; 107 settings (all argparse options) |
| 2 | `decide --checkpoint P1` | 0 | P1 decided |
| 3 | `template --use manual --sections ...` (piped to `head -2`) | 0 then `INTERNAL BrokenPipeError` | template was recorded; the traceback came from the coder's pipe |
| 4 | `measure ... start`, `analyze` | 0 | 48 packets, none partitioned; P2 open |
| 5 | `measure ... stop`, `decide --checkpoint P2` | 0 | `source_reading` 291.9 s of tool time |
| 6 | `check` | 0 | `claims: 603 verified`; 32 `A014` and 2 `A016` advisories; P3 open |
| 7 | `check`, `decide --checkpoint P3`, `document` | 0, 0, 1 | after the three analyses were written; first `document` run writes 57 unanswered slots, 855 facts |
| 8 | `document` (answers and pages written) | 1 | first attempt `FAIL 2.1.1: cites component:claims ... which nothing in this run verified`; second `FAIL 2.3.1: a basis of 'observed' must name a verified_id`; third `wrote doc.json: 7 page(s), 67 block(s)`, tolerated exit 1 from `build_flow_diagrams` (no flow traced) |
| 9 | `render --docs docs` | 0 | `rev-0001`; build check skipped, `editions: passed` |
| 10 | `readability.py ... --for-review` | 0 | four passages of 27 to 38 words; split |
| 11 | `review` | 1 | gate `failed`; 27 queued; 3 `P003` errors; P4 opened |
| 12 | `document`, `render`, `review` (repairs) | 0/1/1 | `rev-0002`, then `rev-0003`; 0 prose errors |
| 13 | `review --review prose-review.jsonl` | 1 | `held at checkpoint P4` |
| 14 | `resume`, `status` | 0 | `next ... decide --checkpoint P4 ...`; 48 read, 0 unread |

No other command was run, `publish` was not run, and P4 was not decided.

### Checkpoint notes recorded

- **P1:** "Unattended run: all 48 product files accepted as scope with no cap; one configuration asset
  excluded; no feature map found and setup-verification unavailable so continuing without one".
- **Template:** "Unattended choice by the coder: same manual subset as run one covering purpose, key operation,
  configuration and failure".
- **P2:** "Unattended: accepted 48 module roles; most rows rest on docstrings and outlines, flagged inferred;
  unknowns are listed in the report".
- **P3:** "Unattended: nine components grouped by purpose not directory; no flow traced because stages run by
  subprocess; operations quoted from the driver docstring". (Decided once; the analyses were written before
  `check` was rerun, so the P3 binding problem of run 1 did not recur.)

### Counts

- **`scope.json`:** `Counter({'product': 48, 'asset': 1})`; by reading, 48 `analyzed` and 1 `excluded`.
  Unread at the end: 0 (see the caveat above).
- **Analysis:** 48 module rows, 256 statements, 603 verified claims (none hand-written), 9 components covering
  all 48 modules, 0 flows (`absent`, with the reason that stages run as subprocesses), 3 procedures and 1
  requirement from the driver's docstring.
- **Manual:** 51 of 57 answered (`partial`), 27 sections composed, 1,122 prose words. The 6 `unknown` answers
  are the same ids as in run 1.

### Gate outcome (`generation-report.json`, at the state of the last plain `review`)

- `analysis_mode`: `partial`. `status`: `review_required` once reviewed rows exist (it was `failed` before).
- Reasons:
  1. "analysis mode is partial: 48 of 48 module(s) were read, but only 25 answer all four of responsibility,
     state, interface, failure";
  2. "manual leaves 6 of 57 question(s) unanswered: 1.1.7, 2.1.7, 2.2.5, 2.3.7, 3.1.8" (five ids named for six);
  3. "manual is missing required diagram(s): architecture/data_flow", because no flow was traced;
  4. "detector B: components and directories agree on 90% of module pairs";
  5. "27 block(s) have no fresh confirmed model review" (held behind P4).
- Before the repair: three `P003` errors ("calls" and "imports" over a statement that does not support them).

### Revisions, rounds and open findings (P4)

- Revisions `rev-0001` to `rev-0003`. `rev-0002` and `rev-0003` were minted by the readability and `P003` repairs.
- `prose-review.jsonl` holds 27 `self_review` rows: 21 `confirmed` and 6 `unresolved`
  (`architecture/overview:1`, `architecture/data_flow:3` and `architecture/module_reference:1` to `4`), because
  those sections rest on outline-depth reading or on the coder's own grouping. The rows were not consumed,
  because the reviewed pass is held at P4. `resume`: "27 block(s) queued, 27 unreviewed, 0 stale", no
  open findings, no seal.

### Stop and resume

No stop was needed in this run. The test of `continuation.md` and `resume` was done in run 1 (above). Its
result there (wrong suggestion before any draft exists, right suggestion at P4) was confirmed here: `resume` at
P4 named `decide --checkpoint P4` correctly.

### Problems found

1. **Reading depth is invisible to the gate** (above). 34 of 48 modules rest on outlines, and `scope.json` and
   `status` report "48 read, 0 unread". The only trace is the number of modules answering all four kinds
   (25 of 48), which depends on how many statements the author wrote, not on how much was read.
2. **A component's `inferred` status makes its id unusable as evidence.** `FAIL 2.1.1: cites component:claims
   ... which nothing in this run verified`. Only `declared` or `observed` components count. The message does
   not say that status is the reason. Worked around by removing the ids.
3. **`observed` needs at least one verified id, and the message says so** (`FAIL 2.3.1`), but a section that
   rests only on `inferred` modules has nothing to cite. Worked around by citing driver statements.
4. **`P003` is triggered by ordinary verbs.** "calls", "imports" and "uses" were refused for sections whose
   cited statement used no ranked verb; the repair was to reword (for example "serve"). The same happened in
   run 1.
5. **No flow, so the data-flow page fails its mandatory diagram.** The stages are subprocess calls, which the
   verifier cannot trace; `flow-analysis.json` is `absent` and the gate says "missing required diagram:
   architecture/data_flow". The prose on the page still traces the stage order, from the driver's `run`.
6. **Detector B at 90%** with components grouped by purpose across directories. Nine components, 3 of them
   spanning more than one folder, still agree with the directory partition on 90% of module pairs, because
   the repository is itself organised by purpose. Counted as a failing reason.
7. **Piping `template --use` into `head` produced `INTERNAL BrokenPipeError`**, exit 3 after the choice was
   written. A closed stdout is the coder's doing, but the driver prints an internal error where a quiet
   exit would do.
8. **`detect_stack.py` documents exit 2 for a usage error, and returns 1** for a missing directory or target
   (`detect_stack.py:25-26` against `968-973`). Found while reading the file, not by the pipeline.
9. **Line numbers differ between `shared/scripts/pipeline.py` and the plugin's copy** (`resume_step` is at
   1627 in the copy of `shared/scripts` and at 1630 in the plugin folder), so a citation to either needs its
   path. The coder cited the plugin's lines in run 1 and the `shared` lines here.
10. **The same minor problems as run 1 recurred:** the "unanswered" reason lists five ids for a count of six; the
    gap blocks read "does not yet establish N detail(s)"; the build check was skipped without Sphinx.
11. **`manual-grounding.json` was not written** and **rows were written from scripts** (problems 11 and 12 of run 1
    apply here too).
12. **Answer 2.3.1 first said "publish (13)"** and the folder has 12 scripts; the coder caught it on a recount
    and fixed the answer, which did not change the rendered page. An example of why a count in prose needs
    its source cited.

### Time and turns

About 55 tool calls after run 1. `source_reading` was measured at 291.9 s; the rest is an estimate.

### For the grader

The drafts are in `/root/e2e-runs/shared-scripts/.docs-build/rendered-docs/`; kept revisions under
`.docs-build/drafts/`; answers in `.docs-build/manual-analysis.json`; the reading ledger in
`.docs-build/depth.tsv`. Weak spots to grade first: the 34 outline-depth modules, the nine-component grouping,
and any claim about a function's inner behavior outside the ten fully read files.
