---
description: should fire setup-verification and not verify-change
tags: [trigger]
max_turns: 6
allowed_tools: [Read, Glob, Grep, Skill]
---

We added a billing module since the verify skill under .github/skills was written, and it knows nothing about it. Bring that verification skill up to date.
