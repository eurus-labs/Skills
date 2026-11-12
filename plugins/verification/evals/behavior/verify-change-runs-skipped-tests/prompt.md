---
description: fixtures/11 — the fast suite is green because the tests that catch the bug are skipped
tags: [behavior]
max_turns: 40
timeout_seconds: 1200
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Verify my branch `bulk-rate` against issue #61 before I merge it into `main`.

Issue #61: "Orders over 20 kg ship at the bulk rate of 0.50 per kg. Orders of 20 kg or less keep the standard rate."
