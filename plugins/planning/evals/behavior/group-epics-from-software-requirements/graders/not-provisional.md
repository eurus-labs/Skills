---
type: regex
target: { source: file, path: requirements/export/epics.md }
pattern: '(^|\n)# [^\n]*[Pp]rovisional'
match: not_contains
---
