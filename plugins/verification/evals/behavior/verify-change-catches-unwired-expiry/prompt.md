---
description: fixtures/07 — green tests, new tests that fail on main, and a goal the change does not meet
tags: [behavior]
max_turns: 40
timeout_seconds: 1200
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Verify my branch `reset-token-expiry` against issue #41 before I merge it into `main`.

Issue #41: "Password-reset tokens must expire 30 minutes after they are issued. Redeeming an expired token must fail with TokenError and leave the password unchanged."

You may check out `main` in a temporary git worktree if you need it.
