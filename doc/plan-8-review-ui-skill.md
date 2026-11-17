# Plan 8 — add a `review-ui` skill and rename `code-review` to `review`

Status: approved
Date: 2026-11-17
Branch: `feat/review-ui-skill`
Baseline: `origin/main` at `c2bafbccbf83ca63d08d87bade5c5d82f4ceb04c`
Target: `plugins/code-review` (renamed `plugins/review`), new skill `review-ui`; references to the plugin name elsewhere

## Goal

The repository reviews code (`review-code`) and tests (`review-tests`), but not the interface a change
produces. Add `review-ui`. It judges rendered screens, the DOM and the styles behind them, and the same
screens on the base revision, for:

- accessibility against WCAG 2.1 AA;
- consistency with the existing interface;
- clarity of wording and states;
- unintended visual change.

Findings are ranked by severity. Once the plugin holds both code and UI review, `code-review` no longer
describes it, so rename the plugin to `review`.

The user wrote the skill (Appendix A), drawing on the `design:accessibility-review` (WCAG 2.1 AA) and
`design:design-critique` skills of Claude's `design` plugin.

## Decisions

1. **The plugin `code-review` becomes `review`** (decided by the user).
   - Rename the folder to `plugins/review/` with `git mv`, so history follows.
   - Set `name: review` in both `plugin.json` copies and both `marketplace.json` entries.
   - Rewrite `plugins/review/README.md` for the new name and both kinds of review.
   - The install name changes from `code-review@eurus-labs` to `review@eurus-labs`, so this is a breaking
     change. Rejected: keeping `code-review`, because the user chose the broader name.
2. **`review-ui` lives in `review`**, next to `review-code` (decided by the user).
3. **Its content is the user's draft in Appendix A**, with only these edits:
   - Add a `## Bundled resources` section saying "None. Everything this skill requires is in this file.",
     matching the template.
   - Step 3 adds: "If the harness starts a server or app, stop it when the capture is done."
   - "use review-tests" becomes "use `review-tests` from the `testing` plugin". The description already names
     `review-code` without a plugin, which is correct because they now share one.
   - The WCAG checklist and the contrast formula stay in `SKILL.md` (decided by the user), not in
     `references/`.
   Rejected: rewording the rules, because they are the user's and already meet the repository's skill rules.
4. **`review-code` defers UI review to `review-ui`.** Add one "When not to use" bullet: "The rendered
   interface, accessibility, or visual change is the subject — use `review-ui`." Name `review-ui` in its
   description's "instead" list. This changes when `review-code` defers, so the root catalog row changes in
   the same commit.
5. **Every other reference to the plugin name follows the rename.** "`review-code` from the `code-review`
   plugin" becomes "`review-code` from the `review` plugin" in these files:
   - `plugins/development/skills/implement/SKILL.md` (2)
   - `plugins/development/README.md` (2)
   - `plugins/reasoning/skills/design-solution/SKILL.md`
   - `plugins/skill-authoring/skills/evaluate-skill/SKILL.md`
   - `plugins/testing/skills/review-tests/SKILL.md`
   - `plugins/verification/skills/setup-verification/SKILL.md`
   - `plugins/verification/skills/verify-change/SKILL.md`
   - `plugins/verification/README.md`
   - the root `README.md`
   - `tools/test_eval_board.py`: point the "plugins without evals" test at `skill-authoring`, which has no
     evals, because `review` gains evals in Decision 8 (amended by the user after review)

   Leave these unchanged as history: `CHANGELOG.md`'s released sections, `doc/skill-manager-redesign.md`, and
   `fixtures/04-security/app.py`, whose wording is generic and which is a planted fixture.
6. **Versions:**
   - `review` `0.2.4` → `0.3.0`: a new skill plus the rename, continuing `code-review`'s numbering.
   - Every other plugin whose shipped text changes gets a patch bump, so installed copies receive it:
     `development` 0.5.1 → 0.5.2, `reasoning` 0.2.1 → 0.2.2, `skill-authoring` +patch, `testing` +patch,
     `verification` +patch.
   - The marketplace `metadata.version` stays 0.3.0. The change goes under `CHANGELOG.md` `[Unreleased]`,
     with a **Breaking changes** entry giving the reinstall command.
7. **Shared files keep working.** `plugins/review/shared.manifest` moves with the folder unchanged. Run
   `python3 tools/materialize.py --check` after the move, and `python3 tools/materialize.py` if it reports
   drift.
8. **Trigger eval cases** go under `plugins/review/evals/trigger/`, modeled on
   `plugins/docs/evals/trigger/<case>/prompt.md` plus `graders/`:
   - `review-ui-a11y-check` ("Is this new settings dialog accessible? Check contrast and keyboard use.") must
     fire `review-ui`;
   - `review-ui-compare-screenshots` ("Compare the before and after screenshots of the checkout page in this
     PR.") must fire `review-ui`;
   - `review-ui-quiet-code-review` ("Review this function for bugs and security issues.") must not fire
     `review-ui`.

## Scope

In:

- `git mv plugins/code-review plugins/review`, and everything in Decisions 1–8.
- `plugins/review/skills/review-ui/SKILL.md` and three trigger cases.

Out:

- Behavior evals, and any screenshot tool or script.
- Changes to `review-code`'s method beyond the one deferral bullet and its description.
- Released `CHANGELOG.md` sections, historical docs, and fixtures.

## Baseline

| Existing (at `c2bafbc`) | Keep, change, or remove |
| --- | --- |
| `plugins/code-review/` with `review-code`, `setup-review-rules`, and `shared.manifest` | Rename to `plugins/review/`; add `review-ui` |
| `plugins/code-review/.github/plugin/plugin.json` and `.claude-plugin/plugin.json` (`name: code-review`, 0.2.4) | `name: review`, 0.3.0, `skills` adds `./skills/review-ui/`, new description |
| Both `marketplace.json` entries for `code-review` | Rename, and match the new version and description |
| `README.md` catalog row for `code-review` | Rename; list `review-ui` |
| `tools/test_eval_board.py:81-82` uses `self.plugins["code-review"]` | Point the "plugins without evals" test at `skill-authoring`, which has no evals, because `review` gains evals in Decision 8 (amended by the user after review) |
| 9 skill and README files naming "the `code-review` plugin" (Decision 5) | Name the `review` plugin |

## Tech stack and constraints

Default per `AGENTS.md`: Markdown skills, no new dependencies, and no network or installs in the skill.
Keep `SKILL.md` under ~500 lines.

## Acceptance criteria

- [ ] `plugins/code-review/` no longer exists. `plugins/review/` holds `review-code`, `setup-review-rules` and
      `review-ui`, and all three are listed in both `plugin.json` copies. Checked by
      `python3 tools/validate.py`.
- [ ] `review` is `0.3.0`, and each bumped plugin's version matches across both `plugin.json` copies and both
      `marketplace.json` copies. Checked by `python3 tools/validate.py`.
- [ ] No reference to the old plugin name remains outside history. Checked by
      `grep -rn 'code-review' --exclude-dir=.git . | grep -v -e '^./CHANGELOG.md' -e '^./doc/skill-manager-redesign.md' -e '^./fixtures/'`
      printing nothing except the new `[Unreleased]` Breaking changes entry, which names the old install name
      on purpose.
- [ ] `review-ui/SKILL.md` matches Appendix A apart from the edits in Decision 3. Checked by diffing the two.
- [ ] `review-code` names `review-ui` in its description and in "When not to use". Checked by
      `grep -n review-ui plugins/review/skills/review-code/SKILL.md`.
- [ ] Shared files are in sync. Checked by `python3 tools/materialize.py --check`.
- [ ] Failure case: the quiet trigger case exists with `min: 0` and `max: 0`. Whether the cases were run is
      reported, not claimed.
- [ ] `CHANGELOG.md` `[Unreleased]` has a Breaking changes entry with `review@eurus-labs`, and an Added entry
      for `review-ui`.
- [ ] `python3 tools/validate.py` passes, and `for t in tools/test_*.py; do python3 "$t" || break; done` passes.
- [ ] Every commit has the expected identity on both sides. Checked before each push by
      `git log origin/main..HEAD --format='%an <%ae> | %cn <%ce>' | sort -u`.

## Risks

| Risk | How it is handled |
| --- | --- |
| Users with `code-review@eurus-labs` installed lose it silently | Breaking changes entry, and the plugin README gives the reinstall command |
| A tool or test hardcodes `code-review` | Decision 5's grep covers `tools/`; the full test loop runs |
| `review-ui` and `review-code` fire on each other's requests | Decision 4's deferral, plus a quiet trigger case |
| `materialize.py` loses track of the moved plugin | Decision 7's `--check` |
| The skill text reproduces another plugin's wording | The user confirmed the wording is their own; the README credits the inspiration |

## Open questions

None. Answered by the user before approval:

- The rename applies to the **plugin** (`code-review` → `review`); the new skill is named `review-ui`.
- The draft's wording is the user's own. It draws ideas from Claude's `design:accessibility-review` and
  `design:design-critique` skills without copying their text. `plugins/review/README.md` credits the two
  skills as inspiration in one line.

## Appendix A — `review-ui/SKILL.md` as written by the user

````markdown
---
name: review-ui
description: Review the user interface a change produces — rendered screenshots, the page's HTML and styles, before and after — for accessibility against WCAG 2.1 level AA, consistency with the existing interface, clarity of wording and states, and unintended visual change, with each finding ranked by severity and naming the screen, the element, the criterion and who is blocked. Use whenever the user says "review the UI", "check the screens", "is this accessible", "a11y check", "check contrast", "does this look right", "compare the screenshots", asks to look over a new dialog, panel, page or webview before merging, or a pull request changes HTML, CSS, templates or webview scripts. To review the code itself use review-code instead; to review a test suite use review-tests.
---

# Review UI

## Overview

Judge what a person will see and operate, from evidence: rendered screenshots, the DOM and the styles behind
them, and the same screens before the change. The deliverable is one report: a severity-ordered findings
table, the evidence it rests on, what could not be checked, and a verdict.

A finding needs a screen, an element, a criterion, and who is blocked or misled. An impression without those
is not a finding.

## Hard rules

- **Evidence only.** Every finding cites a screenshot file or a DOM/CSS location. Never infer a rendered
  result you did not render.
- **Never claim conformance.** Write "checked against WCAG 2.1 AA: no failures found in the listed screens",
  never "accessible" or "WCAG compliant". A screenshot cannot show screen reader output, motion, or every
  state.
- **Measure contrast; never eyeball it.** Take both colors from the computed style or the CSS, compute the
  ratio with the formula below, and write the ratio in the finding.
- **Report; do not fix.** This skill edits no file. Suggest a direction, not a redesign.
- **An unexplained visual difference from the base is a finding**, even when it looks better: the change did
  not say it would happen.
- **Name what was not checked** (themes, widths, states, assistive technology) in its own section.

## When to use this skill

- A change adds or alters a page, dialog, panel, menu, webview, or its styles or wording.
- "Review the UI" / "is this accessible?" / "check contrast" / "compare these screenshots".
- A planner reviews a coder's branch that touched templates, CSS or front-end scripts.

## When not to use this skill

- **The code is the subject** (logic, security, maintainability) — use `review-code`.
- **Tests are the subject** — use `review-tests` from the `testing` plugin.
- **The user wants the UI built or fixed** — use `implement` from the `development` plugin, or do it directly.
- **A formal audit or legal certification** is needed — say that it needs a person testing with assistive
  technology; this review can prepare it, not replace it.
- **No rendered output can be produced or provided** — say so, review the HTML and CSS only, and mark every
  finding as static.

## Steps

1. **Establish scope.** List the screens and states the change affects: from the diff (templates, styles,
   scripts), the PR description, and the UI tests that touch them. State the scope in the report.
2. **Read the repository's UI rules.** `AGENTS.md`, `CONTRIBUTING.md`, a design system or token file, and any
   instruction file scoped to the changed paths. A stated rule a screen breaks is a finding that cites it.
3. **Collect evidence.** Use the repository's own screenshot or UI test harness (find it from `AGENTS.md`,
   `package.json` scripts, or the test folder); do not install a new tool. For each affected screen capture:
   - the changed state, and the empty, loading and error states the change can show;
   - every theme the product supports (for example light and dark) and the narrowest width it supports;
   - the same screens on the base revision, captured the same way.
   Read the DOM of each screen (accessible names, roles, ARIA state, tab order) from the page or the template.
4. **Review in passes**, in this order:
   1. **Regression** — compare each screen with its base capture. Ignore known noise (timestamps, anti-aliasing
      in a few pixels) only when the same difference appears between two base captures; say which.
   2. **Accessibility** — the checklist below.
   3. **Consistency** — the same job uses the same control, wording, spacing and placement as elsewhere in the
      product; a new pattern needs a reason.
   4. **Clarity** — labels say what will happen; errors say what went wrong and what to do; destructive
      actions say what is lost; empty and loading states exist and say something useful.
5. **Rate each finding** with the ladder below, then **report** in the output format.

## Accessibility checklist (WCAG 2.1 AA, in brief)

Cite the success criterion number in each finding.

| Check | Passes when | SC |
| ----- | ----------- | -- |
| Text contrast | ratio ≥ 4.5:1; ≥ 3:1 for text ≥ 24 px, or ≥ 18.66 px bold | 1.4.3 |
| Control and focus contrast | borders, icons, focus rings and state cues ≥ 3:1 against what is next to them | 1.4.11 |
| Color is not the only cue | state, errors and selection also differ in text, icon or shape | 1.4.1 |
| Keyboard | every action works by keyboard; no trap; Escape closes what it opened | 2.1.1, 2.1.2 |
| Focus order and visibility | order follows the layout; the focused element is always visible | 2.4.3, 2.4.7 |
| Names and roles | every control has an accessible name that matches its visible label; icon-only buttons have one | 4.1.2, 2.5.3 |
| State | toggles, menus, tabs and checkboxes expose their state (`aria-pressed`, `aria-expanded`, `aria-checked`, `aria-selected`) | 4.1.2 |
| Labels | every input has a label; instructions are not only placeholders | 3.3.2, 1.3.1 |
| Errors | an error names the field and says how to fix it | 3.3.1, 3.3.3 |
| Status messages | progress and results that appear without focus moving are announced (`role="status"`, `aria-live`) | 4.1.3 |
| Reflow and zoom | at the narrowest supported width, or 200% zoom, nothing is cut off or overlaps | 1.4.4, 1.4.10 |
| Headings and structure | headings and landmarks reflect the layout | 1.3.1, 2.4.6 |

Contrast ratio = (L1 + 0.05) / (L2 + 0.05), with L1 the lighter color's relative luminance. Relative luminance
= 0.2126 R + 0.7152 G + 0.0722 B, each channel c (0–1) linearized as c / 12.92 when c ≤ 0.04045, else
((c + 0.055) / 1.055) ^ 2.4. For a semi-transparent color, blend it over its background first.

Target size of 24 × 24 px is WCAG 2.2 (2.5.8), not 2.1: report it as Consider, not Blocking.

## Severity

| Rating | Meaning |
| ------ | ------- |
| Blocking | A person cannot complete the task (keyboard trap, unlabeled control, text below 3:1), or data can be lost by a misleading control |
| Should fix | A WCAG 2.1 AA failure that has a workaround, or an unexplained regression |
| Consider | Consistency or clarity issue, or a WCAG 2.2 / AAA improvement |
| Nit | Cosmetic, no one is blocked |

## Output format

```
## UI review: <change or PR>

**Scope:** <screens and states> · **Base:** <revision> · **Evidence:** <harness and command>

| # | Rating | Screen (file) | Element | Criterion | Observed | Who is affected | Direction |
|---|--------|---------------|---------|-----------|----------|-----------------|-----------|
| 1 | Blocking | commit-dialog-dark.png | `#commitMessageGenerate` | 1.4.3 | text #8a8a8a on #2d2d2d, 3.99:1 (needs 4.5:1) | low-vision users in the dark theme | use the theme's foreground token |

**Regression:** <screens identical to base / differences and whether they are explained>

**Not checked:** <themes, widths, states, assistive technology, anything not rendered>

**Verdict:** <no blocking findings | n blocking findings: list>
```

With no findings, keep the table header, write "none" in one row, and still list **Not checked**.

## Conventions

- Reference screens by the screenshot file name the harness wrote, so the reader can open it.
- Mark a finding seen only in HTML or CSS, not in a rendered screen, as `static` in the Observed column.
- Keep regression noise out of the findings, but say how it was told apart from real change.
- One finding per element and criterion; a pattern repeated across screens is one finding listing them.
- Network access and installs are not needed; use what the repository already runs.
````
