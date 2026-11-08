---
description: should fire verify-change and not setup-verification
tags: [trigger]
max_turns: 6
allowed_tools: [Read, Glob, Grep, Skill]
---

I've finished my uncommitted changes. Check them against these criteria and tell me if they're really done: 1) `export --csv` writes a header row; 2) empty reports still export.
