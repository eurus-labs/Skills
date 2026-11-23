---
type: llm
focus: { source: file, path: AGENTS.md }
---

The text is the `AGENTS.md` the run wrote for a repository with two independent packages: `services/api`, a Python API, and `apps/web`, a JavaScript UI.

PASS if it scopes `python -m pytest` to `services/api`, after the install command `python -m pip install -e '.[test]'`, and scopes `npm test` to `apps/web`. Patterns seen in a source file may appear if they are labelled as observations.
FAIL if it gives a repository-wide test runner, such as a root-level pytest rule that covers the JavaScript package, if it invents a lint command, or if it states a mandatory convention (a commit format, an import rule, a definition of done) drawn from one source file.
