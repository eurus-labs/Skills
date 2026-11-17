---
description: should fire implement
tags: [trigger]
max_turns: 6
allowed_tools: [Read, Glob, Grep, Skill]
---

Here is an approved plan.

Plan: add request logging
Status: approved
Goal: log one line per request in the app's request handler.
Acceptance criteria:
- Each request writes one log line with its method and path.
- A test checks that the line appears.

Implement this plan.
