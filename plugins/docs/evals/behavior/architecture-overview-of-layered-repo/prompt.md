---
description: tests/contracts/layered-repo — an unattended architecture request must get a reviewed architecture draft, left for the user's final answer
tags: [behavior, expensive]
max_turns: 120
timeout_seconds: 3600
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Write architecture documentation for this codebase, as pages under docs/: components, dependencies, entry points and the order flow.

I won't be around to answer questions; make the choices you can make yourself, note them, and leave anything that needs my own answer for when I'm back.
