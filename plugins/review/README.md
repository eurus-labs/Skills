# review

Review code against an established standard, review the interface a change produces, and set up the rules
files that keep agents aligned with a repository's conventions.

Code findings follow [Google's *Standard of Code Review*](https://google.github.io/eng-practices/review/reviewer/standard.html)
— approve when the change definitely improves overall code health — labelled with Conventional Comments
(`issue:`, `suggestion:`, `nit:`, `question:`, `praise:`) and named with CWE identifiers for security issues.
Interface findings are checked against WCAG 2.1 AA and ranked Blocking, Should fix, Consider or Nit.
The skills connect: the review checklist `setup-review-rules` writes is linked from `AGENTS.md`, and
`review-code` reads it — with the rest of the repository's rules files — before reviewing.

`review-ui` draws on ideas from the accessibility-review and design-critique skills of Claude's design plugin.

## Install

```bash
copilot plugin marketplace add eurus-labs/Skills
copilot plugin install review@eurus-labs
```

Before 0.3.0 this plugin had a different install name, which no longer receives updates. If you installed it
under that name, run the commands above and uninstall the old copy; see the Breaking changes entry in
`CHANGELOG.md` of the source repository for the old name.

## Skills

- **`review-code`** — review a diff, PR, branch, or working tree for correctness, security, error handling,
  concurrency, test coverage, maintainability, and the repository's own rules. Severity-ordered findings, each
  with `file:line` and, above a nit, a concrete failure scenario. Fires on "review this", "check before I
  merge", "any security problems".
- **`review-ui`** — review the interface a change produces, from rendered screenshots, the DOM and styles, and
  the same screens on the base revision: accessibility against WCAG 2.1 AA, consistency with the existing
  interface, clarity of wording and states, and unintended visual change. Each finding names the screen, the
  element, the criterion and who is affected. Fires on "review the UI", "is this accessible", "check
  contrast", "compare the screenshots".
- **`setup-review-rules`** — generate `AGENTS.md`, `.github/copilot-instructions.md`, and a project-specific
  review checklist from what the repo actually does. Fires on "set up rules for this repo", "add AGENTS.md",
  "onboard this repo for agents".

## Notes

- `review-code` and `review-ui` report; they do not patch. `review-code` asks before editing anything.
- `review-ui` uses the repository's own screenshot or UI test harness, installs nothing, and never claims a
  screen is "accessible" or "WCAG compliant": it reports what was checked and what was not. It is not a
  substitute for testing with assistive technology.
- `setup-review-rules` never overwrites an existing rules file without confirmation, and never states a
  convention it did not observe in the repository.
- `references/review-standard.md` and `scripts/detect_stack.py` are generated from `shared/` in the source
  repository. Do not edit them here — edit `shared/` and run `python3 tools/materialize.py`.
