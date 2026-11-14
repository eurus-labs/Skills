# Running the evals

This repository carries eval cases for its skills under `plugins/<plugin>/evals/`. An eval answers one
question: **does the skill make the agent do better than it does without the skill?** This page shows how to
run them on both hosts, read the result, and avoid the mistakes that made earlier runs meaningless.

| Host | Runner | Who grades | Use it for |
| ---- | ------ | ---------- | ---------- |
| Claude Code | `claude plugin eval` | the graders in each case, automatically | repeatable scores, before-and-after a change |
| GitHub Copilot CLI | `python3 tools/copilot_eval.py` | the script for file checks, you for the rest | what users of this marketplace actually get |

The two hosts read a skill's `description` differently, so a skill can fire on one and stay silent on the other.
Their scores are kept apart everywhere, never averaged. A score also depends on the model that produced it, so
pin the model whenever you compare runs; see [Claude Code](#choosing-the-model-claude-code) and [Copilot](#choosing-the-model-copilot).

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

   Useful flags: `--case <glob>` for one case, `--model <model>` to run every case on one model,
   `--judge-model <model>` for the model that grades `llm` graders (default `haiku`), `--json results.json`
   to write the full result, `-j <n>` to run up to 8 at once, `--keep-temp` to keep each run's workspace.
   Pin `--model` and `--judge-model` whenever you compare runs; see
   [Choosing the model](#choosing-the-model-claude-code). A plugin's README lists its own suite and the
   commands for it.

4. **Find the result.** It is written to `plugins/<plugin>/evals/results/<timestamp>/` as
   `aggregate-result.json` and `report.html`. That folder is git-ignored.

### Choosing the model (Claude Code)

By default each case runs on the model Claude Code would use for you. Two flags change that:

| Flag | Sets | Default |
| ---- | ---- | ------- |
| `--model <model>` | the model that does the task, for every case | Claude Code's default for your account |
| `--judge-model <model>` | the model that grades `llm` graders | `haiku` |

Pin **both** when you compare runs over time, or the score moves with the model and not with your change. Use
the same model on both arms (the runner does) and, to compare with Copilot, the same one as the Copilot run.
Names and aliases are the ones your Claude Code accepts, as in `/model`. They are spelled differently from
Copilot's: Claude Code writes `claude-sonnet-5-5` where Copilot writes `claude-sonnet-5.5`.

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

With `--run` the script first sends Copilot one trivial prompt with the flags you pinned, so a model your plan
does not offer, a reasoning effort the model lacks, or a missing sign-in fails **once, with Copilot's own
message**, and not once per case (`--no-check` skips this). Then it starts `copilot -p` for each arm in the
workspace, stops it at the case's `timeout_seconds`, and saves the transcript next to the result. You still
grade whatever the script cannot check.

If Copilot exits with an error, the last lines of its log are printed and the run is **not** put to you for
grading: a dead agent passes every "must stay quiet" grader. If the very first run fails, the suite stops and is
saved as partial, since nothing has worked yet.

**`--run` lets the agent run any command in a scratch directory as you, and is billed to your Copilot plan.**

### Choosing cases

```bash
python3 tools/copilot_eval.py plugins/verification --tag trigger --run          # trigger cases
python3 tools/copilot_eval.py plugins/verification --case "none-*" --run        # must-stay-quiet cases
python3 tools/copilot_eval.py plugins/verification --arms with --run            # skip the baseline arm
```

`--keep` keeps the scratch workspaces so you can look at what the agent did. To pin the model, see below.

### Choosing the model (Copilot)

Pass `--model <name>` (and, if you want, `--reasoning-effort <level>`). The script gives **both arms the same
flags**, prints them in the command it shows you when you run Copilot by hand, and writes them into the result,
where the eval board shows the model next to the host.

```bash
python3 tools/copilot_eval.py plugins/verification --case verify-change-follows-shared-code --run \
  --model claude-sonnet-5.5 --reasoning-effort medium
```

**Which names can I use?**

- In an interactive `copilot` session, run `/model`. It lists every model your plan and organization allow, and
  you can pick one from there. Use exactly that name with `--model`.
- `copilot help config` lists the model IDs this version of the CLI knows, for example `claude-sonnet-5.5`,
  `claude-haiku-5.5`, `claude-opus-5.5` and the `gpt-…` and `gemini-…` families. Your plan may offer fewer, and
  the list changes between CLI versions, so `/model` is the one to trust.
- `--reasoning-effort` accepts `none`, `minimal`, `low`, `medium`, `high`, `xhigh` or `max`, but the levels a
  model supports depend on the model. Unset means the model's own default, medium for most.
- Without `--model` Copilot uses your saved default (`/config model`, or the `COPILOT_MODEL` environment
  variable). `--model` overrides both.

**How to choose**

| Goal | Do this |
| ---- | ------- |
| Compare **with and without** the plugin | Nothing extra: the script uses one model for both arms. |
| Compare a run **before and after** a change | Pin the same `--model` and `--reasoning-effort` for both runs. A different model changes the score by itself. |
| Know what **your users** get | Use the model most of them have: usually the default of your plan. Run once with it, and once with a smaller one to see whether the skill only works on a strong model. |
| Compare **Copilot with Claude Code** | Use the same underlying model on both, for example `claude-sonnet-5.5` here and the same Sonnet through `claude plugin eval --model` there. A difference is then the host's doing (how it reads the skill) and not the model's. |
| Spend less on a first pass | Trigger cases (`--tag trigger`) need little reasoning; try them on a smaller model first. Behavior cases are where a weak model fails for its own reasons, so judge those on the model you care about. |

**Avoid `--model auto`.** Copilot then routes each request to a model of its choosing, so two runs of the same
case can use different models and the scores are not comparable.

Cost depends on the model and on your Copilot plan. A premium model uses more of your allowance per run; check
the plan details before running the whole behavior suite.

### How a run is graded

| Grader type | Who decides |
| ----------- | ----------- |
| `file_exists`, `regex` over a file | the script, in the workspace (honours `match: not_contains`, `count:N`, `flags`; `file_exists` counts only files created during the run) |
| `tool_used` | you, from the transcript, asked as a plain fact ("Did Copilot use the skill `verify-change`?"); the script works out whether that passes |
| `regex` over the reply | you, from the transcript |
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

## The skill manager

```bash
python3 tools/skill_manager.py        # opens the manager in your browser
```

One local page with three tabs, for people who develop the skills:

- **Skills**: one row per skill with its goal, its plugin's version, whether that plugin is installed in Copilot CLI
  and Claude Code (and whether the installed copy is older than this checkout), how many eval cases test it in each
  direction (must fire · must stay quiet · behavior; a dashed red zero is an untested direction), the latest result
  per host as "passing out of trusted", and a status: *no evals*, *not run*, *no trusted run*, *partly run*,
  *needs work*, *passing*, plus *changed since last run* when the skill was committed after its newest result.
  **Run all cases…** runs every case of that skill in turn.
- **Install**: each plugin's version in this checkout and in each host, with **Install**, **Update** and
  **Uninstall** per plugin or for all, and **Register** the marketplace from this checkout or from GitHub. Each
  action shows the exact command and runs only after you confirm.
- **Evals**: the eval board, with a **Run this case** form on every case: host, arms, model, reasoning effort
  (Copilot) and cost ceiling (Claude).

A run starts the same runner you would start from a terminal (`tools/copilot_eval.py --run` or
`claude plugin eval`), streams its output into a panel, and asks each grading question there with
**Yes / No / Skip** buttons and links to the run's transcripts. A Markdown transcript opens as a readable page:
roles, each tool call with its arguments and output folded, and timings; add `&raw=1` to the link for the file
itself. The page escapes everything the agent wrote and may run no script. When a job ends the page reloads.

- It listens on `127.0.0.1` only, accepts only `Host: 127.0.0.1` or `localhost`, and needs the random token in the
  URL it prints, so no other web page can drive it.
- It runs only the cases under `plugins/*/evals` and plugin commands it builds itself for plugins in the
  marketplace, with validated options, one job at a time, and serves only transcripts under
  `plugins/*/evals/results/`. It never runs a command the page sends.
- **Stop** takes effect at the next question or when the current command ends.
- An eval run costs what it costs from the terminal, and lets the agent run commands in a scratch workspace as
  you. Installing changes your Copilot or Claude Code configuration.
- It never passes `--trust-plugin`: if `claude plugin eval` refuses an untrusted directory, run it once in a
  terminal and answer the prompt.

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
| `copilot exited 1` right away, or the check prompt fails | Copilot refused to start. Read the lines printed under it. Usually the model is not on your plan (use a name from `/model`), the model has no such `--reasoning-effort` (leave it out), or you are signed out (`copilot login`). |
| `the scaffold of <case> failed` | The message names the bash used. Run that `bash` on `plugins/.../scaffold.sh` by hand in an empty directory to see the error. |
| Board shows `untrusted` | The run was partial, errored, or had a skipped grader. Rerun, or grade the skipped graders. |

## After you change a skill or a fixture

1. `python3 tools/validate.py` and every `tools/test_*.py` (`for t in tools/test_*.py; do python3 "$t" || break; done`).
2. After editing a fixture: `python3 tools/build_eval_scaffolds.py`, and update `fixtures/EXPECTED.md` in the same
   commit.
3. Rerun the suites above on `main`, then on your branch, and compare. Several changes in one run cannot be told
   apart.
