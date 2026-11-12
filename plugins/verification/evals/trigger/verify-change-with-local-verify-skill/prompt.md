---
description: should fire verify-change even though the repository has its own verify skill
tags: [trigger]
max_turns: 6
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill]
---

Verify my branch `fix-rounding` against issue #31 before I merge it.
