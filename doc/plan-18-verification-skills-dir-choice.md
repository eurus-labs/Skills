# Plan 18 — `setup-verification`: choose a skills directory the repository really has

Status: approved
Date: 2026-11-20
Branch: `fix/verification-skills-dir-choice`
Baseline: `origin/main` at `48371e031b17e39a9c27c2a7177ebea09f76c101`
Target: `plugins/verification/skills/setup-verification/SKILL.md`, the `verification` version, `CHANGELOG.md`

## Goal

`setup-verification` writes its `verify-<app>` skill into "the skills directory the repository already has
(`.github/skills/`, `.claude/skills/`, or `.agents/skills/`); if none exists, use `.github/skills/`"
(`SKILL.md:102`).

In a sandboxed Claude Code session, `.claude/` exists in the working directory even when the repository has
none. The sandbox creates it, and its protected entries, `.claude/skills` among them, are placeholder nodes
like `/dev/null` that refuse writes. This was checked with a sandboxed `claude -p` in an empty directory on
2026-11-20.

In the behavior evals that day, the skill took that placeholder for an existing skills directory in three of
six runs with the plugin. Its writes were then denied, and it stopped without writing anything
(`doc/eval-results.md`). Any user in a sandboxed session can hit the same thing.

When this is done, the skill counts only a skills directory the repository actually holds, so a placeholder
or an empty, uncommitted folder never wins over the `.github/skills/` default.

## Decisions

1. **"Already has" means git tracks a file under it** (the user's choice, 2026-11-20). A candidate directory
   counts only when `git ls-files -- <dir>` from the repository root prints at least one path.
   - The candidates are checked in the existing order: `.github/skills/`, `.claude/skills/`, `.agents/skills/`.
     The first that counts is used.
   - When none counts, use `.github/skills/` and say so, as today.
   - The sandbox placeholder and an empty folder nobody committed both print nothing, so neither counts.

   Rejected: "holds a real `SKILL.md`", because an existing skills folder holding only other files would not
   count. That is kept only as the fallback in Decision 2.
2. **Without git** (`git ls-files` fails because the directory is not a work tree), a candidate counts only when
   it is a real directory, neither a placeholder nor a symlink leaving the repository, and holds at least one
   regular file named `SKILL.md`. Otherwise use `.github/skills/` and say so.
3. **A chosen directory the session cannot write to** is reported, not worked around.
   - This can happen with a tracked `.claude/skills/` in a sandbox.
   - The skill says which directory it chose, why, and that writes there were refused.
   - It names `.github/skills/` as the alternative, and continues only on the user's answer.
   - If the user said they will not answer, it records this as the first open question and stops without
     writing.

   Rejected: silently falling back to `.github/skills/`, which would split the repository's skills across two
   directories without anyone choosing that.
4. **The rule is stated in `SKILL.md` where the directory is chosen**, under "Files written in the user's
   repository". Give the exact command, `git ls-files -- <dir>`, and one sentence on why: a directory can exist
   in a session without being part of the repository. Keep it under 8 lines. Nothing else in the skill
   changes.
5. **Version.** `verification` 0.3.1 → 0.3.2. Update both `plugin.json` copies and both `marketplace.json`
   entries, and add a `### Fixed` entry under `[Unreleased]` in `CHANGELOG.md`.

## Scope

In:

- `plugins/verification/skills/setup-verification/SKILL.md`, the paragraph at line 102.
- The `verification` version, the two marketplace files and `CHANGELOG.md`.

Out:

- **`verify-change`.** Its lookup at `SKILL.md:124` searches the same directories for an existing
  `verify-*` skill, and a placeholder holds none, so it is unaffected.
- **`read_feature_map.py` in `docs`.** It lists `verify-*` directories under the same candidates, and a
  placeholder lists none.
- **The eval cases and their graders.** The planner reruns them (Acceptance).
- **Any bundled script.** The skill has none, and this rule is a command the agent runs.

## Baseline

| Existing | Keep, change, or remove |
| --- | --- |
| `setup-verification/SKILL.md:102-103`: "Use the skills directory the repository already has (…); if none exists, use `.github/skills/` and say so." | Change per Decisions 1–4 |
| `setup-verification/SKILL.md:120`: `V=<skills-dir>/verify-<app>/scripts/verify` | Keep; `<skills-dir>` is the directory this rule chooses |
| `verification/evals/behavior/setup-verification-reports-codified-bug` and `setup-verification-runs-every-ci-check`: graders look under `.github/skills/verify-*` | Keep; rerun by the planner |
| `doc/eval-results.md`: 3 of 6 runs with the plugin chose the placeholder | Read; the planner adds the rerun result |

## Tech stack and constraints

Default. Instructions only; no script.

## Acceptance criteria

- [ ] **The rule is in the skill.** `SKILL.md` states Decisions 1–3, with the command `git ls-files --`. Checked
      by `grep -n "git ls-files" plugins/verification/skills/setup-verification/SKILL.md`, and by reading.
- [ ] **The skill stays within its size rules.** The paragraph is at most 8 lines, and `tools/validate.py`
      passes.
- [ ] **Version and changelog.** `verification` is 0.3.2 in all four files, and `[Unreleased]` has the `Fixed`
      entry. Checked by `python3 tools/validate.py`, which compares the copies, and by reading.
- [ ] **Failure case, by the planner during review.** Run the two `setup-verification` behavior cases on
      Claude Code:

      ```bash
      TMPDIR=<dir outside /tmp> claude plugin eval plugins/verification --tag behavior --case 'setup-verification-*' --no-publish --scaffold --allow-tools Bash Write Edit --trust-plugin -j 3 --model claude-sonnet-5-5 --judge-model haiku --max-cost-usd 8
      ```

      - No run with the plugin chooses `.claude/skills/`. Before this change, 3 of 6 did.
      - Each run either writes under `.github/skills/` or reports a different blocker.

      The planner records the result in `doc/eval-results.md` in the same pull request. A run still choosing
      the placeholder fails this criterion.
- [ ] **Required checks pass:** `python3 tools/validate.py`, `python3 tools/materialize.py --check`, and
      `for t in tools/test_*.py; do python3 "$t" || break; done`.

## Risks

| Risk | How it is handled |
| --- | --- |
| A repository keeps skills in an untracked folder on purpose | Rare, and it gets `.github/skills/` with the skill saying so (Decision 1). The user can move it |
| The agent skips the command and guesses from `ls` | The rule names the command and why a directory may exist without being the repository's. The eval rerun checks the behavior |
| A tracked `.claude/skills/` is unwritable in a sandbox | Reported, with `.github/skills/` offered, never silently (Decision 3) |
| The eval scores move for an unrelated reason | The rerun pins `--model` and `--judge-model`, as the earlier run did, and the planner reads the failing traces before judging |

## Open questions

None.
