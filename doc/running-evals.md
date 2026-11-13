# Running the evals

This repository carries eval cases for its skills under `plugins/<plugin>/evals/`. An eval answers one
question: **does the skill make the agent do better than it does without the skill?** This page shows how to
run them on both hosts, read the result, and avoid the mistakes that made earlier runs meaningless.

| Host | Runner | Who grades | Use it for |
| ---- | ------ | ---------- | ---------- |
| Claude Code | `claude plugin eval` | the graders in each case, automatically | repeatable scores, before-and-after a change |
| GitHub Copilot CLI | `python3 tools/copilot_eval.py` | the script for file checks, you for the rest | what users of this marketplace actually get |

The two hosts read a skill's `description` differently, so a skill can fire on one and stay silent on the other.
Their scores are kept apart everywhere, never averaged.

## Before you start

- Run from the repository root, on `main` or the branch you are testing.
- Commands use `python3`; on Windows type `python`.
- **Never open `fixtures/EXPECTED.md` or a case's `graders/` folder in the session being evaluated.** They are
  the answer key. The cases build their workspace from `scaffold.sh` in an empty directory so the agent under
  test cannot see them.
- Run **both arms**, with the plugin and without. A high score with the plugin proves nothing until you know
  what the same agent scores without it; the difference is the skill's value.
- Read the notes column before the score. A run that could not start can still "pass" a case whose grader asks
  for silence.

## Claude Code: `claude plugin eval`

Needs Claude Code 2.1.269 or later and a credential that a child process can use.

1. **Sign in for the runner.** Each run happens in an isolated temporary directory and cannot use your
   interactive `/login`. Export a credential in the same shell you run the command from, and never paste it
   into a chat or a file:

   ```powershell
   $env:ANTHROPIC_API_KEY = "<your key>"      # PowerShell
   ```

   ```bash
   export ANTHROPIC_API_KEY="<your key>"      # bash
   ```

   Runs are billed to that key.

2. **Probe with one case and a small ceiling.** The first run in a repository asks `Trust this plugin
   directory?`. Answering yes trusts the whole repository, including the fixtures that contain deliberately
   broken code. Do not pass `--trust-plugin` for a repository you have not read.

   ```bash
   claude plugin eval plugins/verification --tag trigger --runs 1 --ablation none --no-publish --max-cost-usd 1
   ```

   The first lines must read `Plugin under test: "verification" version "…"`. If they say
   `none resolved`, the plugin did not load and every score below measures Claude without it.

3. **Run the suites.** Trigger cases are cheap; behavior cases run the whole task twice per case.

   ```bash
   # Does each skill fire on the right requests and stay quiet on the wrong ones?
   claude plugin eval plugins/verification --tag trigger --ablation none --no-publish --max-cost-usd 3 --scaffold

   # Does it do the work well? Both arms, with the tools the tasks need.
   claude plugin eval plugins/verification --tag behavior --no-publish --max-cost-usd 30 \
     --scaffold --allow-tools Bash Write Edit
   ```

   Useful flags: `--case <glob>` for one case, `--json results.json` to write the full result, `-j <n>` to run
   up to 8 at once, `--keep-temp` to keep each run's workspace. A plugin's README lists its own suite and the
   commands for it.

4. **Find the result.** It is written to `plugins/<plugin>/evals/results/<timestamp>/` as
   `aggregate-result.json` and `report.html`. That folder is git-ignored.

### What a good run looks like

- No `invalid YAML frontmatter` lines, and `Plugin under test` names the plugin.
- No `error:` on any case, and no `partial` in the summary line (`stopped: authentication failed`,
  cost ceiling, interrupted). A partial run is incomplete; do not chart it.
- The `Δ` column (with minus without) is positive for the cases that should need the skill.

### Cleaning up

A run that fails keeps its temporary directory and prints a `Remove-Item` (or `rm -rf`) command for it. Run
that command, and do not run `git` or anything that reads configuration inside it: the agent may have written
there.

## GitHub Copilot CLI: `tools/copilot_eval.py`

Copilot CLI has no runner for the case format, so the script does what a runner would: it builds a fresh
workspace from the case's `scaffold.sh`, runs Copilot there once with the plugin and once without, and records
a pass or fail for each grader.

### Requirements

- GitHub Copilot CLI, signed in (`copilot login`).
- Python 3.9 or later.
- **bash.** On Windows install [Git for Windows](https://git-scm.com/download/win) and use its Git Bash. The
  `bash.exe` in `C:\Windows\System32` starts WSL and cannot run the scaffolds; the script skips it, and stops
  with a message when it finds no other bash.

### Run a case by hand

```bash
python3 tools/copilot_eval.py plugins/verification --case verify-change-follows-shared-code
```

For each arm the script builds the workspace, prints the `copilot` command to start there (with
`--plugin-dir` for the with-plugin arm only, none for the other), and prints the prompt to paste. Press Enter
when the agent finishes. The script checks what it can on files and asks you `passed? [y/n/s]` for the rest,
showing the lines of the transcript that match the grader's pattern as a hint.

### Let the script run Copilot

```bash
python3 tools/copilot_eval.py plugins/verification --case verify-change-follows-shared-code --run
```

With `--run` it starts `copilot -p` for each arm in the workspace, stops it at the case's `timeout_seconds`,
and saves the transcript next to the result. You still grade whatever the script cannot check.

**`--run` lets the agent run any command in a scratch directory as you, and is billed to your Copilot plan.**

### Choosing cases

```bash
python3 tools/copilot_eval.py plugins/verification --tag trigger --run          # trigger cases
python3 tools/copilot_eval.py plugins/verification --case "none-*" --run        # must-stay-quiet cases
python3 tools/copilot_eval.py plugins/verification --arms with --run            # skip the baseline arm
```

`--model <name>` picks the model; `--keep` keeps the scratch workspaces so you can look at what the agent did.

### How a run is graded

| Grader type | Who decides |
| ----------- | ----------- |
| `file_exists`, `regex` over a file | the script, in the workspace (honours `match: not_contains`, `count:N`, `flags`; `file_exists` counts only files created during the run) |
| `tool_used`, `regex` over the reply | you, from the transcript |
| `llm` | you, from the rubric in the grader file |

- Grade **before** you open `fixtures/EXPECTED.md`.
- `tool_used: Skill` only shows whether the plugin fired; it is not part of the score.
- The score is the weighted share of graded graders that passed.
- Pressing `s` to skip a scored grader is recorded and marks the run as not fully graded. The board never
  counts such a run as a trusted score.

The result is written to `plugins/<plugin>/evals/results/copilot-<time>/aggregate-result.json` with
`"host": "copilot"`.

### Not yet verified on a real run

- Whether Copilot stops to ask to trust the scratch folder when started with `-p`.
- The shape of the JSONL transcript. Until a real file is checked against it, the script uses transcripts only
  as hints and does not grade `tool_used` graders itself.
- Whether Copilot reports which skill it used. If it does not, judge from the reply: a table of checks, one
  verdict and a JSON block mean `verify-change` ran.

## See every skill's results

```bash
python3 tools/build_eval_board.py        # writes eval-board.html, which is git-ignored
```

The board has one card per skill, with the number of cases that must fire it, must keep it quiet, and grade its
behavior, and one badge per host for each case's latest run. A zero marks a direction nobody tests. A score
counts as trusted only when the suite finished, no run of the case errored, and no judge grader was skipped;
otherwise the board shows it as untrusted, with the last trusted score beside it. The page switches between
English and Vietnamese. Add result files from elsewhere with `--results [plugin=]<file>`.

## When something goes wrong

| What you see | Cause and fix |
| ------------ | ------------- |
| `invalid YAML frontmatter` on a case | A description with `: ` or ` #` must be quoted. `tools/test_eval_frontmatter.py` catches this; run the tests. |
| `Plugin under test: none resolved` | `claude plugin eval` reads `plugin.json` or `.claude-plugin/plugin.json`. Every plugin needs both copies, identical; `tools/validate.py` checks. |
| `Not logged in · Please run /login` | Export `ANTHROPIC_API_KEY` in the same shell and run again. |
| A case scores `1.00` and has an `error:` | The run never started. A grader that asks for silence passes on a dead agent. Fix the error; do not read the score. |
| `no usable bash found` (Copilot script, Windows) | Install Git for Windows. |
| `the scaffold of <case> failed` | The message names the bash used. Run that `bash` on `plugins/.../scaffold.sh` by hand in an empty directory to see the error. |
| Board shows `untrusted` | The run was partial, errored, or had a skipped grader. Rerun, or grade the skipped graders. |

## After you change a skill or a fixture

1. `python3 tools/validate.py` and every `tools/test_*.py` (`for t in tools/test_*.py; do python3 "$t" || break; done`).
2. After editing a fixture: `python3 tools/build_eval_scaffolds.py`, and update `fixtures/EXPECTED.md` in the same
   commit.
3. Rerun the suites above on `main`, then on your branch, and compare. Several changes in one run cannot be told
   apart.
