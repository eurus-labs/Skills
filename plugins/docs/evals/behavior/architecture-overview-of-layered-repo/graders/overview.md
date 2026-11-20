---
type: llm
---

PASS if the reply describes the architecture it documented: the CLI and HTTP entry points, `OrderService.record`, `Store.put`, and the dependency direction from `api` to `core` to `infra`.
FAIL if it delivers a questionnaire, a list of files, or a generic product manual instead of an architecture overview, or describes a call it shows no evidence for.
