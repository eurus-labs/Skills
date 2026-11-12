# Changelog

All notable changes to this marketplace. Each plugin also carries its own `version` in its
`plugin.json`; the release number below is the marketplace's `metadata.version`.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
