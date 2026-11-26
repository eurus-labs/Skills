# planning

Turn a requirement into work, in three steps that share one ID scheme and one check script. The tech lead
analyses the requirement with the Product Owner (PO) until nothing blocks, derives software requirements from
it, and groups those into epics. None of the skills changes code or sends anything to the PO.

## Install

```bash
copilot plugin marketplace add eurus-labs/Skills
copilot plugin install planning@eurus-labs
```

`analyze-requirements` used to be in `reasoning` (before 0.5.0). Install `planning` to keep it.

## Skills

- **`analyze-requirements`** — step 1. Reads the requirement (`.md`, `.txt` or `.rst`, from a file, pasted, or a
  requirement repository), its previous version, the DoD (Definition of Done), the DoU and the code. It writes
  `analysis.md`, with the requirements as system requirements `SYS-001…`, each checked against the DoD and the
  code with `path:line`; and `dou.md`, the one file of points for the PO, `DOU-001…`. Each pass adds points;
  after each discussion it records only what the PO said, closes the points answered and applies them. It never
  answers for the PO. `analysis.md` is `Status: final` only when no blocking point is open. Fires on "analyze
  this requirement", "compare this requirement with the previous version", "update the analysis from the DoU",
  "cập nhật requirement analysis từ DoU với PO".
- **`derive-software-requirements`** — step 2, in the style of ASPICE SYS to SWE. Derives `SWR-001…` from a final
  `analysis.md`: one "The software shall …" statement each, with its rationale, its trace to `SYS-` IDs, its type,
  verification criteria that meet the DoD, and the code area. A two-way traceability table closes the file. It
  states what the software does, never how to build it, and never edits `analysis.md` or `dou.md`. Fires on
  "derive software requirements from this analysis".
- **`group-epics`** — step 3. Groups `software-requirements.md` into epics `E-01…`, each with a goal, its `SWR-`
  IDs, acceptance criteria with a negative case, dependencies, risks and code areas, and a traceability table
  `SYS-` to `SWR-` to `E-`. It edits nothing before it. Fires on "split these software requirements into
  epics", "tách epic".

| You ask for | Skill |
| ----------- | ----- |
| A requirement analysed, compared with its previous version, checked against the DoD, a DoU recorded | `analyze-requirements` |
| Software requirements derived from the final analysis | `derive-software-requirements` |
| The software requirements grouped into epics | `group-epics` |
| How to build a change, answered in chat; or a plan saved to a file | `design-solution`, `write-plan`, in the `reasoning` plugin |

## How the chain works

Every artifact goes in one topic folder, `requirements/<topic>/` by default, in the language of the requirement:

```
requirements/<topic>/
  analysis.md                step 1   SYS-001…   Status: draft | final
  dou.md                     step 1   DOU-001…   Status: open | closed
  software-requirements.md   step 2   SWR-001…
  epics.md                   step 3   E-01…
```

1. Run `analyze-requirements` with the requirement and the DoD. Take the points in `dou.md` to the PO.
2. Bring back your notes, or an edited `dou.md`, and run it again. It closes the points the PO answered and
   applies them. Repeat until `analysis.md` is `final`.
3. Run `derive-software-requirements`. If a blocking point is still open, it lists the points and stops. A gap
   it finds while deriving becomes a new point for `analyze-requirements`; it never edits the earlier files.
4. Run `group-epics` on the software requirements.
5. After every write each skill runs `scripts/requirements.py check`, which fails on a duplicated or unknown ID,
   a closed point with no answer or no date, a final analysis over a blocking point, an in-scope system
   requirement with no software requirement, a software requirement with no system requirement or in no epic
   or two, and a non-provisional file over a draft analysis.

## Notes

- **Side effects:** the skills write only their own files in the topic folder and never commit them unless you
  ask. `analyze-requirements` asks where the requirement, the DoD and the code live, and may run `git clone` and
  `git fetch` (network access) for a repository you name, writing the clone only to a destination you confirm.
  Its bundled script, `requirements.py`, is standard library only, reads only the files it is given, makes no
  network call and writes nothing. The same script is authored once in `shared/` and bundled in each skill.
- The DoD is read, never written. With no DoD, the analysis records "DoD not given" as a point that does not
  block.
- Stories, estimates, and a Jira or CSV export are out of scope; the chain stops at epics.
