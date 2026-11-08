# presentation

Make slides that explain a process at a glance. The first skill turns a workflow, a before/after, or an
operating model into one simple, visual PowerPoint slide, built on your own deck.

## Install

```bash
copilot plugin marketplace add eurus-labs/Skills
copilot plugin install presentation@eurus-labs
```

## Skills

- **`workflow-slides-blocks`** — rebuilds one slide, or makes a new one, as 1–4 framed blocks of icon +
  short-label nodes joined by arrows, in 2–3 colours taken from your deck's theme when it has one. It works in
  this order:
  - starts with a **scope card** that fixes the slide's one message, what is in and out, and the gaps;
  - moves sentences to the speaker notes and writes `[DATA NEEDED]` for numbers nobody gave;
  - checks the layout for wrapped, overflowing, crossing and overlapping text;
  - validates the saved file and confirms that only the target slide changed;
  - renders the slide, when LibreOffice is available, and looks at it.

  Fires on "refine this slide", "redraw this slide", "apply the template", "make a workflow slide",
  "theo template", "vẽ lại slide".

| You ask for | Skill |
| ----------- | ----- |
| A process, workflow, before/after or operating-model slide made or refined | `workflow-slides-blocks` |
| Documentation of a codebase | `document-codebase`, in the `docs` plugin |

## Requirements

- **Required:** Python 3.9+ with **`python-pptx`** and **`Pillow`**: `python3 -m pip install python-pptx Pillow`.
  The skill checks for them first and stops with that command if they are missing. **It never installs
  anything.**
- **Optional:** LibreOffice (`soffice`) and Poppler (`pdftoppm`), to render the slide and check it visually.
  Without them, the skill says the slide was not rendered.

## Notes

- **Side effects:** the skill never writes to your file. It writes a copy, its build script, renders, and
  `<name>-refined.pptx` in the working folder or the path you name. No network access.
- **Bundled scripts:** `wfslides.py` requires python-pptx and Pillow. This is the repository's one named
  exception to standard-library-only scripts, for an output format the standard library cannot write.
  `slide_text.py` and `check_pptx.py` use the standard library only.
- **Icons:** it uses your or your team's outlined PNG icon set when you point to one. Otherwise it uses
  outline icons drawn as native PowerPoint shapes, which you can edit like any other shape.
- **Fonts:** a render uses the fonts installed where it runs. If your deck's font is missing there, the
  layout is approximate; check it in PowerPoint.
