---
type: llm
focus: { source: file, path: .docs-build/rendered-docs/flows.rst }
---

The text is a drafted reStructuredText page. Its source references sit in `.. only:: audit` blocks as `path:line`, and it names functions by module, for example `cli.main` for `main` in `api/cli.py`.

PASS if it has a flow that starts at the CLI entry point (`cli.main`) and a flow that starts at the HTTP entry point (`Handler.post`), each reaching `OrderService.record` and then `Store.put`, and each step has a `path:line` reference.
FAIL if the page is missing or empty, either flow is missing, either call is missing, or a step has no reference.
