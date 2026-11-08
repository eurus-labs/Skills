---
type: llm
---

PASS if the generated verification skill has a checks table that covers lint (`make lint`, pyflakes) and tests (`make test`), marks both required because CI gates on them, and accounts for build and static analysis as well, with a reason if there is none. The report gives each check a trial-run result, and a check that could not run, such as pyflakes not being installed, is `not run` with that blocker.
FAIL if lint is missing, if a check that could not run is reported as passed, or if the report claims every command was trial-run without showing their results.
