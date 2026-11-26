# backlog

Turn settled requirements into a delivery backlog. Today that is one skill, `split-epics`, which splits a
requirement analysis into epics. Stories, estimates and a Jira export may follow.

## Install

```bash
copilot plugin marketplace add eurus-labs/Skills
copilot plugin install backlog@eurus-labs
```

`split-epics` reads the `analysis.md` that `analyze-requirements` writes, so install `reasoning@eurus-labs`
too unless you write the analysis yourself in the same format.

## Skills

- **`split-epics`** — reads a topic folder (`requirements/<topic>/`) holding `analysis.md` and its `dou-NNN.md`
  files, and writes `epics.md` beside them. Every in-scope requirement is in exactly one epic or in a "Not in
  any epic" list with the reason. Each epic has a goal, its R- IDs, acceptance criteria with a negative case,
  dependencies, risks and code areas, and a traceability table closes the file. It writes epics only when no
  blocking open point is open; otherwise it lists the blocking points and stops, unless you explicitly ask for
  epics, and then the file is headed `Provisional` and each dependent epic names its open point. It never edits
  the analysis or a DoU: a requirement that looks wrong becomes a note to take back to `analyze-requirements`.
  Fires on "split this requirement analysis into epics", "tách epic từ requirement analysis này". With no
  `analysis.md` it says so and names `analyze-requirements`.

| You ask for | Skill |
| ----------- | ----- |
| The settled analysis split into epics | `split-epics` |
| A requirement compared with its previous version, open points, a DoU | `analyze-requirements`, in the `reasoning` plugin |

## How it works

1. Run `analyze-requirements` until no blocking open point is open. It tells you the analysis is ready.
2. Ask for the epics. The skill runs `scripts/requirements.py check` on the folder, lists any blocking open
   point, and otherwise writes `epics.md` from its template.
3. It runs `check` again, which fails on a requirement in no epic or in two, and on epics not marked
   `Provisional` while a blocking point is open. Take any note it leaves back to `analyze-requirements`.

## Notes

- **Side effects:** `split-epics` writes `epics.md` in the topic folder and never commits it unless you ask. Its
  bundled script, `requirements.py`, is standard library only, reads only the files it is given, makes no
  network call and writes nothing. The same script is authored once in `shared/` and is also bundled in
  `reasoning`.
- The epic split was part of `analyze-requirements` before `reasoning` 0.5.0.
