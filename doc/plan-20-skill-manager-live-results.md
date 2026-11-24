# Plan 20 — the skill manager redraws itself when a new eval result appears

Status: draft
Date: 2026-11-24
Branch: `feat/tools-skill-manager-live-results`
Baseline: `origin/main` at `efe98efb8c1aacfde416de66a428885a64d691c7`
Target: `tools/skill_manager.py`, `tools/build_eval_board.py`, their tests, `doc/running-evals.md`,
`CHANGELOG.md`

## Goal

`tools/skill_manager.py` serves the eval board. Today the page reloads results in only one case: a job that
the page itself started has ended (`build_eval_board.py:838-842`). It does so once, after the job's last
case. The page never notices results that come from anywhere else:

- `claude plugin eval` or `tools/copilot_eval.py` run in a terminal;
- result folders copied in from another machine, such as a cloud session (`doc/running-evals.md`,
  troubleshooting);
- the earlier cases of a multi-case run that is still going.

The user has to reload the page by hand, and the reload loses the open skill, the selected case and the
search.

When this is done, an open skill-manager page shows a new or rewritten `aggregate-result.json` within about
5 seconds, from any source. It keeps what the user had open, and it does no work on the server beyond
listing the result files.

## Decisions

1. **The page redraws on every new result, whatever wrote it** (the user's choice, 2026-11-24).
   - Rejected: redrawing after each case of a page-started run only, which still misses terminal runs and
     copied results.
   - Rejected: a reload button only, which still needs a click.
2. **A cheap signature endpoint, `GET /api/results`**, returning `{"signature": "<hex>", "count": <n>}`.
   - The signature is a SHA-1 over the sorted list of `(path relative to the repository, st_mtime_ns,
     st_size)` for each file `board.result_files()` returns. It reads no file contents.
   - A file that vanishes between the listing and its `stat` is left out, not an error.
   - It needs the same token header as every other `/api/` path.
   - Rejected: polling `/api/state`, because `board.catalog()` runs `git log` per path
     (`build_eval_board.py:70-75`) on every call.
   - Rejected: a file watcher, which has no portable standard-library form.
   - Rejected: server-sent events, which hold a thread per open page.
3. **The page polls the signature every 5 seconds, only while it is visible.**
   - Gate the poll on `document.visibilityState === "visible"`, and check at once on the
     `visibilitychange` that makes the page visible.
   - Keep polling while a job runs, so each finished case of a multi-case run shows when it lands.
   - When the signature differs from the last one seen, fetch `/api/state`, call `setData`, and redraw.
   - The first signature comes with the page: the server puts it in the `SERVER` object it already
     embeds (`skill_manager.py:602`), so a result written between page load and the first poll is not
     missed.
   - A failed poll, from a lost connection or a stopped server, is silent and retried on the next tick.
     It never opens the Run view, unlike `alertRun`.
4. **A redraw keeps what the user has open:**
   - the view and the tab;
   - the search text and the filter;
   - the expanded skills;
   - the selected case in the side panel;
   - an open run form and the values chosen in it;
   - the Run view.

   While keyboard focus is in an `input`, `select` or `textarea` of the page, the redraw waits. It runs on
   the next tick after focus leaves.

   Rejected: `location.reload()`, which loses all of the above.
5. **Unchanged:**
   - the refresh when a page-started job ends, which also reloads the install state;
   - the static `eval-board.html` written by `build_eval_board.py`, which has no server (`SERVER` is
     `null`) and must not poll.
6. **Docs, and no plugin version.** This is contributor tooling under `tools/`.
   - `tools/skill_manager.py` docstring: one sentence saying the page picks up new results by itself.
   - `doc/running-evals.md`, section "The skill manager": the same.
   - In the troubleshooting row added by plan 19 for results from another machine, replace "then reload"
     with the fact that an open skill manager shows them within seconds. The static board still needs a
     rebuild.
   - `CHANGELOG.md` `[Unreleased]` `### Changed`: one bullet for contributors.

## Scope

In:

- `tools/skill_manager.py`: the `/api/results` route, the signature function, and the initial signature in
  the served page.
- `tools/build_eval_board.py`: the page script, for the poll, the visibility gate, the deferred redraw and
  keeping the open state.
- `tools/test_skill_manager.py` and `tools/test_eval_board.py`: the tests in Acceptance.
- `doc/running-evals.md`, `CHANGELOG.md`.

Out:

- **The scoring, the status rules and the layout of the board.**
- **`tools/copilot_eval.py` and how results are written.**
- **The static `eval-board.html`'s behavior.**
- **Install-state refresh outside the end of a job.** `/api/installed` runs `plugin list` commands, which
  are too costly to poll.
- **Any plugin, skill or version.**

## Baseline

| Existing | Keep, change, or remove |
| --- | --- |
| `build_eval_board.py:221` `result_files(repo)`: glob of `plugins/*/evals/results/*/aggregate-result.json` | Keep; the signature lists the same files |
| `build_eval_board.py:170-215` `load_results`: skips unreadable or non-result JSON with a message | Keep; a half-written file changes the signature again when its write finishes |
| `build_eval_board.py:557` `setData`, `:927-928` `renderEvals`/`renderAll`, `:549` `state` | Reuse for the redraw; keep `state` intact across it |
| `build_eval_board.py:755-843` `JOB`, `api()`, `poll()`; the refresh at `:838-842` | Keep; add the results poll beside it |
| `build_eval_board.py:1036` `if (SERVER) { poll(); … }` | Start the results poll here, inside the same `SERVER` guard |
| `skill_manager.py:462` `state()`, `:602` page render with `{"token": …}`, `:618-623` GET routes | Add the route and the initial signature |
| `test_skill_manager.py:34` `Server` fixture with `request()` | Reuse |
| `doc/running-evals.md` "The skill manager" and the plan 19 troubleshooting row | Update per Decision 6 |

## Tech stack and constraints

Default: Python 3.9+ standard library, and plain JavaScript in the page with no library and no network
request beyond the local server.

## Acceptance criteria

- [ ] **The endpoint needs the token.** `GET /api/results` without the header returns 403, and with it
      returns `signature` and `count`. Checked by a new test in `tools/test_skill_manager.py`.
- [ ] **The signature follows the files.** In a temporary repository: the signature is stable across two
      calls; it changes when a result folder is added; it changes when an existing
      `aggregate-result.json` is rewritten with a different size or mtime; and `count` matches. Checked by
      a new test, with `result_files` pointed at the temporary repository.
- [ ] **Failure case: a malformed result does not break anything.** A half-written
      `aggregate-result.json` (invalid JSON) changes the signature, `/api/results` and `/api/state` both
      still return 200, and the bad file is skipped as today. Checked by a new test.
- [ ] **The page carries the first signature, and only the server page polls.** The page served at `/`
      contains the current signature. The static board from `build_eval_board.board(...)` with no server
      still has `SERVER` as `null`. Checked by tests in `tools/test_skill_manager.py` and
      `tools/test_eval_board.py`.
- [ ] **In a browser, by the planner during review**, with the Chromium and Playwright in the session:
  - start the manager on a copy of the repository;
  - open a skill, select a case and type in the search;
  - copy a result folder into `plugins/<p>/evals/results/`;
  - within 10 seconds the case shows the new score, and the open skill, the selected case and the search
    are unchanged;
  - while focus is in the search box, no redraw happens until it leaves.
- [ ] **Required checks pass:** `python3 tools/validate.py`, `python3 tools/materialize.py --check`, and
      `for t in tools/test_*.py; do python3 "$t" || break; done`.

## Risks

| Risk | How it is handled |
| --- | --- |
| A redraw resets a run form the user is filling in | Decision 4: the open form and its values survive, and focus defers the redraw. The planner's browser check covers it |
| Polling costs the server work with many result folders | Decision 2: one glob and one `stat` per file, no reads; 5 seconds, visible pages only |
| A result being written is read half-way | `load_results` already skips bad JSON; the finished write changes mtime and size, so the next poll reloads it |
| The poll keeps a stopped server's page busy with errors | Decision 3: failures are silent and retried; nothing opens the Run view |
| Two refreshes race when a job ends and a result lands together | Both call the same `/api/state` and `setData`; the later one wins and both show the same data |

## Open questions

None.
