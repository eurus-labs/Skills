# Plan 23 — `analyze-requirements`: compare a requirement with its previous version, resolve open points with the PO, then split epics

Status: approved
Date: 2026-11-25
Branch: `feat/reasoning-analyze-requirements`
Baseline: `origin/main` at `2b81ebf557ea1f5f394ae967b6a5c7a892ddc253`
Target: a new skill `plugins/reasoning/skills/analyze-requirements/`, the `reasoning` plugin manifest, README
and version, the root catalog, `CHANGELOG.md`, a new fixture, and eval cases

## Goal

The user works through requirements in a fixed loop:

1. A new requirement arrives. It is compared with the previous version, and the differences are analysed.
2. Open points are discussed with the Product Owner (PO).
3. Each discussion yields a **DoU** (Discussion of Understanding) file, and the requirement analysis is updated
   from it.
4. When nothing is left open, the analysis is split into **epics**.

The analysis is always a Markdown file. Today no skill supports this loop. `design-solution` designs a change,
and `write-plan` writes an implementation plan, but neither compares requirement versions, tracks open
points, or produces epics.

When this is done, a new skill, `analyze-requirements`, runs all three steps on one set of files that share
one ID scheme:

- **analyse:** compare the current requirement with the previous one, check both against the repository's
  code, and write `analysis.md` with every difference and open point;
- **update from a DoU:** draft a DoU from the user's notes of the PO discussion, or read one the user brings,
  then update `analysis.md`, closing only the open points the PO actually answered;
- **split epics:** write `epics.md` from the analysis, once no blocking open point remains.

## Decisions

1. **One skill, three steps** (the user's choice, 2026-11-25).
   - The skill is named `analyze-requirements` and lives in the `reasoning` plugin (the user's choice). It
     comes before `design-solution` and `write-plan` in the chain: clarify the problem, then design, then
     plan, then hand off.
   - It works out which step to run from the request and from the files already in the topic folder (no
     `analysis.md` → analyse; a new DoU or PO notes → update; "split into epics" → epics). It says which
     step it chose.
   - Rejected: a separate `split-epics` skill, because the epics depend on the same IDs and open-point state.
2. **Inputs** (the user's choice): the current requirement and an optional previous version, each as a
   `.md`, `.txt` or `.rst` file, or pasted into the conversation.
   - The previous version may be another file, or the same file at an earlier git revision (`git show
     <rev>:<path>`). The analysis records which revision it used.
   - With no previous version, this is a first analysis, and every requirement is `added`.
   - Other formats (`.docx`, `.pdf`, Confluence, Jira) are out of scope. The skill asks for a text export.
3. **A bundled stdlib script makes the comparison mechanical, and the agent makes it meaningful.**
   `scripts/requirements.py diff <previous> <current>`:
   - splits each document into units (headings and sections for Markdown and reStructuredText, numbered
     and bulleted items, and paragraphs for plain text), each with its file and line range;
   - matches the units of the two versions and prints JSON, each unit `added`, `removed`, `changed` (with
     both line ranges) or `unchanged`.

   The agent then reads every non-`unchanged` unit, and the units around it, and decides what the change
   means. A reworded unit with the same meaning is recorded as `unchanged (wording)` with both quotes, not
   dropped.

   Rejected: comparing by reading alone, which misses changed numbers and dropped items in long documents.
4. **The repository's code is checked** (the user's choice). When the session is in a repository:
   - The skill finds the code each changed requirement touches and reads it.
   - It records each requirement's impact as `new` (nothing implements it), `changes existing behavior`, or
     `already met`, with `path:line`. A claim about code is made only after reading that code.
   - A requirement that contradicts what the code does now is an open point.
   - The skill changes no code.

   Outside a repository, it records "code not checked".
5. **The artifacts are always files** (the user's choice), in one topic folder, `requirements/<topic>/` by
   default, or a folder the user names:
   - `analysis.md`, from `references/analysis-template.md`, holds:
     - the sources, with their paths and revisions;
     - a change table with one row per requirement: ID `R-001…`, status, both source quotes with `path:line`,
       and code impact;
     - the findings per requirement: ambiguous, missing, conflicting, untestable, or non-functional gap;
     - the open points `OP-001…`, each with:
       - the question for the PO;
       - the requirement IDs it affects;
       - whether it blocks the epic split;
       - its status, `open` or `resolved`;
       - the DoU that resolved it;
     - the assumptions, each with its owner and the risk if it is wrong;
     - a revision history.
   - `dou-NNN.md`, from `references/dou-template.md`, holds:
     - the date and participants;
     - for each open point discussed: the question, the PO's answer as given, the decision, who confirmed
       it, and the requirement IDs it changes;
     - the new open points the discussion raised.
   - `epics.md`, from `references/epics-template.md`, holds, for each epic `E-01…`:
     - its goal;
     - the requirement IDs it covers;
     - its acceptance criteria;
     - its dependencies on other epics;
     - its risks;
     - its code areas.

     It ends with a traceability table showing every in-scope requirement and its epic.

   The artifacts are written in the language of the requirement. The skill writes the files but never commits
   them unless the user asks.
6. **A DoU is drafted or read** (the user's choice, "both").
   - **If the user brings a DoU, the skill reads it.**
   - **If the user brings only notes, it drafts `dou-NNN.md` first, and shows it to the user.**
     - It records only what the notes say the PO said.
     - A point the notes leave unanswered stays `open`. The skill never answers for the PO and never turns an
       assumption into a decision.
   - **Then it updates `analysis.md`:**
     - It sets each answered open point to `resolved`, with its DoU.
     - It applies each decision to the requirements it changes. Changed rows keep their previous text, marked
       superseded, and are never deleted.
     - It adds any new open points.
     - It appends a revision-history line naming the DoU.
7. **Epics only when nothing blocks.** `epics.md` is written only when no open point marked blocking is
   `open`.
   - If any is, the skill lists them and stops.
   - If the user explicitly asks for epics anyway, `epics.md` is headed `Provisional`. Each epic that depends
     on an open point names it.
   - Every in-scope requirement appears in exactly one epic, or in a "Not in any epic" list with the reason.
8. **A second subcommand checks the files**: `scripts/requirements.py check <topic-folder>` fails, naming the
   line, when:
   - an ID is duplicated;
   - an epic or a DoU references an unknown `R-` or `OP-` ID;
   - a `resolved` open point names no DoU, or names a DoU that does not exist;
   - an in-scope requirement is in no epic and not in the "not in any epic" list;
   - `epics.md` exists and is not `Provisional` while a blocking open point is `open`.

   The skill runs `check` after every write and fixes what it reports. The script is stdlib-only Python 3.9+,
   reads only the files it is given, and writes nothing.
9. **Plugin changes.**
   - Add `"./skills/analyze-requirements/"` to `skills` in both `plugin.json` copies.
   - Bump `reasoning` from 0.3.0 to **0.4.0** in all four version files.
   - Widen the plugin `description` to cover requirement analysis, in both `plugin.json` copies and both
     `marketplace.json` entries.
   - Update `plugins/reasoning/README.md` and the root catalog row.
   - Add a `CHANGELOG.md` `[Unreleased]` `### Added` entry.
   - Add a "use analyze-requirements instead" hand-off to the descriptions of `design-solution` and
     `write-plan`, so that they do not compete for "analyze this requirement".
10. **Evals.**
    - **Trigger cases:** two that must fire ("Compare this requirement with the previous version and analyze
      what changed", "Cập nhật requirement analysis từ DoU với PO") and one that must stay quiet ("How would
      you design the export feature?", which belongs to `design-solution`). Use the format of
      `plugins/reasoning/evals/trigger/`.
    - **Behavior case:** a new fixture, `fixtures/17-requirement-change/`. It holds:
      - `requirements/v1.md` and `requirements/v2.rst`, so that both formats are exercised;
      - a small code module.

      Between the versions, plant exactly:
      - one added requirement;
      - one removed requirement;
      - one changed number, such as a limit going from 50 to 100;
      - one ambiguous new sentence;
      - one requirement that contradicts the code.

      Add `EXPECTED.md` §17 and a `fixtures/README.md` row, and generate a `scaffold.sh` with
      `tools/build_eval_scaffolds.py`, leaving out the fixture's README.

      The prompt asks for an unattended analysis of `v2.rst` against `v1.md`. The graders are:
      - `used-skill` (with-only);
      - `analysis.md` written;
      - `epics.md` not written, because blocking open points remain;
      - an `llm` grader with `focus` on the analysis file, which needs all five planted items, the
        contradiction cited with `path:line`, and no invented PO answer.

    The planner runs the cases during review, with a cost ceiling the user agrees to, and the coder records the
    results in `doc/eval-results.md`.

## Scope

In:

- `plugins/reasoning/skills/analyze-requirements/`:
  - `SKILL.md`, under ~500 lines;
  - `references/analysis-template.md`, `references/dou-template.md` and `references/epics-template.md`;
  - `scripts/requirements.py`.
- Tests for the script: a new `tools/test_requirements_script.py`, covering `diff` for each format and
  `check` for each rule in Decision 8, with failure cases.
- The plugin manifests, README, versions, descriptions, root catalog and `CHANGELOG.md` (Decision 9).
- The hand-off sentence in the `design-solution` and `write-plan` descriptions.
- `fixtures/17-requirement-change/`, `fixtures/EXPECTED.md` §17, the `fixtures/README.md` row, the eval
  cases, the scaffold and `tools/build_eval_scaffolds.py`.

Out:

- **`.docx`, `.pdf`, Confluence or Jira input**, and a Jira CSV export of the epics.
- **Splitting epics into stories or tasks.**
- **Sending anything to the PO.** The skill drafts questions, and the user takes them to the PO.
- **Changing code.**
- **Changes to `coder-handoff`.**

## Baseline

| Existing | Keep, change, or remove |
| --- | --- |
| `plugins/reasoning/.github/plugin/plugin.json` and `.claude-plugin/plugin.json`: version 0.3.0, three skills | Add the skill, bump to 0.4.0, widen the description |
| `plugins/reasoning/skills/write-plan/references/plan-template.md` | Model for the three templates' style |
| `plugins/reasoning/skills/design-solution/SKILL.md` and `write-plan/SKILL.md` descriptions | Add the hand-off to `analyze-requirements` |
| `plugins/reasoning/evals/trigger/*` (8 cases) | Format for the new trigger cases |
| `plugins/_template/skills/example-skill/SKILL.md` | Start the new `SKILL.md` from it |
| `tools/build_eval_scaffolds.py` `SCAFFOLDS`; `fixtures/16-flawed-skill` (plan 19) | Pattern for the fixture and scaffold |

## Tech stack and constraints

- Default: `scripts/requirements.py` is stdlib-only Python 3.9 or later, makes no network call and writes
  nothing, so `SKILL.md` declares no side effects beyond the artifact files the agent writes.
- reStructuredText is split by its heading underlines, not by a docutils parse, so nothing is installed.

## Acceptance criteria

- [ ] **The skill installs.** `python3 tools/validate.py` passes, with `analyze-requirements` listed in both
      `plugin.json` copies, and `reasoning` is 0.4.0 in all four files.
- [ ] **`diff` handles every format.**
  - For `.md`, `.rst` and `.txt` pairs, the units carry correct line ranges.
  - Added, removed, changed and unchanged are each detected.
  - A changed number inside an otherwise identical item is `changed`.

  Checked by `tools/test_requirements_script.py`.
- [ ] **`check` catches each rule of Decision 8, as failure cases.** It fails, naming the line, for:
  - a duplicated ID;
  - an unknown ID in an epic;
  - a resolved open point with no DoU;
  - a requirement in no epic;
  - non-provisional epics with an open blocking point.

  It passes on a consistent folder. Checked by the same test file.
- [ ] **The rules are in `SKILL.md`:**
  - never answer for the PO;
  - superseded rows are kept;
  - epics only when nothing blocks, unless the user explicitly asks;
  - code claims only after reading, with `path:line`;
  - run `check` after every write.

  Checked by reading.
- [ ] **The descriptions do not compete.**
  - `design-solution` and `write-plan` name `analyze-requirements` as the skill for requirement analysis.
  - The trigger cases pass. In particular, the quiet case does not fire `analyze-requirements`, and the fire
    cases do.

  Checked by the planner's run.
- [ ] **Fixture 17 holds exactly the five planted changes**, and `EXPECTED.md` §17 lists them. The scaffold
      leaves out the README and `EXPECTED.md`. Checked by
      `python3 tools/build_eval_scaffolds.py --check` and
      `grep -l "EXPECTED\|README" plugins/reasoning/evals/behavior/*/scaffold.sh`, which must print nothing.
- [ ] **The behavior case passes with the plugin, by the planner during review**:
  - `analysis.md` is written;
  - `epics.md` is not written;
  - all five planted items are found;
  - no PO answer is invented.

  A failure is recorded with what its trace shows.
- [ ] **Required checks pass:** `python3 tools/validate.py`, `python3 tools/materialize.py --check`, and
      `for t in tools/test_*.py; do python3 "$t" || break; done`.

## Risks

| Risk | How it is handled |
| --- | --- |
| The agent fills an open point with a guessed PO answer | Decision 6 forbids it. The DoU records only what the notes say, the behavior grader fails an invented answer, and `check` needs a DoU for every resolved point |
| Rewording looks like a change, or a real change hides in a rewording | The script flags both as `changed`, and the agent records `unchanged (wording)` with both quotes, so a reader can check |
| History is lost when a DoU updates the analysis | Superseded rows are kept, and every update adds a revision line |
| The new skill steals triggers from `design-solution` or `write-plan` | Hand-off sentences in both descriptions, and a quiet trigger case |
| Epics are split while a blocking question is open | Decision 7, and `check` fails non-provisional epics while a blocking point is open |
| `SKILL.md` grows past its size rule | The templates and the output formats live in `references/` |

## Open questions

None.
