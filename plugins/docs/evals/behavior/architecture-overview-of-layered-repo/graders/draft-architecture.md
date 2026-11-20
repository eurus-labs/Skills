---
type: llm
focus: { source: file, path: .docs-build/rendered-docs/architecture.rst }
---

The text is a drafted reStructuredText page. Its source references sit in `.. only:: audit` blocks as `path:line`.

PASS if it describes the three parts `api`, `core` and `infra`, and shows that dependencies point from `api` to `core` and from `core` to `infra`, with `path:line` references.
FAIL if the page is missing or empty, is only a list of files or directories with no dependencies, or gets the dependency direction wrong.
