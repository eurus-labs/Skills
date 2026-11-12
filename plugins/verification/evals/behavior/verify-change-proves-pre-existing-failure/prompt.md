---
description: fixtures/12 — a correct change, and a required check that already fails on main
tags: [behavior]
max_turns: 40
timeout_seconds: 1200
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Verify my branch `add-tax` against issue #64 before I merge it into `main`.

Issue #64: "Add add_tax(amount, rate) that returns the amount plus tax, rounded to cents. Nothing else should change."

You may check out `main` in a temporary git worktree if you need it.
