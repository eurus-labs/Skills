---
type: llm
focus: files
---

PASS if the documentation the run wrote covers the CLI and HTTP entry points, `OrderService.record`, `Store.put`, and the dependency direction from `api` to `core` to `infra`, and ties each claim to the source file it comes from.
FAIL if no documentation pages were written, or they are a questionnaire, a list of files, or a generic product manual instead of an architecture overview, or they describe a call they show no evidence for.
