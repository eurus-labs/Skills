# Plan 25 — a `planning` plugin: requirement analysis with a DoU, software requirements, then epics

Status: draft
Date: 2026-11-26
Branch: `feat/planning-requirements-to-epics`
Baseline: `origin/main` at `c24e3eb106ec68015b519fc78e883466d6813cdd` (marketplace 0.5.0)
Target: a new plugin `plugins/planning/` with three skills; `analyze-requirements` moved out of `reasoning`;
`shared/`; the marketplaces, catalog, `CHANGELOG.md`, fixtures and evals
Supersedes: plan 24 (`feat/backlog-split-epics`, never merged). Its work may be reused (Decision 9).

## Goal

The user refined how a tech lead turns a requirement into work (2026-11-26):

1. **Requirement analysis.** The tech lead analyses the requirement to understand what has to be built.
   - Every unclear point goes into the **DoU** (Discussion of Understanding) with the Product Owner (PO).
   - The **DoD** (Definition of Done) agreed with the PO is the bar the requirements must meet.
   - Analysis and discussion repeat until the DoU has no open point, and the result is the requirement
     analysis file.
2. **Software requirements.** The analysed requirements are the **system requirements**. Each is derived
   into **software requirements**.
3. **Epics.** The software requirements are grouped by category into epics.

The inputs are:

- the requirement, as a Markdown file or read from a requirement repository;
- the DoD;
- the DoU;
- the codebase.

Today `analyze-requirements` sits in `reasoning` (0.4.0, released in marketplace 0.5.0). It does steps 1 and
3, has no DoD, has no software requirements, and spreads the open points across `analysis.md` and one
`dou-NNN.md` per meeting.

When this is done, a new plugin, **`planning`**, holds the whole chain as three skills that share one ID scheme
and one check script:

| Skill | Reads | Writes |
| --- | --- | --- |
| `analyze-requirements` | requirement (+ previous version), DoD, `dou.md`, code | `analysis.md` (system requirements `SYS-`), `dou.md` (points `DOU-`) |
| `derive-software-requirements` | final `analysis.md`, DoD, code | `software-requirements.md` (`SWR-`) |
| `group-epics` | `software-requirements.md` | `epics.md` (`E-`) |

## Decisions

1. **One plugin, `planning`, version 0.1.0** (the user's choice, 2026-11-26).
   - `analyze-requirements` moves to it from `reasoning`, and `reasoning` goes back to designing, planning
     and handing off.
   - Rejected: keeping the chain in `reasoning`, or splitting it into `backlog` (plan 24).
   - **Breaking change for `reasoning` users:** `reasoning` 0.4.0 → **0.5.0** drops `analyze-requirements`.
     Record it under `### Breaking changes` in `CHANGELOG.md`: install `planning` to keep it.
   - `design-solution` and `write-plan` hand requirement work to the `planning` plugin's skills.
   - Add `planning` to both marketplace copies and the root catalog. Update the `reasoning` README,
     description and catalog row.
2. **The DoD is read, never written** (the user's choice).
   - The user gives a DoD file (`.md`, `.txt` or `.rst`).
   - `analyze-requirements` checks every system requirement's acceptance criteria against it. A requirement
     that cannot meet the DoD (no measurable criterion, no number for a performance target, …) becomes a
     DoU point.
   - `derive-software-requirements` writes verification criteria that satisfy it.
   - With no DoD, the skill asks for one, or records "DoD not given" as a DoU point that does not block.
3. **One living DoU file** (the user's choice): `dou.md` in the topic folder holds every point for the PO.
   - Each point `DOU-001…` has:
     - the question;
     - the `SYS-` IDs it concerns;
     - `Blocks: yes|no`;
     - `Status: open|closed`;
     - the PO's answer as given;
     - the date;
     - who confirmed it.
   - **Each analysis pass adds points.** After each discussion, the user brings notes or an edited `dou.md`.
     The skill records **only what the PO said**, closes the points the PO answered, and applies each answer to
     `analysis.md`. Superseded rows are kept, never deleted.
   - `analysis.md` carries no open-point table. It refers to `DOU-` IDs.
   - `analysis.md` is `Status: final` only when no blocking DoU point is open. Until then it is `draft`.
   - This replaces `dou-NNN.md` and the `OP-` table.
4. **`analyze-requirements` keeps what plan 23 built, except the epic step.**
   - It keeps the sources step (ask where the requirement, the requirement repository and the code live;
     clone only a named repository after the user confirms the destination; never in an unattended run).
   - It keeps the version `diff`, the code check (list the workspace first), "never answer for the PO", and
     `check` after every write.
   - Its requirements are now **system requirements**, `SYS-001…`. They replace `R-`.
   - It never writes software requirements or epics. When `analysis.md` is final, it names
     `derive-software-requirements`.
5. **`derive-software-requirements`, in the style of ASPICE SYS → SWE** (the user's choice).
   - **Input:** a `final` `analysis.md`. If it is still `draft` with a blocking DoU point open, list the
     points and stop. On an explicit request, write a file headed `Provisional`.
   - **Output: `software-requirements.md`.** Each `SWR-001…` has:
     - one statement, "The software shall …";
     - its rationale;
     - its trace to one or more `SYS-` IDs;
     - its type: functional, or non-functional with the quality named;
     - verification criteria that are testable and meet the DoD;
     - the affected component or code area, as `path:line` after reading the code;
     - its status: `new`, `changes existing behavior`, or `already met`.
   - **A two-way traceability table.** Every in-scope `SYS-` has at least one `SWR-`, or appears in "Not
     derived to software" with its reason (a manual or process step, or hardware). Every `SWR-` traces to an
     existing `SYS-`.
   - **Rules:**
     - state what the software shall do, never how to build it;
     - one testable statement per `SWR-`;
     - never invent a requirement that no `SYS-` supports. A gap found while deriving becomes a new DoU point
       for `analyze-requirements`, and the skill does not edit `analysis.md` or `dou.md` itself.
6. **`group-epics`.**
   - **Input:** `software-requirements.md`, which must pass `check` and must not be `Provisional`, unless the
     user explicitly asks.
   - **Output: `epics.md`.** It states the grouping basis first: user outcome by default, or component or
     category if the user asks. Each epic `E-01…` has:
     - a goal;
     - its `SWR-` IDs;
     - acceptance criteria drawn from its software requirements' verification criteria and the DoD,
       including a negative case;
     - dependencies;
     - risks;
     - code areas.
   - Every `SWR-` is in exactly one epic.
   - The file ends with a traceability table, `SYS-` → `SWR-` → `E-`.
   - It never edits the earlier files.
7. **One script, in `shared/`.** `shared/scripts/requirements/requirements.py` is stdlib-only, makes no network
   call and writes nothing. `tools/materialize.py` copies it into all three skills through
   `plugins/planning/shared.manifest`.
   - `diff` is unchanged from plan 23 (with the Codex fixes).
   - `check <topic-folder>` checks the new formats. It fails, naming the line, on:
     - a duplicated or unknown ID;
     - a `closed` DoU point with no answer or no date;
     - an `analysis.md` marked `final` while a blocking DoU point is open;
     - an in-scope `SYS-` with no `SWR-` and not in "Not derived";
     - an `SWR-` tracing to no existing `SYS-`;
     - an `SWR-` in no epic, or in two;
     - a non-provisional `software-requirements.md` or `epics.md` over a `draft` analysis.

     IDs quoted from the source are never read as references.
   - Point `tools/test_requirements_script.py` at the shared source. Rewrite its `check` tests for the new
     rules, with a failure case for each.
8. **Templates and references.** Each skill has its own templates in `references/`, and no `SKILL.md` links
   outside `plugins/planning/`:
   - `analysis-template.md`, `dou-template.md`, `software-requirements-template.md` and
     `epics-template.md`;
   - a short `formats.md` per skill for the tables `check` reads.

   Every artifact goes in the topic folder (`requirements/<topic>/` by default). Each is written in the
   language of the requirement and never committed unless the user asks.
9. **Reuse, and the migration from plan 23 and plan 24.**
   - Move `plugins/reasoning/skills/analyze-requirements/` into `plugins/planning/skills/`, then rework it as
     above.
   - Move its evals and fixture 17 with it: `plugins/reasoning/evals/*/analyze-requirements-*` go to
     `plugins/planning/evals/`.
   - Plan 24's branch, `feat/backlog-split-epics`, may be read for reuse: the `shared/` move of
     `requirements.py`, the `split-epics` rules and fixture 18's settled and blocked layout. Build on `main`,
     not on that branch.
10. **Evals.**
    - **Trigger cases:** two that must fire and one that must stay quiet for each of the three skills. The
      quiet cases point at a neighbouring skill:
      - "Split these software requirements into epics" must not fire `derive-software-requirements`;
      - "Derive software requirements from this analysis" must not fire `group-epics`;
      - "How would you design the export?" must not fire `analyze-requirements`.
    - **`reasoning`** keeps its 8 original trigger cases and loses the `analyze-requirements` ones.
    - **Behavior cases:**
      - **`analyze-requirements-flags-planted-changes`** on fixture 17, which gains a `dod.md` whose criteria
        the vague "finish quickly" sentence fails. Its graders are updated:
        - `analysis.md` and `dou.md` are written;
        - the `llm` grader checks the five planted changes, the `DOU-` points, every point left `open`, the
          DoD gap, and the code contradiction with `path:line`;
        - neither `software-requirements.md` nor `epics.md` is written.
      - **`derive-software-requirements-from-final-analysis`** on a new fixture 18, holding a final
        `analysis.md`, a closed `dou.md`, a `dod.md` and the code. Its graders:
        - the file is written;
        - an `llm` grader checks that each in-scope `SYS-` traces to a "shall" `SWR-` with verification
          criteria that meet the DoD and a code area, and that no requirement is invented;
        - `analysis.md` is untouched.
      - **`derive-software-requirements-refuses-while-blocked`** on fixture 18's variant with one blocking
        DoU point open. No file is written, and the reply names the point.
      - **`group-epics-from-software-requirements`** on fixture 18's variant that holds a
        `software-requirements.md`. Its graders:
        - `epics.md` is written;
        - every `SWR-` is in exactly one epic, per `check` run by a regex or `llm` grader;
        - the grouping basis is stated;
        - acceptance criteria are given per epic.
    - Add `EXPECTED.md` §17 updates, a new §18, `fixtures/README.md` rows, and scaffolds from
      `tools/build_eval_scaffolds.py` that leave every fixture's README out.
    - The planner runs the evals during review, with a ceiling the user agrees to. The coder records the
      results in `doc/eval-results.md`.
11. **No release in this plan.** The next release PR carries `planning` 0.1.0 and `reasoning` 0.5.0.

## Scope

In:

- `plugins/planning/`: the manifests, README, `shared.manifest`, and three skills with their references and
  generated scripts.
- `plugins/reasoning/`: remove `analyze-requirements`; bump to 0.5.0; update the descriptions of
  `design-solution` and `write-plan`, the README and the catalog row.
- `shared/scripts/requirements/requirements.py` and `tools/test_requirements_script.py`.
- Both marketplaces, the root catalog, and `CHANGELOG.md` `[Unreleased]` (Breaking changes, Added).
- Fixture 17 (`dod.md`, and its `EXPECTED.md` update), fixture 18 and its variants, the eval cases and the
  scaffolds.

Out:

- **Stories, estimation, and a Jira or CSV export.**
- **Writing or editing a DoD.**
- **`.docx`, `.pdf`, Confluence or Jira input.**
- **Merging plan 24.** Its branch stays unmerged, and the user deletes it.
- **A marketplace release.**

## Baseline

| Existing | Keep, change, or remove |
| --- | --- |
| `plugins/reasoning/skills/analyze-requirements/` (plan 23) | Move to `planning` and rework (Decisions 3 and 4) |
| Its `references/` templates (`analysis`, `dou`, `epics`, `diff-output`) | Rework into Decision 8's set |
| Its `scripts/requirements.py` (`diff`, `check`) | Move to `shared/`, and extend `check` (Decision 7) |
| `plugins/reasoning/evals/*/analyze-requirements-*`, `fixtures/17-requirement-change/` | Move the evals; extend the fixture with `dod.md` |
| `tools/test_requirements_script.py` | Repoint, and add the new `check` tests |
| `plugins/docs/shared.manifest`, `tools/materialize.py` | The pattern for `planning/shared.manifest` |
| Branch `feat/backlog-split-epics` (plan 24) | Read only, for reuse |

## Tech stack and constraints

Default. Stdlib-only Python 3.9 or later. The skills' side effects are declared in each `SKILL.md`: the
artifact files, and for `analyze-requirements` the `git clone` and `git fetch` the user confirms.

## Acceptance criteria

- [ ] **The plugin installs.** `python3 tools/validate.py` passes with `planning` 0.1.0 holding its three
      skills, and with `reasoning` at 0.5.0 without `analyze-requirements`.
- [ ] **One script source.** `python3 tools/materialize.py --check` passes, with all three copies generated
      from `shared/`.
- [ ] **`check` enforces Decision 7.** `tools/test_requirements_script.py` has a failing case for each rule
      and a passing case for a consistent folder, and the IDs quoted from the source still pass.
- [ ] **The skills stay within their lanes.**
  - `analyze-requirements` never writes `software-requirements.md` or `epics.md`.
  - `derive-software-requirements` never edits `analysis.md` or `dou.md`.
  - `group-epics` edits nothing before it.

  Checked by reading each `SKILL.md`, and by the behavior graders.
- [ ] **The DoU loop.** `analyze-requirements` writes a single `dou.md`, never answers for the PO, and marks
      `analysis.md` final only when no blocking point is open. Checked by reading, by `check`, and by the
      behavior case.
- [ ] **Failure case:** `derive-software-requirements-refuses-while-blocked`. With the plugin, no run writes
      `software-requirements.md`, and each run names the blocking DoU point. Checked by the planner's run.
- [ ] **Triggers separate.** Every trigger case in `planning` and `reasoning` passes, and no quiet case fires
      its skill. Checked by the planner's run.
- [ ] **The breaking change is recorded**, and `reasoning`'s descriptions name `planning`.
- [ ] **Required checks pass:** `python3 tools/validate.py`, `python3 tools/materialize.py --check`,
      `python3 tools/build_eval_scaffolds.py --check`, `grep -rn "focus: files" plugins/*/evals` printing
      nothing, and `for t in tools/test_*.py; do python3 "$t" || break; done`.

## Risks

| Risk | How it is handled |
| --- | --- |
| Three skills compete on "requirement" requests | Each description names its neighbours ("use … instead"), there is a quiet case per skill, and `validate.py` overlap warnings are read |
| A software requirement is invented, or turns into a design | Rule: every `SWR-` traces to a `SYS-`, and states what, not how; the `llm` grader fails an invented one |
| The DoU drifts from the analysis | One `dou.md`; `check` ties closed points to answers and dates, and ties `final` to no open blocking point |
| `reasoning` users lose `analyze-requirements` after updating | Breaking change in `CHANGELOG.md`; `design-solution` and `write-plan` name `planning` |
| The plan is large for one coder run | It is split into commits per skill, with a push after each, so a cut-off run resumes |

## Open questions

None.
