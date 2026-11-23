---
name: digest-notes
description: Condense meeting notes into a digest of the decisions made and the action items, each with an owner. Use when the user says "summarize these notes", "recap the meeting", "what were the action items", or "digest my notes".
---

# Digest notes

## Overview

Condense raw meeting notes into a digest: the decisions made, and the action items with their owners.

## When to use this skill

- The user pastes or points to meeting notes and wants a digest, a recap, or the action items.

## When not to use this skill

- **The input is an audio or video recording** — this skill reads text only.
- **The user wants the notes rewritten or proofread** — that is editing, not digesting.

## Hard rules

1. Report only what the notes say. Never add a decision or an owner the notes do not state.
2. Mark an action item with no owner as `owner: unassigned`.

## Output format

```markdown
## Digest
<two or three sentences>

## Decisions
- <decision>

## Action items
- <task> — owner: <name>
```

## Steps

1. Read the notes the user gave, in full.
2. List the decisions the notes state.
3. List each action item with its owner, or `owner: unassigned`.
4. Print the digest in the output format above.

## Conventions

- **Side effects.** Reads the notes file. Writes nothing and installs nothing.
