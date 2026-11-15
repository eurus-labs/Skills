# Skill manager — page redesign

Status: **proposal**. Nothing here is implemented. It describes a redesign of the page that
`tools/skill_manager.py` serves (markup and script in `tools/build_eval_board.py`), drawn as a
clickable mock-up. The mock-up lives on a private design canvas and is not part of this repository.

## Baseline

The design builds on the one-tab layout in branch `feat/tools-eval-board-one-tab`
("fold the skills tab into the evals tab"), which is **not on `main` yet**. That branch replaces
the Skills tab with an Evals tab whose skill rows open to their cases. `main` still has three tabs.
Implementing this design should start after that branch merges, or on top of it.

What the page does today, and keeps doing:

- **Evals**: one row per skill with its goal, plugin version, install state per host, case counts
  per direction (must fire · must stay quiet · behavior), latest result per host and a status. A row
  opens to its cases grouped by direction; each case has its prompt, graders, run history and a
  Run form. "Run all cases…" runs the skill's cases in turn.
- **Install**: plugin versions in this checkout and in each host, Install / Update / Uninstall per
  plugin or for all, and registering the marketplace. Every action shows its command and runs only
  after the person confirms.
- **Runs** stream their output and ask grading questions with Yes / No / Skip.

## Decisions taken

| Question | Decision |
| --- | --- |
| Tabs | **Two: Evals and Install**, as in the one-tab branch. The redesign changes layout, not structure |
| Install with more than two hosts | **A platform selector.** One host is shown at a time, so a new host adds a button, not a column |
| Install row buttons | **Fixed slots.** Install or Update always sits in the first slot, Uninstall in the second, so buttons line up on every row |
| Grading buttons | **Tinted, with an icon.** Yes: green tint and ✓. No: red tint and ✕. Skip: neutral and →. Colour is not the only cue |

## Screens

### Evals

- Header: the two tabs, host status, EN/VI switch (both languages already exist in the board's
  strings).
- Summary: eval cases, skills with a case, trusted scores, result files read — the board's
  existing counters.
- Search and status filters (All, Not run, No evals).
- Skill list. Each row shows name, plugin and version, goal, three direction counts (a zero gets a
  dashed red outline, as the board does now), install chips per host and a status badge. A row
  expands in place to a "Run all N cases" bar and the three direction groups.
- Case panel on the right. Clicking a case shows its description, prompt, graders (each tagged
  `tool`, `llm` or `regex`), runs and the **Run this case** form (host, arms, model, cost ceiling).
  Today this detail opens inline in the list; the panel keeps the list short while reading a case.

### Run

- A full view of the current job instead of the corner panel: back link, status pill, "case X of
  N", cost ceiling, **Stop**, and a progress bar.
- Left: the waiting question with Yes / No / Skip and links to the transcripts, then a tally of
  answers so far.
- Right: the live output, colour-coded by line kind (command, agent action, grader match, question).
- When stopping or finished, the question card is replaced by a message saying what happens next.

### Install

- A row of platform buttons. Each shows the host name, a status dot and "x of 7 installed", or
  "not found on PATH". Choosing one shows only that host below.
- A marketplace card: where the marketplace is registered from, with Register from this checkout,
  Register from GitHub and Update marketplace.
- A plugin table with four columns: plugin and its skills, version in this checkout, version in the
  chosen host, and the fixed action slots. Install all and Update all sit above the action column.
  Version chips: installed (green), older than this checkout (amber, "older"), disabled (grey), not
  installed (dashed).
- A confirm bar that shows the exact command before anything runs, then a "Running …" notice.
- A host that is not on PATH shows how to fix it instead of the table.

## What the mock-up shows that is not real data

- Plugin names, versions, skill goals, case names and the per-skill split come from the catalog
  on the one-tab branch. Prompts and graders are real for three cases only
  (`verify-change-catches-unwired-expiry`, `verify-change-working-tree`, `none-review-code`); the
  rest are placeholders.
- Install state per host, the older `docs` copy, the disabled `code-review` copy, the marketplace
  sources, the log lines and the third grading question are illustrative.
- "[Next platform]" is a placeholder for a third host.

## Open questions

- **Install chips on Evals rows.** Per-host chips grow with every host. A count ("2 of 3
  platforms") with detail on hover would scale; not decided.
- **Hosts as data.** `HOSTS` is a fixed mapping in `tools/skill_manager.py`, and the page script
  has its own host list. A selector only scales if both read one list.
- **Not-registered state.** The page handles a host with no marketplace; the mock-up does not
  draw it yet.
- **Run view or corner panel.** The full view needs a way back to the case list while a job runs.

## Implementing it

- Keep the server's rules unchanged: `127.0.0.1` only, the token, one job at a time, and commands
  built only by the server.
- Cover the new behaviour in `tools/test_eval_board.py` and `tools/test_skill_manager.py`:
  platform switching, aligned action slots, and the confirm step on every action.
- Update `doc/running-evals.md` and `CHANGELOG.md` when the page changes.
