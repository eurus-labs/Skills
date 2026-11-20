# End-to-end evaluation of `document-codebase` (plan 17)

Plan: [`plan-17-docs-end-to-end-run.md`](plan-17-docs-end-to-end-run.md). This is the coder's record. Grading is
the planner's and is added later in a "Grading" section.

## Setup common to both runs

- **Repository state.** The branch `test/docs-end-to-end-run` was rebased onto `origin/main` at `49e213d`
  (plan 15 merged, `fix/docs-scope-empty-files`). `plugins/docs/.github/plugin/plugin.json` says `docs`
  **1.7.1**. Plan 16 (`feat/docs-migrate-legacy-build`) is not on `main`.
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
