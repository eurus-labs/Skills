---
name: workflow-slides-blocks
description: Make or refine a simple, visual PowerPoint slide that shows a workflow, process, before/after comparison, problem and solution, or operating model, drawn as 1–4 framed blocks of icon + short-label nodes in 2–3 colours, built with python-pptx on top of the user's own .pptx so its theme, size and other slides stay intact. Starts with a scope card that fixes the slide's one message, then builds, checks for overlaps and overflow, and validates the file. Use when the user says "refine this slide", "redraw this slide", "apply the template to this slide", "make a workflow slide", "turn this process into a slide", "fewer words, more visual", "theo template", "vẽ lại slide", or "làm slide workflow", or hands over a .pptx with a text-heavy or SmartArt process slide. Not for a whole deck of text or bullet slides, data charts or dashboards on their own, Google Slides or Keynote files, or written documents; to document a codebase, use document-codebase instead.
---

# Workflow slides as simple visual blocks

## Overview

Turn a workflow, process, before/after, problem–solution, or operating-model idea into one slide that reads at
a glance: framed blocks, each holding a few nodes, each node an icon and a one-to-three-word label, joined by
arrows. Sentences move to the speaker notes.

The deliverable is a real `.pptx`: the user's deck with the target slide rebuilt, or a new deck when there is
none, plus a short reply with the scope card, what changed, the assumptions, and one challenging question
about the story or the data.

Principles, in priority order:

1. **Analyze first, draw second.** Agree the message and the scope before touching a shape.
2. **Simple, not decorative.** 2–3 colours in all, white background, no gradients or shadows, no filled tiles
   behind icons.
3. **Pictures over words.** Every idea is an icon and a 1–3 word label.
4. **Draw in blocks.** 1–4 framed blocks; the content decides how many, never a quota.
5. **Use the deck's own look** — its font and corporate colour — when it has one.

## When to use this skill

- The user gives a `.pptx` and asks to refine, redraw, simplify, or "apply the template" to a process,
  workflow, before/after, or operating-model slide.
- The user describes a process in words and wants it as one visual slide.
- A slide is a wall of text or a SmartArt diagram that should become a flow.

## When not to use this skill

- **A whole deck of text or bullet slides**, or editing slide text in place — that is ordinary PowerPoint
  work; this skill rebuilds one diagram slide at a time.
- **A chart or dashboard on its own** — use a native chart; this skill adds a chart only when a number is part
  of the workflow's message.
- **Google Slides, Keynote, or an image of a slide with no `.pptx`** — this skill writes `.pptx` only. From an
  image, it can build a new slide; say that the original's theme cannot be kept.
- **Documentation of a codebase** — use `document-codebase` from the `docs` plugin.

## Requirements

- **Required:** Python 3.9+ with `python-pptx`, `lxml` (installed with it) and `Pillow`. Check with
  `python3 scripts/wfslides.py --check-deps`. If any is missing, stop and give the user the command
  `python3 -m pip install python-pptx Pillow`; **this skill never installs anything.**
- **Optional:** LibreOffice (`soffice`) and Poppler (`pdftoppm`) to render the slide and look at it. Without
  them, say the slide was not rendered and must be checked in PowerPoint.

`scripts/slide_text.py` and `scripts/check_pptx.py` use the standard library only, so they run before the
requirement check.

## Hard rules

1. **Never modify the user's file.** Copy it into a working folder and write the result as a new file,
   `<name>-refined.pptx` next to the original unless the user names another path. Write your build script in
   a different folder from the deck you were given.
2. **Change only the slides you were asked to.** `scripts/check_pptx.py --original` lists the slides whose XML
   changed; anything beyond the target slide is a defect to undo.
3. **Never invent numbers.** A figure the sources do not give is written `[DATA NEEDED]`. Numbers read off a
   screenshot or dashboard image are approximate — say so in the notes.
4. **Keep the user's terms** — product names, abbreviations, internal acronyms — exactly as given. Flag an
   abbreviation you cannot expand; do not expand it by guessing.
5. **One message per slide.** If the content carries two, propose splitting it.
6. **Keep the slide's existing speaker notes.** `c.notes()` adds the moved sentences after them; pass
   `replace=True` only when the user asks for their notes to go.
7. **Fix every warning `Canvas.check()` reports** before saving, and never shrink text below 11 pt to do it.

## Output format

The scope card, shown in the reply — before building when the slide is new or the story is unclear, together
with the result when it is a straightforward refine:

```text
SCOPE CARD — <slide title>
Message : <one sentence the audience must remember = the takeaway line>
Audience: <who decides / reads>
In      : <what this slide shows>
Out     : <moved to notes / to another slide>
Shape   : <linear flow | before/after lanes | loop | cycle model | input→process→output | stack>
Blocks  : <1–4 blocks, each: title → nodes>
Gaps    : <missing numbers, unclear terms, order doubts — what a manager will ask>
```

Then, in the user's language: the output path, 3–5 bullets on what changed, the assumptions, whether the
slide was rendered and checked, and one question that challenges the story or the data.

## The look

A 1920 × 1080 px grid; 1 pt = 2 px. Read the deck theme first with `read_theme(prs)`.

- **Font:** the theme's heading font via `+mj-lt`. The renderer may not have the deck's font, so renders are
  approximate — keep about 10 % slack and tell the user to check in PowerPoint.
- **Colours:** if the deck has a clear corporate primary (its `accent1`, or the colour its slides already
  use), that is `primary`. Otherwise the defaults: primary `0F4C81`, second `12807A`, accent `EF7A22` — the
  accent marks **one** thing per slide, such as the "accepted" exit. Neutrals: ink `1A1D24`, muted `5B6270`,
  line `D9DDE2`, light `F5F7F9`. Office's default accents (`156082`, `E97132`, `4F81BD`, …) are not a
  corporate palette; use the defaults instead.

| Element | Spec |
| ------- | ---- |
| Title | (36, 44), UPPERCASE bold 26 pt ink, one line |
| Subtitle | (36, 114), 15 pt muted, one line |
| Block | Rounded outline 1.2 px; dashed = input or process, solid = result; UPPERCASE block title in the block colour, with a number badge |
| Icon | Outlined line icon (white fill, ink stroke), 56 px, no background circle |
| Node | Icon + bold label 14–16 pt (≤ 2 lines) + muted sub-label 11.5–12.5 pt (≤ 2 lines) |
| Step number | `chip_for(icon_cx, icon_cy, n, colour)` — always at the icon's top-left, never placed by hand |
| Arrow | Straight 1.5 px, triangle head; loop-backs and optional paths dashed, with a 1–4 word label |
| Takeaway | One bold line at y ≈ 905, after 1–2 small icons |
| Page number | Bottom right, 12 pt muted |

The standard three-block grid, adapted when the content needs it: block 1 at x 70 w 470, block 2 at x 590
w 770, block 3 at x 1410 w 450, all at y 170 h 690. Keep at least 40 px between blocks.

Layout patterns:

```text
BEFORE / AFTER LANES (problem slide)         INPUT → PROCESS → OUTPUT
[BEFORE  request → manual step → ✔ same day]  [INPUT ] [ PROCESS                 ] [RESULT ]
[AFTER   request → hand-off → wait → 15–20 d]  draft ┐  ①prepare → ②check → ③final   ✔ list
           ↓                                   input ┘   rework ← feedback ← review   ↑
[1 hand-off → 2 meet → 3 fix → 4 build → 5]             └── revise × n ──┘ accepted → accept

CYCLE MODEL (operating model)
[CURRENT  list ↓ ticket ↓ code ↓ check] ⇒ [TARGET  need → analyze → decide → build → validate → improve (circle)] [ENABLERS  icon rows]
```

Also: a flow row (4–6 nodes with chips), a loop (4 nodes in a rectangle around a label, the exit arrow in the
accent), and a stack (a vertical hierarchy). A chart only when its numbers are the point: a native chart, one
colour family, greys for "cost" categories, tiny labels hidden with the number format `[<thr]"";#,##0`.

## Icons

In order of preference:

1. **The user's or team's icon set**, if they point to one — outlined PNGs; use each file's name as the icon's
   name, and look at any example slides that come with it before designing.
2. **Shape icons** built into `wfslides.py`: pass a name from `SHAPE_ICONS` (`document`, `database`, `decide`,
   `cloud`, `config`, `loop`, `feedback`, `target`, `risk`, `user`, …) where a PNG path would go. They are
   native outlined shapes, editable in PowerPoint.

Say in the reply which set was used.

## Steps

1. **Check the requirements** (above). Copy the deck into a working folder (hard rule 1).
2. **Read everything.** `python3 scripts/slide_text.py deck.pptx` prints each slide's text, its SmartArt text
   and its notes. Render it when you can — `soffice --headless --convert-to pdf deck.pptx`, then
   `pdftoppm -jpeg -r 70 deck.pdf page` — and look at every page.
3. **Write the scope card** (output format). Ask only when the order of the flow or the scope is genuinely
   ambiguous; otherwise state the assumption and build.
4. **Build** in a script in its own folder that imports `scripts/wfslides.py`:

   ```python
   import sys; sys.path.insert(0, "<skill folder>/scripts")
   from pptx import Presentation
   from wfslides import Canvas, read_theme
   prs = Presentation("work/deck.pptx")
   c = Canvas(prs, prs.slides[2], palette={"primary": "..."}, font="+mj-lt")
   c.clear(); c.title(...); c.block(...); c.vnode(...) or c.hnode(...); c.chip_for(...)
   c.line(...) or c.poly(...); c.takeaway(...); c.notes(...)
   print(c.check())
   prs.save("deck-refined.pptx")
   ```

   For a new deck, start from `Presentation()` and set `slide_width` and `slide_height` to 16:9.
5. **Fix every warning** `c.check()` prints — `WRAP`, `OVERFLOW`, `CROSS`, `OVERLAP` — by shortening words
   first, then moving or widening; never below 11 pt (hard rule 7). Do not pass `track=False` for free text
   such as an arrow's label; only text inside a shape is untracked, so `check()` sees every label.
6. **Validate**: `python3 scripts/check_pptx.py deck-refined.pptx --original deck.pptx` must print
   `package OK`, and `changed slides:` must list only the target slide (hard rule 2).
7. **Render and look**: arrows ending in empty space, uneven gaps, more than three colours, labels outside
   their blocks or touching lines, empty corners, crowded blocks. `check()` is necessary but not sufficient.
   Fix, and re-render the changed slide only.
8. **Report** in the output format.

## Gotchas

- New shapes and connectors carry a theme `p:style`, which adds shadows; `Canvas` removes it, so remove it
  from any shape you add without `Canvas`.
- Recolouring existing icons: also remove picture `spPr` fills and group `grpSpPr` fills. Track processed
  pictures by element, not `id()` — lxml proxies are recycled.
- Hidden white icons left over from an old design become visible after recolouring; delete orphans.
- SmartArt cannot be restyled: `clear()` drops it; redraw it with nodes and arrows.
- Deleting a slide: drop its relationship from `prs.part` and remove it from `sldIdLst`; python-pptx leaves
  out unreferenced parts when it saves. Run `check_pptx.py` afterwards.
- `fit()` measures text with Liberation or DejaVu fonts under `/usr/share/fonts`; elsewhere it estimates from
  character counts, so leave more slack.

## Bundled resources

| Path | Use |
| ---- | --- |
| `scripts/wfslides.py` | The `Canvas` helper: shapes, nodes, chips, arrows, notes, shape icons, and `check()`. Import it from the build script; `--check-deps` checks the requirements. |
| `scripts/slide_text.py` | Step 2: each slide's text, SmartArt text and notes. Standard library only. |
| `scripts/check_pptx.py` | Step 6: the package is well formed, and which slides changed. Standard library only. |

## Conventions

- **Side effects.** Writes the copied deck, the build script, renders, and the result file in the working
  folder or the path the user names; never writes to the original. Rendering runs LibreOffice, which may write
  its profile under the user's home directory. No network access. Requires python-pptx and Pillow
  (Requirements); installs nothing.
- Reply in the user's language; keep the slide in the deck's language.
