---
name: review-ui
description: Review the user interface a change produces — rendered screenshots, the page's HTML and styles, before and after — for accessibility against WCAG 2.1 level AA, consistency with the existing interface, clarity of wording and states, and unintended visual change, with each finding ranked by severity and naming the screen, the element, the criterion and who is blocked. Use whenever the user says "review the UI", "check the screens", "is this accessible", "a11y check", "check contrast", "does this look right", "compare the screenshots", asks to look over a new dialog, panel, page or webview before merging, or a pull request changes HTML, CSS, templates or webview scripts. To review the code itself use review-code instead; to review a test suite use `review-tests` from the `testing` plugin.
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
   `package.json` scripts, or the test folder); do not install a new tool. If the harness starts a server or app, stop it when the capture is
   done. For each affected screen capture:
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

## Bundled resources

None. Everything this skill requires is in this file.

## Conventions

- Reference screens by the screenshot file name the harness wrote, so the reader can open it.
- Mark a finding seen only in HTML or CSS, not in a rendered screen, as `static` in the Observed column.
- Keep regression noise out of the findings, but say how it was told apart from real change.
- One finding per element and criterion; a pattern repeated across screens is one finding listing them.
- Network access and installs are not needed; use what the repository already runs.
