# Plan 10 — skill manager: Skills tab, Enable, Uninstall all, and stale plugins

Status: draft
Date: 2026-11-17
Branch: `feat/tools-skill-manager-plugin-actions`
Baseline: `origin/main` at `e679abc4fe12215a6eee3cb71898946f65bfeedf`
Target: `tools/skill_manager.py`, `tools/build_eval_board.py`, their tests; one eval prompt in
`plugins/development/evals/trigger/implement-approved-plan/`

## Goal

The user found four problems on the skill manager's Install tab while using Copilot CLI:

- **Disabled plugins look installed.** `reasoning` and `review` show `0.x · disabled` with only Update
  and Uninstall, so there is no way to turn them on.
- **There is no Uninstall all**, although Install all and Update all exist.
- **A renamed plugin stays installed.** `code-review` is now `review`, but the old `code-review` is still in
  the user's Copilot. The page lists only plugins in this checkout's marketplace, so the old one is invisible
  and cannot be removed from the page.
- **The tab name.** The user wants the tab called "Skills" instead of "Install".

Separately, the trigger eval `implement-approved-plan` failed 5 of 6 runs on 2026-11-17. The traces show why:
its prompt names `doc/plan-1-add-logging.md`, which does not exist in the eval workspace. Each time, the
agent searched for the file, did not find it, and asked the user where it was, before any skill could fire.
The case tests a missing file rather than the skill.

When this is done, the user can see and fix every one of this marketplace's plugins on each host from the
page, and the `implement` trigger case measures the skill.

## Decisions

1. **Rename the tab label only.** The tab reads "Skills" in both languages (`tabInstall` in `en` and `vi`),
   and the back link reads "← Back to skills" / "← Về Skills". The internal view id stays `install`
   (`data-tab`, `data-view`, `state.back`, the saved `localStorage` value), so a saved tab still opens and
   the tests that list view ids keep working. Rejected: renaming the id to `skills`, because an older
   page already saved `"skills"` for a tab that was folded into Evals (`build_eval_board.py:1022`), and
   reusing it would reopen that confusion.
2. **A disabled plugin gets Enable in the first slot**, in place of Update; Uninstall stays in the second
   slot. Enable runs:
   - Copilot: `copilot plugin enable <name>`, by name, as GitHub's plugin reference gives it;
   - Claude Code: `claude plugin enable <name>@eurus-labs`, as `claude plugin --help` gives it.

   `plugin_command` builds both; `run_install` accepts `enable` only for a plugin that the host lists from
   this marketplace. Rejected: showing Update for a disabled plugin, because updating it leaves it off.
3. **A missing `enabled` field does not mean disabled.** `installed()` records `enabled: False` only when the
   listing says `false` explicitly. A missing field is read as enabled. Rejected: keeping
   `bool(item.get("enabled"))`, because it turns a missing field into "disabled". That may be part of what
   the user sees, but nobody has checked their real listing yet (see Risks).
4. **Uninstall all**, as a third header button after Install all and Update all. It uninstalls only the
   plugins this host has installed from this marketplace, including the stale ones of Decision 5, and is
   disabled when there are none. Like every action, it shows its commands and runs only after Confirm.
   Rejected: sending every catalog name, because uninstalling a plugin that is not installed fails the job
   at its first step.
5. **Stale plugins get their own rows.** A plugin the host lists from marketplace `eurus-labs` that is not in
   this checkout's catalog (for example `code-review`) is shown below the catalog rows with:
   - its installed version;
   - a note, "no longer in this marketplace" / "không còn trong marketplace";
   - an empty first slot and an Uninstall button in the second.

   `run_install` accepts `uninstall` for such a name only when `installed()` for that host lists it under
   `eurus-labs`, and only if it matches `^[a-z0-9][a-z0-9-]*$`. Every other action still requires a catalog
   name. Rejected: a free-text "uninstall any plugin" field, because the page must never run a command the
   page supplies (module docstring).
6. **Fix the eval by putting the plan in the prompt.** `implement-approved-plan/prompt.md` keeps its
   frontmatter (`max_turns: 6`, `allowed_tools: [Read, Glob, Grep, Skill]`, tag `trigger`). Its request
   becomes an approved plan given inline: a short plan with `Status: approved`, a goal, and two acceptance
   criteria, followed by "Implement this plan." It no longer names a file. Rejected: adding a `scaffold.sh`
   that writes the plan file, because trigger cases run without `--scaffold` (`doc/running-evals.md`), so
   the file would still be missing.

## Scope

In:

- `tools/build_eval_board.py`: the labels of Decision 1; the Enable slot (2); Uninstall all (4); stale rows
  (5); the strings for each, in `en` and `vi`.
- `tools/skill_manager.py`: `plugin_command` for `enable`; `run_install` checks (2, 5); `installed()` (3);
  the module docstring's description of the tab.
- `tools/test_skill_manager.py` and `tools/test_eval_board.py`: tests for each decision, including refusals.
- `plugins/development/evals/trigger/implement-approved-plan/prompt.md` (Decision 6).
- `doc/running-evals.md:251` and `doc/skill-manager-redesign.md:87`, where they name "the Install tab".

Out:

- Installing a single skill. Hosts install whole plugins; the user confirmed they meant per-plugin buttons,
  which already exist for plugins that are not installed.
- A Disable button. Nobody asked for it.
- Any other eval case, and any plugin or skill version. The eval prompt is not shipped skill content, so no
  plugin version bump.
- Released `CHANGELOG.md` sections. Released sections already record contributor tools (for example the
  skill manager in 0.3.0), so add one `### Changed` bullet under `[Unreleased]` for the skill manager, and
  touch nothing else in the file.

## Baseline

| Existing | Keep, change, or remove |
| --- | --- |
| `tools/skill_manager.py:238` `plugin_command` (install, update, uninstall, marketplace-add, marketplace-update) | Change: add `enable` per Decision 2 |
| `tools/skill_manager.py:277` `installed()`, `enabled: bool(item.get("enabled"))` | Change per Decision 3; the shape of `entry["plugins"]` stays `{name: {version, enabled}}` |
| `tools/skill_manager.py:519` `run_install`, which accepts only catalog names | Change per Decisions 2 and 5 |
| `tools/build_eval_board.py:851-916` `installTab()`: fixed slots, Install all and Update all in the header | Change per Decisions 2, 4 and 5; keep the fixed-slot layout |
| `tools/build_eval_board.py:494, 532` `tabInstall` ("Install", "Cài đặt"); `backInstall` | Change the strings per Decision 1 |
| `tools/build_eval_board.py:1022-1023`: a saved `"install"` reopens the tab | Keep |
| `tools/test_eval_board.py:173-174`: view ids are `evals`, `install`, `run` | Keep passing unchanged |
| `tools/test_skill_manager.py:430-500`: command, refusal, job and listing tests | Keep; add cases |
| `plugins/development/evals/trigger/implement-approved-plan/prompt.md` | Change the request per Decision 6 |

## Tech stack and constraints

Default: stdlib-only Python 3.9+, and the page stays one self-contained HTML string with no new dependency.

## Acceptance criteria

- [ ] The tab and back link read "Skills" in both languages, and the view id is still `install`. Checked by
      a test on the built page, and by `python3 tools/test_eval_board.py`.
- [ ] `plugin_command("copilot", "enable", "review")[1:]` is `["plugin", "enable", "review"]`, and
      `plugin_command("claude", "enable", "review")[1:]` is `["plugin", "enable", "review@eurus-labs"]`.
      Checked by `python3 tools/test_skill_manager.py`.
- [ ] A listing row with no `enabled` field is recorded as enabled, and one with `"enabled": false` as
      disabled. Checked by a test of `installed()`.
- [ ] Failure cases, each refused with HTTP 400:
      - `enable` or `uninstall` for a name the host does not list;
      - `install` or `update` for a stale name;
      - a stale name that fails the name pattern (for example `a;rm -rf ~`).

      Checked by `python3 tools/test_skill_manager.py`, with `installed()` patched.
- [ ] `uninstall` for a stale name the host lists from `eurus-labs` (`code-review`) runs
      `copilot plugin uninstall code-review@eurus-labs`. Checked by a job test with a fake process.
- [ ] Rendered with a fake listing (one catalog plugin disabled, one stale plugin), the page shows:
      - Enable and Uninstall for the disabled one;
      - a stale row with Uninstall only;
      - an Uninstall all button whose plugin list is exactly the installed plugins.

      Checked by a test that runs the page script, or by checking `installTab()`'s output the way the
      existing page tests do. If neither is possible, say which parts were checked by reading.
- [ ] `implement-approved-plan/prompt.md` names no file path and contains `Status: approved`. Checked by
      `grep -n "doc/\|\.md" plugins/development/evals/trigger/implement-approved-plan/prompt.md` printing
      nothing, and by reading.
- [ ] The repository's required checks pass: `python3 tools/validate.py`,
      `python3 tools/materialize.py --check`, and
      `for t in tools/test_*.py; do python3 "$t" || break; done`.

## Risks

| Risk | How it is handled |
| --- | --- |
| The Copilot `enable` syntax (by name, not `name@marketplace`) comes from GitHub's docs as quoted by a search; docs.github.com was blocked in this session | Before merge, the user clicks Enable on `reasoning` on their machine. If Copilot refuses the bare name, the fix is the one-line `plugin_command` branch |
| The user's "disabled" rows have another cause, not a missing field | Decision 2 gives them a working Enable either way. The planner asks the user for their `copilot plugin list --json` rows for `reasoning` and `review` and records the cause in the PR |
| Stale-plugin uninstall becomes a way to run arbitrary names | Allowed only for names `installed()` returns for `eurus-labs` on that host, only for `uninstall`, and only matching the name pattern; covered by the refusal tests |
| The new eval prompt still does not fire `implement` | The planner reruns the case (`claude plugin eval plugins/development --tag trigger --ablation none --no-publish --max-cost-usd 1`) during review and reports the score in the PR. A low score is reported, not hidden |

## Open questions

None.
