# Changelog

All notable changes to this marketplace. Each plugin also carries its own `version` in its
`plugin.json`; the release number below is the marketplace's `metadata.version`.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- **Eval board** (for contributors): `python3 tools/build_eval_board.py` writes `eval-board.html`, one page
  showing every skill's eval cases (must fire, must stay quiet, behavior) with the latest local result of
  each and the runs before it. Partial suites and errored runs are never counted as trusted scores. The
  interface switches between English and Vietnamese. Each host's results get their own badge: Claude Code
  and Copilot CLI are never mixed.
- **How to run the evals** (for contributors): `doc/running-evals.md` covers `claude plugin eval` and the
  Copilot runner, the credential, Windows setup, grading, reading results, and common errors. It explains how to choose
  and pin the model on each host. `tools/copilot_eval.py` takes `--model` and `--reasoning-effort`, gives both
  arms the same flags, and records them in the result, and the eval board shows the model beside the host. With `--run` it
  first checks that Copilot accepts the pinned flags, prints the last lines of Copilot's log when a run fails,
  and never grades a run whose Copilot process died.
- **Skill manager** (for contributors): `python3 tools/skill_manager.py` serves one local page with three tabs.
  *Skills* shows each skill's goal, install state per host, eval coverage, latest results and a status, including
  "changed since last run". *Install* installs, updates or removes plugins in Copilot CLI and Claude Code and
  registers the marketplace. *Evals* is the eval board with a Run form on every case. Runs and installs stream to
  the page, which asks grading questions with Yes, No and Skip, and opens a run's Markdown transcript as a
  readable page (roles, tool calls with folded arguments and output) that escapes everything the agent wrote. It listens on `127.0.0.1` with a token. The
  Copilot runner now asks `tool_used` graders as plain facts ("Did Copilot use the skill …?").
- **Copilot eval runner** (for contributors): `python3 tools/copilot_eval.py plugins/<plugin>` runs a plugin's
  eval cases on GitHub Copilot CLI, with and without the plugin, each in a fresh scaffolded workspace. It
  checks file graders itself, asks a person for the rest, and records the scores for the eval board.

- **`verification`** (0.1.3): five eval cases for the failures a pilot of the plugin found or could not
  exercise: a required check that cannot run (`fixtures/10`), tests skipped by default that hide a bug
  (`fixtures/11`), a required check already failing on `main` (`fixtures/12`), CI commands with shell pipes
  (`fixtures/13`), and a repository that already has its own verify skill (`fixtures/14`, triggering).
  Not run yet.

### Changed

- **`verification`** (0.2.0): one place judges a change. A pilot of the plugin on this repository found the
  generated `verify-<app>` skill competing with `verify-change` and reporting false greens.
  - The generated skill no longer claims "verify a change", has no review table or `met`/`not met` verdicts,
    and carries the no-edit, no-stash rules. `verify-change` gives the verdict and uses it.
  - Whether a check is required comes from CI or a written rule, never from whether it can run here.
  - A baseline no longer changes what passes: failing checks go under **Known failures**, and a failure is
    pre-existing only when it reproduces on the change's base.
  - Skipped tests are not evidence.
  - The CLI contract requires `check` to print every row of `## Checks` and to fail on a row it cannot read,
    to accept a commit range, to act on the current directory's repository, and to scope evidence to a run
    with a tree fingerprint.
  - `verify-change` ends its report with a JSON verdict for CI, and should run in a session that did not
    write the change when it gates a merge.
- **`implement`** (`development` 0.3.2) uses the project's verification skill for checks and confirmed
  behavior instead of its review table, and treats skipped tests and known failures the same way.
- **`verification`** (0.3.0): a generated `verify-<app>` skill holds up under shared code and parallel
  agents.
  - Feature areas list the shared code they use (`uses:`), and `affected` reports an area reached only
    through it as `via <path>`. A path no area owns or uses has no feature criteria: `verify-change` covers
    it from the goal or lists it under **Not verified**.
  - Each run starts the app on a free port with its data under `.verify/<run-id>/`; drive commands read the
    address from the new `url` command instead of a fixed port. A project that cannot be isolated says so
    under `## Isolation`. The trial run starts a second run alongside the first to prove it.
  - `stop` runs even after a failed step, and the new `clean` lists old run folders and deletes them only with `--yes`, after the user agrees, never a
    live one.
  - A behavior eval case on the new `fixtures/15-shared-code-change`: a branch that changes a helper the cart
    and the invoice export share, with a green suite. Not run yet.
- **`implement`** (`development` 0.3.3) follows the same `via` areas, `unmapped:` paths and `stop` rule.

## [0.2.0] — Unreleased

The first release under the **`eurus-labs`** name. It renames the marketplace, regroups skills into plugins by
capability, and adds three plugins and eval suites.

### Breaking changes

- **The marketplace is now `eurus-labs`** (it was `CopilotBox`, and some installs used `eurus-skills`).
  Install names change from `<plugin>@CopilotBox` to `<plugin>@eurus-labs`. Re-register once:

  ```bash
  copilot plugin marketplace remove CopilotBox --force   # or eurus-skills
  copilot plugin marketplace add eurus-labs/Skills
  copilot plugin install <plugin>@eurus-labs
  ```

- **`implementation` is split** into **`development`** (`design-solution`, `implement`) and **`verification`**
  (`setup-verification`, `verify-change`). If you installed `implementation`, install both
  `development@eurus-labs` and `verification@eurus-labs` instead.

### Added

- **`verification` plugin** (0.1.2):
  - **`verify-change`** (new): verifies an existing change — the working tree, a branch, a commit range or a
    pull request — against its goal, without editing code. It fixes the acceptance criteria first, then runs
    build, lint, static analysis and tests. Each check ends `passed`, `failed`, `not applicable` (with a
    reason) or `not run` (with the blocker). A failure counts as pre-existing only when it reproduces on the
    base. The report ends in one verdict.
  - **`setup-verification`** (moved from `implementation`): the `verify-<app>` skill it generates now has a
    `## Checks` table (command, when it applies, whether it is required, what passes) and a `verify check`
    command.
- **`skill-authoring` plugin** (0.1.1), with **`evaluate-skill`**: evaluates a skill on three levels.
  - Static: structure and scope.
  - Triggering: does it fire on the right requests and stay quiet on the wrong ones?
  - Behavior: does it beat no skill on a task whose answer was written beforehand?

  It writes the suite for `claude plugin eval` and reports what each failure points to. It asks before any
  billed run and never publishes results unless you agree.
- **`presentation` plugin** (0.1.1), with **`workflow-slides-blocks`**: makes or refines one simple, visual
  PowerPoint slide for a workflow, process, before/after or operating model, built on your own deck.
  - It starts with a scope card.
  - It writes `[DATA NEEDED]` instead of inventing numbers.
  - It keeps your speaker notes and writes a new `<name>-refined.pptx`; your file is never changed.
  - It checks that only the target slide changed.
  - **It requires `python-pptx` and `Pillow`**, which it never installs.
- **Eval suites** for `claude plugin eval` in `testing`, `docs`, `verification` and `presentation`, under each
  plugin's `evals/`: trigger cases in both directions, and behavior cases graded
  against `fixtures/EXPECTED.md`. Three new fixtures: `07-unverified-change`, `08-codified-bug` and
  `09-wordy-process-slide`. The evals have not been run yet; see each plugin README for the commands.

### Changed

- **`implement`** (`development`) names all four kinds of check in its verification step. It hands "verify
  without changing" to `verify-change`, and recommends `setup-verification` only for runtime changes or a
  first-time setup.
- **`write-tests`** (`testing`) and **`review-code`** (`code-review`) now point to `implement` in
  `development`.
- Every manifest's `author` and `repository` now name `eurus-labs`.

### Fixed

- **Claude Code can install the plugins.** `claude plugin marketplace add` failed with "Marketplace file not
  found": Claude Code reads only `.claude-plugin/marketplace.json`, and refuses a plugin `source` without a
  leading `./`. The marketplace now uses `./plugins/<name>`, which Copilot also accepts, and an identical
  `.claude-plugin/marketplace.json`; the validator keeps them identical. The README shows the Claude Code install.
- **Evals load.** The first real `claude plugin eval` run found that nine eval descriptions were invalid YAML
  (four `verification` cases and five `presentation` cases refused to load) and that no plugin resolved at
  all, because Claude Code reads `.claude-plugin/plugin.json` and the manifests only existed at
  `.github/plugin/plugin.json`. Every plugin now carries both, and the validator and two new tests keep
  them identical and the eval frontmatter parseable.
- **`implement`** never runs a dependency install.
- **`document-codebase`** (`docs`): `verify_doc` resolves method receivers correctly in more cases, including
  `self.m` assignments that shadow a base method, `__dict__` replacement and nested functions without `self`.

### For contributors

- `main` is the only long-lived branch; `dev` is retired. Open pull requests against `main`.
- Bundled scripts stay standard library only, with one named exception: a package required to write an
  output file format the standard library cannot (today `.pptx`), listed in
  `.github/instructions/domain/scripts.instructions.md`.
- `tools/build_eval_scaffolds.py` generates each behavior case's `scaffold.sh` from its fixture, including git
  history and binary files; `tools/test_eval_scaffolds.py` checks they match.

### Plugin versions in this release

| Plugin | Version |
| ------ | ------- |
| `testing` | 0.3.5 |
| `code-review` | 0.2.4 |
| `docs` | 1.3.6 |
| `development` | 0.3.1 |
| `verification` | 0.1.2 |
| `skill-authoring` | 0.1.1 |
| `presentation` | 0.1.1 |
