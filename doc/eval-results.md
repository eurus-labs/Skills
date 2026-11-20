# Eval results

A record of the `claude plugin eval` runs on `main`, so the next run has something to compare with. Each
section names its date, host, models and commit. A score depends on the model that produced it, so only
compare runs with the same `--model` and `--judge-model`. How to run the suites is in
[`running-evals.md`](running-evals.md).

Behavior cases run three times with the plugin and three times without it. **Δ** is the score with the plugin
minus the score without it. A pass needs every scored grader to pass in a run.

## 2026-11-19 and 2026-11-20 — `docs`, `testing`, `verification` and `presentation` on Claude Code

- **Host:** Claude Code 2.1.329, in a Linux cloud container, running as root.
- **Models:** `--model claude-sonnet-5-5 --judge-model haiku`.
- **Commit:** `main` at `642a431`, after plan 14. The plugin versions are those in the tables.
- **Not covered:**
  - GitHub Copilot CLI;
  - `review-code`, `setup-review-rules` and `evaluate-skill`, which have no eval cases.

### Trigger cases

These ran with `--tag trigger --ablation none --scaffold`. Each case ran three times.

| Plugin | Cases passed | Runs passed | Cost |
| --- | --- | --- | --- |
| `docs` 1.7.0 | 6 / 6 | 18 / 18 | $0.83 |
| `testing` 0.3.6 | 12 / 12 | 36 / 36 | $2.02 |
| `verification` 0.3.1 | 11 / 11 | 33 / 33 | $1.94 |
| `presentation` 0.1.1 | 9 / 9 | 27 / 27 | $1.31 |

The `reasoning`, `development` and `review` trigger cases ran on 2026-11-17 with Claude Code 2.1.326 and the
same `--model`:

- `reasoning`: 8 / 8.
- `review`: 3 / 3.
- `development`: 0 / 1 on `main`. Its prompt named a plan file the workspace did not have. It scored 3 of 3
  runs on the plan 10 branch, which put the plan in the prompt.

Every trigger case in the repository has now passed on Claude Code: 50 cases.

### Behavior cases

These ran with `--tag behavior --scaffold --allow-tools Bash Write Edit`, so both arms ran. `testing` was run
again after `pytest` was installed; the table shows that run.

| Plugin | Case | With plugin | Without | Δ |
| --- | --- | --- | --- | --- |
| `docs` 1.7.0 | `architecture-overview-of-layered-repo` (old design; see below) | 0 / 3 (0.33) | 0 / 3 (0.50) | −0.17 |
| `presentation` 0.1.1 | `workflow-slide-from-wordy-slide` | 3 / 3 (1.00) | 0 / 3 (0.50) | +0.50 |
| `testing` 0.3.6 | `debug-failing-test-blames-the-test` | 3 / 3 (1.00) | 3 / 3 (1.00) | 0 |
| | `review-tests-finds-weak-suite` | 3 / 3 (1.00) | 3 / 3 (1.00) | 0 |
| | `write-tests-reports-contract-bugs` | 3 / 3 (1.00) | 3 / 3 (1.00) | 0 |
| `verification` 0.3.1 | `setup-verification-reports-codified-bug` | 1 / 3 (0.75) | 0 / 3 (0.63) | +0.13 |
| | `setup-verification-runs-every-ci-check` | 2 / 3 (0.89) | 0 / 3 (0.67) | +0.22 |
| | `verify-change-catches-unwired-expiry` | 3 / 3 (1.00) | 0 / 3 (0.80) | +0.20 |
| | `verify-change-follows-shared-code` | 2 / 3 (0.93) | 3 / 3 (1.00) | −0.07 |
| | `verify-change-proves-pre-existing-failure` | 2 / 3 (0.92) | 0 / 3 (0.75) | +0.17 |
| | `verify-change-reports-blocked-required-check` | 3 / 3 (1.00) | 3 / 3 (1.00) | 0 |
| | `verify-change-runs-skipped-tests` | 3 / 3 (1.00) | 3 / 3 (1.00) | 0 |

The suites cost $0.43 (`docs`), $0.92 (`presentation`), $1.75 (`testing`) and $4.54 (`verification`).

### What the traces show

- **`docs`: the skill did not fire.** The prompt is "Write an architecture overview of this codebase:
  components, dependencies, entry points and the order flow." In all three runs with the plugin, Sonnet read
  the 75-line fixture and wrote the overview in its reply, in 3 turns. It never called `document-codebase`
  (`used-skill` failed), so `wrote-docs` (`docs/**`) failed. The judge passed the overview in two of the three
  runs. The skill's description
  sends "how does this fit together" questions to a chat answer, and this prompt does not ask for files. The
  trigger case "Document this repo. Write proper architecture documentation for it." fired 3 of 3.
  - **Rerun with a clearer prompt.** The prompt now asks for "architecture documentation for this codebase,
    as pages under docs/". The skill fired in 3 of 3 runs. Each run then stopped at checkpoint P1 after 4
    turns, recommended the `architecture` preset, and asked the user to confirm the scope and the preset. It
    scored 0 / 3 (0.00), against 0 / 3 (0.50) without the plugin, for $0.58.
  - **Why the case cannot pass as written.** The skill never answers P4 on the user's behalf (`SKILL.md`,
    rule 6). Pages reach `docs/` only at `publish`, after P4. So a one-message run with nobody to answer can
    never satisfy `wrote-docs` (`docs/**`). The case predates that rule and needs redesigning, not only
    rewording.
  - **Redesigned as an unattended run** (2026-11-20). The redesign is described in the next section.
- **`setup-verification`: the skill chose a directory it could not write.** In the three failing runs with the
  plugin, it found `.claude/skills/` in the workspace, although the repository has no such folder.
  - **Where the folder comes from:** Claude Code's sandbox creates it. Inside a sandboxed shell, `.claude/`
    exists in the working directory. Its protected entries, `.claude/skills` among them, are placeholder nodes
    like `/dev/null` that block writes. This was checked with a sandboxed `claude -p` in an empty directory, so
    it can happen in any sandboxed Claude Code session, not only in evals.
  - **What the skill did:** it took that folder as "the skills directory the repository already has"
    (`SKILL.md`, line 102). Writes there were denied, and it stopped without writing anything.
  - **The passing runs** wrote to `.github/skills/`, which is where the graders look.
  - **Rerun after plan 18** (2026-11-20, `verification` 0.3.2, Claude Code 2.1.329,
    `--model claude-sonnet-5-5 --judge-model haiku`, $2.15). The skill now counts a skills directory only when
    `git ls-files -- <dir>` prints a path.

    | Case | With plugin | Without | Δ |
    | --- | --- | --- | --- |
    | `setup-verification-reports-codified-bug` | 3 / 3 (1.00) | 0 / 3 (0.63) | +0.38 |
    | `setup-verification-runs-every-ci-check` | 3 / 3 (1.00) | 0 / 3 (0.67) | +0.33 |

    No run with the plugin chose `.claude/skills/`; all six wrote the skill under `.github/skills/`
    (`wrote-skill` passed). Before the change, 3 of 6 chose the placeholder.
- **`verify-change-proves-pre-existing-failure`:** the failing run asked for permission to check `main` in a
  worktree, although the prompt allows one. Its verdict was therefore `failed` instead of proving the failure
  pre-existing.
- **`verify-change-follows-shared-code`:** the failing run's last message reports what the grader asks for:
  - the invoice now prints `$9.00` and `TOTAL,,$12.50`;
  - `docs/invoice-csv.md` forbids a symbol;
  - the cause is the shared `format_amount` in `shop/money.py`.

  The Haiku judge still failed `invoice-checked` three times. This reads as a judge error, not a skill error.
  In the same run, the repository's own `verify doctor` crashed with a `PermissionError` on an unreadable
  dotfile placeholder from the sandbox, and the skill ran the checks directly instead.
- **`testing`: no measurable gain on this model.** Sonnet without the plugin also passes all three cases, so
  the suite cannot show what the skills add. A harder case or a smaller model would.

### The `docs` behavior case, redesigned

The case now tests an unattended run, the one way a one-message eval can exercise the whole pipeline.

- **Prompt:** it asks for architecture documentation under `docs/`, and adds "I won't be around to answer
  questions; make the choices you can make yourself, note them, and leave anything that needs my own answer
  for when I'm back."
- **Scored graders:**
  - `draft-flows` and `draft-architecture`: the judge reads the drafted `flows.rst` and `architecture.rst` in
    `.docs-build/rendered-docs/`, which the architecture preset always renders;
  - `not-published`: nothing may appear in `docs/`, because P4 waits for the user;
  - `handoff`: the reply names the choices the run made and what is left for the user.
- **Indicators:** `used-skill`, `architecture-preset`, `not-manual-preset` and `rendered-draft` are
  `with-only`. A `with-only` grader is reported but not scored.

| Run | With plugin | Without | Δ |
| --- | --- | --- | --- |
| Final graders, recomputed from the run below | 3 / 3 (1.00) | 0 / 3 (0.25) | +0.75 |
| As run, with an `overview` grader on the reply | 1 / 3 (0.87) | 0 / 3 (0.27) | +0.60 |

The run cost $1.78. Every run with the plugin used the `architecture` preset, rendered a draft and left
`docs/` empty. Without the plugin, Sonnet wrote pages straight to `docs/`. Its replies still passed `handoff`
in 3 of 3 runs, so that grader is lenient. The run's other point, `not-published`, is the one that catches
the difference.

**Lessons from the redesign**

- **`focus: files` hands the judge only the list of paths written, not their contents.** An earlier
  version judged the overview that way, so it was judging file names. The page graders name one file each
  with `focus: { source: file, path: … }`.
- **The Haiku judge failed a flows page that met the criteria.** It passed once the criteria said that
  references sit in `.. only:: audit` blocks and that functions appear as `cli.main`.
- **The `overview` grader on the reply was dropped.** It failed two runs whose drafted pages passed. Those
  replies were hand-off reports, and one grouped the code into four components rather than the three
  directories. The page graders already check the content.

**A product bug the redesigned case found:** the skill reported the quality gate as `partial`, with "4 of
10 modules unread". The reason is that `survey` puts every empty `__init__.py` in scope as an unread
`product` file. An empty file has no line to cite, so it can never be read, and any Python package stays
`partial` unless the user narrows the scope at P1.

### Environment problems found on the way

Each of these produced scores that measured the machine, not the skill. They were fixed before the runs
above. See "When something goes wrong" in [`running-evals.md`](running-evals.md).

- **No sandbox.** `bubblewrap` and `socat` were missing, so every behavior run was refused at once.
- **The temp directory was under `/tmp`.** The sandbox denies writes to `/tmp`, which made the case workspace
  read-only. Setting `TMPDIR` to a directory outside `/tmp` fixed it.
- **No `pytest`.** The sandbox has no network, so a run cannot install it. The `write-tests` skill would not
  write tests it could not run, and it failed 0 of 3, against 3 of 3 without the plugin. With `pytest`
  installed, it passed 3 of 3.
