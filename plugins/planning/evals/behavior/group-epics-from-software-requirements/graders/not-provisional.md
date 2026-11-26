---
type: regex
target: { source: file, path: requirements/export/epics.md }
pattern: '(?im)^# .*provisional'
match: not_contains
---
