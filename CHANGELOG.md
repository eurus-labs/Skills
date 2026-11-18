# Changelog

All notable changes to this marketplace. Each plugin also carries its own `version` in its
`plugin.json`; the release number below is the marketplace's `metadata.version`.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Breaking changes

- **`code-review` renamed to `review`** (`review` 0.3.0), because the plugin now reviews the interface as well
  as the code. The install name changes, so a copy installed as `code-review@eurus-labs` stops updating.
  Reinstall with `copilot plugin install review@eurus-labs` (or `claude plugin install review@eurus-labs`) and
  remove the old one. The skills `review-code` and `setup-review-rules` keep their names.

### Added

- **`review-ui`** (`review` 0.3.0): review the interface a change produces from rendered screenshots, the DOM
  and styles, and the same screens on the base revision. It checks accessibility against WCAG 2.1 AA (with a
  measured contrast ratio, never an eyeballed one), consistency with the existing interface, clarity of
  wording and states, and unintended visual change, and ranks each finding by severity with the screen, the
  element, the criterion and who is affected. It reports and edits nothing. Trigger cases for it (two that
  must fire, one that must stay quiet). Not run yet.

### Changed

- **`coder-handoff`** (`reasoning` 0.3.0) always dispatches the plan to a model at least one tier below the
  planner's, from the allowed coders Sonnet, Haiku, terra and luna (the lowest tier hands off to itself). It
  learns the planner's model from the host or asks, stops when the host lacks the coder, asks before using a
  coder the user names that breaks the rule, and names both models in its report.
- **`document-codebase`** (`docs` 1.4.0) defines the Coordinator, Analyst, Writer and Reviewer roles, with a
  task contract for each and a Coordinator-only rule for shared files. The skill uses subagents only when the
  host offers them, records `independent` or `self_review` truthfully, routes each finding to the role that
  caused it, and states a stop rule that never becomes `confirmed`. Instructions only; no script changed.
  Immutable revision snapshots and resume are not implemented yet.
- **`document-codebase`** (`docs` 1.5.0) keeps every rendered draft as an immutable revision. `render` copies a
  changed draft to `.docs-build/drafts/rev-NNNN/` (an unchanged re-render reuses the latest; numbers are never
  reused; `--keep-revisions N`, default 5, minimum 3, prunes the oldest). The review queue's `draft_revision`
  now names that revision without making an approval stale, each review round's rows and prose report are kept
  in `drafts/rev-NNNN.meta/`, and the publish seal (`seal_version` 2) names one revision, so a draft
  re-rendered after review, or a snapshot edited afterwards, cannot be published. An existing version 1 seal is
  refused: run `review` again. A resume command is not implemented yet.
- **`review-code`** hands the rendered interface, accessibility and visual change to `review-ui`.
- Skills and READMEs in `development` (0.5.2), `reasoning` (0.2.2), `skill-authoring` (0.1.2), `testing`
  (0.3.6) and `verification` (0.3.1) name the `review` plugin where they named it by its old install name.
- **Skill manager** (contributor tool): the Install tab is now called Skills. A disabled plugin gets Enable
  in place of Update, there is an Uninstall all button, and a plugin installed from this marketplace that the
  checkout no longer has (such as the old `code-review`) gets a row with Uninstall.

## [0.3.0] — 2026-11-17

Adds the **`reasoning`** plugin for planning on a high-tier model and handing approved plans to a coder
subagent, and the contributor eval tooling.

### Breaking changes

- **`design-solution` moved** from `development` to the new `reasoning` plugin (`development` 0.4.0).
  `development` now holds only `implement`. If you used `design-solution`, install `reasoning@eurus-labs`.

### Added

- **`coder-handoff`** (`reasoning` 0.2.0): the second half of `write-plan`, as its own skill. When you approve
  a plan it sets `Status: approved` and pushes, then dispatches the plan to a subagent on the implementing
  model (for example the Agent tool with `model: sonnet` and `isolation: worktree` in Claude Code). The
  subagent's report returns to the planner directly. It reviews only when the plan says
  `Status: implemented`, opens the pull request when every acceptance criterion is met, and otherwise opens
  nothing and sends the gaps to a new subagent run. It merges only when you ask. A host that cannot start a
  subagent gets a stop and the instruction to run the plan with `implement`. Trigger cases for it (two that
  must fire, one that must stay quiet). Not run yet.
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
- **Skill manager** (for contributors): `python3 tools/skill_manager.py` serves one local page with two tabs.
  *Evals* shows each skill's goal, install state per host, eval coverage, latest results and a status, including
  "changed since last run", with search and status filters; a skill opens to a run-all bar and its cases, and a
  case opens in a side panel with its Run form. *Install* shows one platform at a time and installs, updates or
  removes plugins in Copilot CLI and Claude Code, with the buttons in fixed slots, and registers the
  marketplace. A run opens a Run view with progress, Stop, the grading question with Yes (✓), No (✕) and
  Skip (→), a tally of the answers, and the live output coloured by kind. The page opens a run's Markdown
  transcript as a readable page (roles, tool calls with folded arguments and output) that escapes everything the
  agent wrote. It listens on `127.0.0.1` with a token. The
  Copilot runner now asks `tool_used` graders as plain facts ("Did Copilot use the skill …?").
- **Copilot eval runner** (for contributors): `python3 tools/copilot_eval.py plugins/<plugin>` runs a plugin's
  eval cases on GitHub Copilot CLI, with and without the plugin, each in a fresh scaffolded workspace. It
  checks file graders itself, asks a person for the rest, and records the scores for the eval board.

- **`verification`** (0.1.3): five eval cases for the failures a pilot of the plugin found or could not
  exercise: a required check that cannot run (`fixtures/10`), tests skipped by default that hide a bug
  (`fixtures/11`), a required check already failing on `main` (`fixtures/12`), CI commands with shell pipes
  (`fixtures/13`), and a repository that already has its own verify skill (`fixtures/14`, triggering).
  Not run yet.

- **`reasoning` plugin** (0.1.0): planning skills for sessions on a high-tier model, meant to be loaded only in a
  planning session. The plugin cannot block a weaker model; where you install it decides who uses it.
  - **`write-plan`** (new): writes a plan to the repository's plan folder from a bundled template, on its
    own branch, with `Status: draft` until you approve it. It confirms before the first push and ends with a
    hand-off message: the branch, the plan path, and the baseline sha. Branch naming, commit identity, and
    commit format come from the target repository's own instructions.
  - **`design-solution`** moved here from `development`. It answers advice and comparison questions in the
    conversation; a saved design goes to the repository's plan folder instead of `docs/design/`.
  - Trigger eval cases for both skills, and one for `implement` on an approved plan. Not run yet.

### Changed

- **`write-plan`** (`reasoning` 0.2.0) ends at the draft: it no longer dispatches the plan, reviews the branch,
  or opens the pull request, and names `coder-handoff` for that. This replaces the separate-session hand-off
  and the cross-session messaging of its 0.1.0 hand-off.
- **`implement`** (`development` 0.5.0): on a handed-off plan its last commit changes only the plan's `Status`
  line to `implemented`, and its final report is the notice to the planning session; it no longer messages
  another session. It still never opens or merges a pull request on a handed-off plan.
- **For contributors:** `AGENTS.md`'s hand-off bullet and the plan template's `Status` line describe the
  subagent flow and who sets each `Status` value.
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
- **`implement`** (`development` 0.4.0) builds a plan document from `write-plan` safely: it starts only when
  `Status` is `approved`, works and commits on the plan's own branch, re-checks the plan's Baseline when the
  default branch has moved, follows the numbered Decisions as written, and stops to ask on a conflict with a
  Decision or the Scope.
  When another session hands it the plan, the message only points to it: `implement` reads the plan on the
  named branch, never merges or opens a pull request, changes no permissions or environments, asks the
  planning session only factual questions, and takes any change to a Decision or to Scope to you. When its
  work is pushed it tells the planning session the branch is ready for review. Used directly, it still opens
  a pull request only when you ask.
- **`write-plan`** (`reasoning` 0.1.0) finishes the hand-off: after you approve, it sends the hand-off to the
  implementer session you name through the host's messaging tool, or gives you the message to paste. When the
  implementer reports the branch ready, it reviews the branch against the plan's acceptance criteria and
  opens the pull request; it merges only when you ask. It never writes session ids into committed files.
- **For contributors:** the plan template moved from `doc/_plan-template.md` into
  `plugins/reasoning/skills/write-plan/references/plan-template.md`, generalized, and `AGENTS.md` points at it.

### Fixed

- **Commit identity is checked before every push** (`development` 0.5.1, `reasoning` 0.2.1). `implement`
  sets the author and committer explicitly on every commit, never changes the repository's configuration,
  and lists the author and committer of every commit it is about to push; on a mismatch it recommits first.
  `coder-handoff` puts the identity and that check in the subagent prompt and checks every commit's identity
  in its review, counting only the commits unique to the plan's branch. A commit already pushed with the
  wrong identity is reported as public, and it is rewritten with `--force-with-lease` on the plan's own
  unmerged branch only after you confirm. `design-solution` now sends hand-offs to `coder-handoff` instead of
  `write-plan`.

## [0.2.0] — 2026-11-09

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
