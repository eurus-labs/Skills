#!/usr/bin/env bash
# GENERATED FILE -- DO NOT EDIT. Regenerate with: python3 tools/build_eval_scaffolds.py
# Recreates fixtures/16-flawed-skill in the eval's empty workspace.
set -euo pipefail
mkdir -p '.claude-plugin'
cat > '.claude-plugin/plugin.json' <<'EVAL_FIXTURE_EOF'
{
  "name": "notes-helper",
  "description": "Turn meeting notes into a short summary with decisions and action items.",
  "version": "0.1.0",
  "keywords": [
    "notes",
    "meetings"
  ],
  "author": {
    "name": "example"
  },
  "license": "MIT",
  "skills": [
    "./skills/summarize-notes/"
  ]
}
EVAL_FIXTURE_EOF
mkdir -p '.github/plugin'
cat > '.github/plugin/plugin.json' <<'EVAL_FIXTURE_EOF'
{
  "name": "notes-helper",
  "description": "Turn meeting notes into a short summary with decisions and action items.",
  "version": "0.1.0",
  "keywords": [
    "notes",
    "meetings"
  ],
  "author": {
    "name": "example"
  },
  "license": "MIT",
  "skills": [
    "./skills/summarize-notes/"
  ]
}
EVAL_FIXTURE_EOF
mkdir -p 'skills/digest-notes'
cat > 'skills/digest-notes/SKILL.md' <<'EVAL_FIXTURE_EOF'
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
EVAL_FIXTURE_EOF
mkdir -p 'skills/summarize-notes'
cat > 'skills/summarize-notes/SKILL.md' <<'EVAL_FIXTURE_EOF'
---
name: summarize-meeting-notes
description: Summarize meeting notes into a short summary with the decisions made and the action items, each with an owner. Use when the user says "summarize these notes", "recap the meeting", "what did we decide", or "list the action items".
---

# Summarize meeting notes

## Overview

Turn raw meeting notes into a summary a reader can act on in under a minute: what was decided, and who does
what next.

## When to use this skill

- The user pastes or points to meeting notes and wants a summary, a recap, or the action items.

## When not to use this skill

- **The input is an audio or video recording** — this skill reads text only.
- **The user wants the notes rewritten or proofread** — that is editing, not summarizing.

## Hard rules

1. Report only what the notes say. Never add a decision or an owner the notes do not state.
2. Mark an action item with no owner as `owner: unassigned`.

## Output format

```markdown
## Summary
<two or three sentences>

## Decisions
- <decision>

## Action items
- <task> — owner: <name>
```

## Steps

1. Read the notes the user gave, in full.
2. Run `python3 scripts/extract_actions.py <notes-file>` to list the lines that look like action items. Run it;
   do not read it.
3. Write the summary and the decisions from the notes.
4. Write the action items from the script's list, checking each against the notes.
5. Print the summary in the output format above.

## Conventions

- **Side effects.** Reads the notes file. Writes nothing and installs nothing.
EVAL_FIXTURE_EOF
