# Plan 26 — keep eval results in the repository, with local paths scrubbed

Status: implemented
Date: 2026-11-27
Branch: `feat/tools-archive-eval-results`
Baseline: `origin/main` at `8056c02b64394b7ce80accc60ce1cd7496594a0f` (marketplace 0.6.0)
Target: a new `tools/archive_eval_results.py`, `tools/build_eval_board.py`, `tools/skill_manager.py`, their
tests, `.gitignore`, the docs, and 46 archived results

## Goal

`claude plugin eval` writes each run's `aggregate-result.json` and `report.html` to
`plugins/<plugin>/evals/results/<timestamp>/`. That folder is git-ignored, so the results stay on the machine
that ran them (`.gitignore:226`). The runs for plans 10 to 25 were made in a cloud container. Today they exist
only in a scratch bundle that disappears with the session. The user has received them as tarballs, and
`doc/eval-results.md` holds only the numbers.

The user wants them kept in the repository (2026-11-27). The raw files contain absolute paths of the machine
that ran them:

- `tracePath` values such as `/root/evaltmp/claude-eval-…/out/trace.jsonl`;
- workspace paths in replies and in `report.html`;
- on a contributor's own machine, `/home/<name>/…` or `/Users/<name>/…`.

No email, token or key was found in the current 46 files, but a future run could hold one.

When this is done:

- a contributor archives a run with one command;
- the archived files hold no absolute local path and no secret;
- the eval board and the skill manager show archived and local results together;
- the 46 results gathered so far are archived.

## Decisions

1. **Keep `aggregate-result.json` and `report.html`** (the user's choice, 2026-11-27). Transcripts (`*.jsonl`,
   `*.md`) are never archived.
   - For the current 46 runs this is about 1.8 MB plus 2.4 MB.
   - Rejected: the JSON only. The user wants the readable report as well.
2. **A separate, tracked folder: `plugins/<plugin>/evals/archive/<timestamp>/`.**
   - `results/` stays git-ignored, so a raw local run can never be committed by accident.
   - Only the tool writes into `archive/`.
   - Rejected: un-ignoring files inside `results/`. Every local run would then show up as untracked, and could
     be committed without scrubbing.
3. **`tools/archive_eval_results.py`** (the user's choice of a tool). It is stdlib-only Python 3.9 or later, makes
   no network call, and writes only under `plugins/*/evals/archive/`.
   - **Usage:** `python3 tools/archive_eval_results.py <source>…`, where a source is a
     `results/<timestamp>/` folder, an `aggregate-result.json`, or a folder holding `plugins/*/evals/results/*`
     (an unpacked bundle).
   - **Which plugin:** taken from the `plugins/<p>/evals/results/` path, else from `suite.plugins[0].name` in
     the JSON. A plugin missing from the marketplace is refused, and the reason is printed.
   - **Scrubbing.** Every absolute local path in both files is replaced with `<local>`, keeping the trailing
     relative part only where it lies inside the repository. The paths covered are:
     - `/root/…`, `/home/<x>/…`, `/Users/<x>/…`, `/tmp/…`, `/var/folders/…`;
     - Windows `C:\Users\<x>\…`;
     - the repository's own absolute path.

     `tracePath` becomes `null`, because the trace is not archived.
   - **Secrets.** A file that matches a secret pattern after scrubbing is refused and nothing is written. The
     patterns are:
     - `sk-ant-`;
     - `ghp_`, `gho_`, `github_pat_`;
     - `AKIA[0-9A-Z]{16}`;
     - `-----BEGIN … PRIVATE KEY-----`;
     - `Authorization: Bearer `, followed by a token;
     - the email address in `git config user.email`, when that is set.

     The tool names the file and the pattern, but never prints the match.
   - **Size.** A file over 5 MB is refused.
   - **Idempotent.** The same timestamp with the same content is skipped. The same timestamp with different
     content is refused unless `--replace` is given.
   - **`--check`** writes nothing. It verifies that every archived file has no absolute local path, no secret
     pattern, and no file over 5 MB, and exits 1 naming the offenders. The tests run it over the repository.
4. **The board and the skill manager read both folders.**
   - `build_eval_board.result_files()` globs `results/*/aggregate-result.json` and
     `archive/*/aggregate-result.json`.
   - `plugin_of` and `RESULTS_DIR` accept both folders.
   - A timestamp present in both folders is counted once, and the archived copy is used.
   - `skill_manager.results_signature()` covers both folders, so a newly archived run redraws an open page.
   - Transcript links stay `results/` only, and an archived run shows "transcript not archived".
5. **Archive the 46 results gathered so far.** They sit in the planner's scratch bundle, a folder holding
   `plugins/*/evals/results/*/`. The planner gives its path to the coder when it hands the plan over, and the
   path is never written into a committed file.
   - Run the tool on it and commit the archive in its own commit.
   - Results whose case later moved keep the plugin they ran under. For example, `analyze-requirements`
     results from plan 23 stay under `reasoning`. The board shows them as history.
6. **Docs.**
   - `doc/running-evals.md`, section "Recording a run": how to archive, and that only the tool writes
     `archive/`.
   - The troubleshooting row about results from another machine, updated: archive them, or copy them.
   - One bullet in `CONTRIBUTING.md` next to the eval board bullets.
   - `doc/eval-results.md`: one line at the top, saying that the raw files are under `plugins/*/evals/archive/`.
   - `CHANGELOG.md` `[Unreleased]` `### Changed`: one bullet for contributors.
   - No plugin version changes.

## Scope

In:

- `tools/archive_eval_results.py` and its test, `tools/test_archive_eval_results.py`.
- `tools/build_eval_board.py`, `tools/skill_manager.py`, and their tests.
- `.gitignore`. Keep `plugins/*/evals/results/` ignored; `archive/` is not ignored.
- `plugins/*/evals/archive/`, holding the 46 archived runs.
- `doc/running-evals.md`, `CONTRIBUTING.md`, `doc/eval-results.md`, `CHANGELOG.md`.

Out:

- **Transcripts.**
- **Running any eval.**
- **Changing how `claude plugin eval` writes results.**
- **Any plugin or skill.**

## Baseline

| Existing | Keep, change, or remove |
| --- | --- |
| `.gitignore:226` `plugins/*/evals/results/` | Keep |
| `build_eval_board.py:153` `RESULTS_DIR`, `:157` `plugin_of`, `:220` `result_files` | Extend to `archive/` |
| `skill_manager.py:455` `results_signature`, `:314` `transcript_path` | Extend the signature; transcripts unchanged |
| `tools/test_eval_board.py`, `tools/test_skill_manager.py` | Add cases for archived results |
| Scratch bundle (46 runs; 28 JSON files hold `/root`, `/home/user` or `/tmp` paths, and the reports hold `/tmp/claude-eval-…` paths) | Source for Decision 5 |

## Tech stack and constraints

Default: stdlib-only Python 3.9 or later. No new dependency.

## Acceptance criteria

- [ ] **Scrubbing works.** A test fixture result containing `/root/x`, `/home/alice/y`, `/Users/bob/z`,
      `C:\Users\carol\w`, `/tmp/claude-eval-1/home/cwd` and the repository path is archived with every path
      replaced, and `tracePath` set to null. Checked by `tools/test_archive_eval_results.py`.
- [ ] **Failure cases.**
  - A result containing `sk-ant-…`, or a `-----BEGIN PRIVATE KEY-----` block, is refused, nothing is written,
    and the output names the pattern but never the matched text.
  - A file over 5 MB is refused.
  - The same timestamp with different content is refused without `--replace`.
  - An unknown plugin is refused.

  Checked by tests.
- [ ] **`--check` guards the repository.** `python3 tools/archive_eval_results.py --check` exits 0 on the
      repository. A test plants an absolute path in a temporary archive and sees exit 1, with the file named.
- [ ] **The board and the manager see both folders.**
  - `build_eval_board.py` counts archived results.
  - A run in both folders is counted once.
  - `results_signature()` changes when a run is archived.

  Checked by tests.
- [ ] **The 46 runs are archived.**
  - `find plugins -path '*/evals/archive/*/aggregate-result.json' | wc -l` prints 46.
  - `--check` passes.
  - `grep -rEl '/root/|/home/[a-z]|/Users/|/tmp/' plugins/*/evals/archive` prints nothing.
  - On a clean checkout, `python3 tools/build_eval_board.py` reports 46 result files.
- [ ] **Required checks pass:** `python3 tools/validate.py`, `python3 tools/materialize.py --check`, and
      `for t in tools/test_*.py; do python3 "$t" || break; done`.

## Risks

| Risk | How it is handled |
| --- | --- |
| A secret or personal path is committed | Only the tool writes `archive/`; it scrubs paths, refuses secret patterns, and `--check` runs in the tests |
| The repository grows with every run | Archiving is a deliberate command, not automatic; the 5 MB cap per file; about 4 MB for the first 46 runs |
| Scrubbing breaks the JSON or the HTML | Replace inside string values (JSON) and text (HTML); the test re-parses the JSON and the board reads it |
| The same run is counted twice | Deduplicated by timestamp, with the archived copy used |

## Open questions

None.
