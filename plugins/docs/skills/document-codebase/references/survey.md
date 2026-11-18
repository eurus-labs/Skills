# Survey — what is in this repository

The first component. This file is what to read in its output and what to decide from it; which stages it
runs, which may fail without stopping it, and every flag are in [`pipeline.md`](pipeline.md).

**Checkpoint P1 closes this component**, and `analyze` will not run until it is decided.

```bash
python3 scripts/pipeline.py survey --root . --top 25
```

- **Read** the scanner's digest, every finding from the index validator, and the selected units with their
  fan-in and fan-out.
- **Decide** whether to continue, rescan, or stop and report the repository is out of scope — and whether the
  scope this picked is the right one.

**If the scan reports `FAIL no source files found`, stop and say so.** The scanner parses Python, JavaScript,
TypeScript, Go, Rust, Java, Ruby, C and C++. Report which extensions were present and that this skill cannot
cover them; do not fall back to reading files and writing an unverifiable document.

An `E007`/`E008` finding means the tree changed under the scan — rerun. These never enter a retry loop with
the model; they are defects in a deterministic step.

The digest names the **assets** — README, packaging manifests, CI workflows, ADRs, configuration, examples —
with a count per kind. These are listed, never parsed. They are what a page about installation or conventions
may cite, and the absence of one is itself an answer: a repository with no ADR gets "no decision record
exists", not a rationale you worked out.

**The scope is the product; the cutoff only orders the reading.** `build_scope.py` writes `scope.json`, which
gives every scanned file a disposition (`product`, `test`, `generated`, `vendor`, `asset`) and, for anything
that is not product, the rule that put it there — a `tests/` directory, a `third_party/` tree, a `Code
generated ... DO NOT EDIT` header. Read that classification at P1 and disagree with a rule you think is wrong;
never accept an exclusion you cannot explain. Every `product` file is a unit, including an entry or
side-effect module that defines no symbol (it owes one statement saying what it does, not four).

Reading is expensive, so `select_units.py` ranks the units by connections — how many modules import each one
plus how many it imports — and `--top` (default 25) is the size of the **next reading batch**, written to
`units.txt` together with every entry point. Fan-in alone ranks the shared helpers first and the modules that
drive the system last, because an orchestrator imports much and is imported by little; counting both
directions keeps both. The files outside the batch stay in `scope.json` as `unread`, each with the `batch`
it falls in. They are not dropped: a run with unread product files reports `incomplete: N product files
unread` and lists them, and `status` prints the count. Narrow the scope only deliberately: set a row's
`disposition`, a `reason`, and an `override` note saying who decided and why, and the report records it as a
scope change. **Read the warnings the selection prints.** A repository whose modules import nothing from each
other — standalone CLIs, scripts a scheduler runs — has no connections to rank, and the order it gets is
arbitrary rather than considered; say so in the document.

**A feature map is a checklist, never evidence.** When the repository has a `verify-*` skill with
`references/features/` under `.github/skills/`, `.claude/skills/` or `.agents/skills/`,
`read_feature_map.py` records each area's name and its `owns:` and `uses:` globs in `feature-map.json`. Each
area becomes a `feature:<area>` required topic, and the product files an area owns are one reading task.
`quality_docs.py` lists any area no section cites a file of. No sentence cites the map: it cites source, and
where the map's expected behavior disagrees with the code you record an open question for the user. With no map
the survey prints `no feature map found` and nothing else changes; offer `setup-verification` at P1 as the
skill says.

Ruff's import-usage annotation is advisory and additive. **An unused import is not evidence that a dependency
is unnecessary** — re-export, side effects, registration and dynamic discovery all look identical from here.
Report the count in the limitations with that caveat, and never propose removing an import as part of
documenting. `--policy disabled` if the user does not want an external tool invoked.

## The settings this repository reads

`survey` also extracts every setting the code reads — `os.environ[...]`, `os.environ.get`, `os.getenv`, and
`argparse` options — into `.docs-build/config-analysis.json`, then validates it.

**This is the one artefact a context packet cannot be.** A packet answers "what is this module for" by
handing over one file and its neighbours. "What configuration does this project take?" is not a question
about a module: the answer is spread across every file that reads one, so no amount of per-module context
assembles it, and without this the only way to answer it is to read the whole tree and hope.

It lists settings; **it does not know what they mean.** The name, where it is read, and a literal default if
there is one — that is the whole claim. What a setting does, what values are legal, what happens when it is
absent: those stay the model's to answer, and this file is what it answers them *from*.

`validate_config.py` then matches each name against the lines it cites (`C006`), which is the `O006` rule
applied here and the reason a `config:` id may stand behind a `confirmed` answer. A row that fails it is
refused rather than downgraded. A repository that reads no settings produces an empty list and says so.

**Pause here — P1.** The scope is the one decision that cannot be corrected later without paying for the
analysis twice. Show the units, the cutoff and the warnings, and ask before spending the budget.
