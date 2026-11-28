# Plan 27 — a VS Code extension: a skills store for everyone, the skill manager for contributors

Status: draft
Date: 2026-11-28
Branch: `feat/vscode-extension-skills-store`
Baseline: `origin/main` at `e9d9b439280c2248ce5d5a122ac787d3e53337a8` (marketplace 0.7.0)
Target: a new `extensions/vscode/`, a new `tools/build_catalog.py` and its generated `catalog.json`,
`tools/test_skill_manager.py`, `.github/workflows/validate.yml`, `.gitignore`, the docs

## Goal

Today there are two ways to browse this marketplace:

- **Plugin users** type `copilot plugin install <name>@eurus-labs` and read the root `README.md`.
- **Contributors** run `python3 tools/skill_manager.py`, which opens a page in a browser.

The user wants both inside VS Code (2026-11-28), and for both audiences:

- **A store**, for everyone. It shows every plugin as a card with its description, version, skills, eval
  score and install state, plus Install, Update, Enable and Uninstall buttons for Copilot CLI and Claude
  Code. It works without a checkout of this repository.
- **The skill manager**, for contributors. When the open folder is this repository, the extension opens the
  existing skill manager in an editor tab, so contributors get the evals, the runs and the transcripts.

A public web page that shows the same catalog is a separate plan, plan 28. It reads the `catalog.json` this
plan adds.

## Decisions

1. **The extension lives in `extensions/vscode/`** (the user's choice, 2026-11-28).
   - Rejected: a separate repository. The catalog and the skill manager live here, and one PR reviews both.
2. **Plain JavaScript (CommonJS), no build step and no runtime dependency.**
   - `package.json` lists no `dependencies` and no `devDependencies`, and no lockfile is committed.
   - Tests use Node's built-in `node:test` and `node:assert`.
   - Packaging runs `npx --yes @vscode/vsce@<exact version> package --skip-license`. The coder pins a version
     that exists on npm and is at least two weeks old.
   - `engines.vscode` is `^1.85.0`, which bundles Node 18, so the code uses nothing newer than Node 18.
   - Rejected: TypeScript with a bundler. That would add a compile step, `node_modules` and a lockfile to a
     repository that ships Markdown and stdlib Python. The extension is small enough not to need types.
3. **One generated, committed `catalog.json` at the repository root is the store's data.**
   - `tools/build_catalog.py` writes it. The tool is stdlib-only and reuses `build_eval_board.catalog()` and
     `build_eval_board.load_results()`. It does not re-implement manifest reading or scoring.
   - `--check` writes nothing. It exits 1 when the file is out of date and prints the command that fixes it.
     A `tools/test_build_catalog.py` runs `--check` on the repository, so CI catches a forgotten rebuild, as
     it does for `materialize.py`.
   - The file is built from the archive only (`plugins/*/evals/archive/`), never from the git-ignored
     `results/`. A clean checkout then gives the same bytes on every machine.
   - The file holds no generation time, so rebuilding unchanged inputs changes nothing.
   - `tools/archive_eval_results.py` runs the build at the end of a successful archive. That way, archiving a
     run never leaves the catalog behind.
   - Rejected: the extension reading the raw manifests from GitHub. That is about 30 requests per refresh,
     and it would repeat the scoring in JavaScript.
   - Rejected: building the catalog only in CI. That needs a publishing target first (plan 28), and a
     contributor could not see the result locally.
4. **The `catalog.json` format (schemaVersion 1):**

   ```json
   {
     "schemaVersion": 1,
     "marketplace": {"name": "eurus-labs", "version": "0.7.0", "source": "eurus-labs/Skills"},
     "hosts": [{"id": "copilot", "label": "Copilot CLI"}, {"id": "claude", "label": "Claude Code"}],
     "plugins": [{
       "name": "planning", "version": "0.1.0", "description": "<marketplace.json description>",
       "skills": [{
         "name": "analyze-requirements", "description": "<short description, as the board shows it>",
         "evals": {
           "cases": 4,
           "hosts": {"claude": {"cases": 4, "score": 0.83, "latest": "<newest stamp>"}}
         }
       }]
     }]
   }
   ```

   - `hosts` comes from `build_eval_board.HOSTS`, without `exe`.
   - **How `evals.hosts.<host>` is counted.** For each case tied to the skill (`case["skills"]`), take the
     newest run on that host that is trusted (`build_eval_board.trusted`).
     - `cases` is how many cases have such a run.
     - `score` is the mean of their scores, rounded to two decimals.
     - `latest` is the newest of their stamps.
   - A host with no trusted run is left out.
   - Plugins and skills keep the marketplace and manifest order. JSON is written with sorted keys, 2-space
     indentation and a final newline.
5. **Where the store gets its data.**
   - **The open folder is this repository.** It reads that folder's `catalog.json`, so a contributor sees
     their branch.
   - **Any other folder.** It fetches `https://raw.githubusercontent.com/eurus-labs/Skills/main/catalog.json`.
     The setting `eurusSkills.catalogUrl` can change this URL, but only to an `https://` URL.
   - **Validating the data.** A fetched file over 1 MB, one that is not schemaVersion 1, or one with a plugin
     or host name that does not match `^[a-z0-9][a-z0-9-]*$` is rejected. The store then says why.
   - **Offline.** The last good copy is kept in `globalState` and shown with its date.
   - **What "this repository" means.** The workspace folder holds `tools/skill_manager.py` and a
     `.github/plugin/marketplace.json` whose `name` is `eurus-labs`.
   - The extension sends no telemetry and makes no other network call.
6. **The store is a sidebar webview** (an Activity Bar icon, "Eurus Skills").
   - It shows a search box, a host switch (Copilot CLI / Claude Code), and one card per plugin.
   - A card shows the name, version, description and eval summary, plus one action button.
   - The card opens to show its skills, each with its description and its eval summary for the chosen host.
   - It follows the editor's theme through the `--vscode-*` CSS variables.
   - Rejected: a TreeView. It cannot show descriptions, scores and buttons together on one card.
7. **Install state and actions use the same CLI commands as `tools/skill_manager.py` `plugin_command`.**
   - **Install state.** The store calls `<exe> plugin list --json` and `<exe> plugin marketplace list --json`
     through `child_process.execFile`, with no shell and a 60-second timeout. It reads them as
     `skill_manager.installed()` does.
   - **The button.** It is Install (not installed), Update (installed version ≠ catalog version), Enable
     (disabled), or Uninstall (offered beside Update or Enable, and alone when up to date).
   - **When the marketplace is not registered**, a banner offers "Register marketplace" from `eurus-labs/Skills`.
     In this repository, it also offers "from this checkout".
   - **A host whose executable is not on PATH** shows its buttons disabled, with the reason.
   - **Running an action.** Each action asks for confirmation in a modal, because it changes the host's
     configuration. It then runs in a VS Code terminal created with `shellPath` set to the executable and
     `shellArgs` set to the arguments, so no shell parses them. The user sees the output and can answer
     prompts. When that terminal closes, the install state refreshes.
   - **Every argument is validated** before use. The plugin must be in the loaded catalog (or, for Enable and
     Uninstall, listed by the host), the host must be in `hosts`, and the action must be one of the six.
   - **One shared table keeps the two in step.** `extensions/vscode/test/commands.json` maps each
     `(host, action)` to its argument list. A new case in `tools/test_skill_manager.py` checks
     `plugin_command` against it, and a Node test checks the extension against it.
   - Rejected: running actions through `skill_manager.py`. Plugin users have no checkout and no script.
8. **The skill manager opens in an editor tab, and only in this repository.**
   - **The command.** "Eurus Skills: Open skill manager" is visible only when the `eurusSkills.inRepo`
     context key is set.
   - **Starting it.** It starts `<eurusSkills.python> -u tools/skill_manager.py --no-open`, with the repository
     as cwd. `eurusSkills.python` defaults to `python3`, and `-u` stops stdout from being buffered.
   - **Reading the URL.** It waits up to 15 seconds for the line
     `Skill manager: http://127.0.0.1:<port>/?token=<token>`. It accepts only that host.
   - **Showing it.** It shows the page in a webview panel as a full-size iframe, whose CSP allows `frame-src`
     only for that origin.
   - **The toolbar.** It has "Open in browser" (`vscode.env.openExternal`), for transcripts and new windows the
     iframe cannot open, and "Restart".
   - **Stopping.** Closing the panel, or deactivating the extension, stops the process.
   - **Logging.** The output channel logs the process output with the token replaced by `…`.
   - **On failure.** If Python is missing or the URL never appears, an error names the setting and shows the
     last output lines.
   - **Remote workspaces** (SSH, WSL, Codespaces) are out of scope. There, the command says to run the skill
     manager in a terminal instead, because the manager accepts only Host `127.0.0.1` or `localhost`.
   - Rejected: rewriting the eval UI in the extension. That would duplicate about 1,800 lines of
     `skill_manager.py` and `build_eval_board.py`, and the two copies would drift.
9. **Webview safety.**
   - **CSP.** Both webviews use `default-src 'none'`, scripts only with a per-load nonce, and styles from
     `webview.cspSource`.
   - **Text.** All catalog text is inserted as escaped text, never as HTML.
   - **Messages.** A message from the webview is an untrusted request: the host side re-validates it as
     Decision 7 says.
10. **No publishing.**
    - The extension is packaged as a `.vsix`, which is git-ignored.
    - The user attaches it to a GitHub Release, and people install it with
      `code --install-extension eurus-skills-<version>.vsix`.
    - `package.json` sets `"publisher": "eurus-labs"`, `"name": "eurus-skills"` and `"version": "0.1.0"`. The
      extension's version is its own, separate from the marketplace's.
    - Rejected: the VS Code Marketplace. The user did not choose it, and it needs a publisher account and a
      token that only the user can create.
11. **CI.**
    - A new `extension` job in `validate.yml` runs `node --test extensions/vscode/test/` on Node 18 and on
      Node 22, through `actions/setup-node`.
    - `verify` needs both `validate` and `extension`, and checks that both succeeded. The required check
      keeps its name.
    - The Python job already runs every `tools/test_*.py`, which includes `test_build_catalog.py`.
12. **Docs.**
    - `extensions/vscode/README.md`: what it does, how to install the `.vsix`, where the data comes from, the
      one network call, the settings, and how to package it.
    - The root `README.md`: a short "VS Code extension" section.
    - `CONTRIBUTING.md`: rebuild `catalog.json` after changing a skill description, a version or the
      archive, and run the extension tests.
    - `AGENTS.md`: one line under "This Repository", noting that `extensions/vscode/` is the only JavaScript
      and has no dependencies. The file stays under 120 lines.
    - `CHANGELOG.md` `[Unreleased]`, under `### Added`: the extension and `catalog.json`.
    - No plugin version changes.

## Scope

In:

- `extensions/vscode/`:
  - `package.json`, `README.md`, `.vscodeignore`, `media/` (one SVG icon);
  - `src/extension.js`, the `vscode` glue;
  - pure modules that do not import `vscode`, so `node --test` can load them:
    - `src/catalog.js`: validates the catalog and merges it with the install state into rows;
    - `src/commands.js`: builds and validates arguments;
    - `src/manager.js`: parses the URL line and masks the token;
    - `src/html.js`: escapes text and renders the store with a nonce;
  - `test/*.test.js` and `test/commands.json`.
- `tools/build_catalog.py`, `tools/test_build_catalog.py`, the generated `catalog.json`.
- `tools/archive_eval_results.py`: runs the catalog build after a successful archive. Its test covers this.
- `tools/test_skill_manager.py`: one case against `commands.json`.
- `.github/workflows/validate.yml`, `.gitignore` (`*.vsix`, `node_modules/`).
- `README.md`, `CONTRIBUTING.md`, `AGENTS.md` (one line), `CHANGELOG.md`.

Out:

- **The public web page.** That is plan 28.
- **Publishing to the VS Code Marketplace**, and an extension for JetBrains.
- **Remote workspaces** for the skill manager tab.
- **Any change to `skill_manager.py` behavior, or to `build_eval_board.py`.** The board's output stays as it
  is.
- **Editing skills from the extension.**
- **Any plugin or skill.**

## Baseline

| Existing | Keep, change, or remove |
| --- | --- |
| `tools/build_eval_board.py:123` `catalog()`, `:172` `load_results()`, `:219` `trusted()`, `:224` `result_files()`, `:239` `HOSTS` | Reuse from `build_catalog.py`; unchanged |
| `tools/skill_manager.py:245` `plugin_command`, `:286` `installed()` | Keep; the extension mirrors them, and `commands.json` pins both |
| `tools/skill_manager.py:704` prints `Skill manager: <url>` | Keep; the extension parses this line |
| `tools/skill_manager.py:593` Host check (127.0.0.1 or localhost only) | Keep; it is why remote workspaces are out of scope |
| `tools/archive_eval_results.py` | Add the catalog build at the end of a successful archive |
| `.github/workflows/validate.yml` `verify` job, the one required check | Add `extension` to its `needs` |
| `.github/plugin/marketplace.json` `name`, `metadata.version`, plugin `description` | Read by `build_catalog.py` |
| No `LICENSE` file in the repository | Hence `vsce package --skip-license` |

## Tech stack and constraints

Default for Python: stdlib-only, Python 3.9 or later.

The deviation, which the user asked for on 2026-11-28, is JavaScript for the VS Code extension. It runs on
Node 18 or later, has no dependencies, and has no build step. The tests need Node only. `vsce` runs through
`npx` for packaging and is never a dependency.

## Acceptance criteria

- [ ] **The catalog is complete.** `python3 tools/build_catalog.py` writes `catalog.json`, and this prints
      `9 18`:

      ```bash
      python3 -c "import json;d=json.load(open('catalog.json'));print(len(d['plugins']),sum(len(p['skills']) for p in d['plugins']))"
      ```

- [ ] **The catalog is reproducible.** On a clean checkout, `python3 tools/build_catalog.py --check` exits 0.
      Running the build twice changes no bytes. Checked by `tools/test_build_catalog.py`.
- [ ] **Failure: a stale catalog is caught.**
  - With a skill description changed in a temporary copy, `--check` exits 1 and prints
    `python3 tools/build_catalog.py`.
  - A run placed only in `results/` does not change the output.

  Checked by `tools/test_build_catalog.py`.
- [ ] **Scores are counted as Decision 4 says.** A fixture archive gives a known `cases`, `score` and
      `latest`. An untrusted run (partial, errored, or with skipped paid graders) is ignored. Checked by
      `tools/test_build_catalog.py`.
- [ ] **Archiving rebuilds the catalog.** Checked by `tools/test_archive_eval_results.py`.
- [ ] **The two command builders agree.** `python3 tools/test_skill_manager.py` and
      `node --test extensions/vscode/test/` both pass against `test/commands.json`.
- [ ] **Failure cases in the extension**, each with a Node test:
  - The catalog is rejected when it is over 1 MB, has another schemaVersion, or has a plugin named
    `a;rm -rf` or `../x`.
  - Arguments are refused for a plugin not in the catalog, an unknown host, or an unknown action.
  - A description holding `<script>` renders as text.
  - The URL parser rejects `http://example.com:1/?token=x` and a line without a token.
  - The masked log contains no token.
  - The buttons are right for four cases: not installed, an older version, disabled, and up to date.
- [ ] **It packages.**

      ```bash
      cd extensions/vscode && npx --yes @vscode/vsce@<pinned> package --skip-license --out /tmp/eurus-skills.vsix
      ```

  This succeeds with no prompt, and `unzip -l /tmp/eurus-skills.vsix` lists no `test/` file.
- [ ] **CI runs it.** `validate.yml` has the `extension` job on Node 18 and 22, and `verify` needs it.
- [ ] **The required checks pass:**
  - `python3 tools/validate.py`
  - `python3 tools/materialize.py --check`
  - `python3 tools/build_eval_scaffolds.py --check`
  - `python3 tools/archive_eval_results.py --check`
  - `python3 tools/build_catalog.py --check`
  - `for t in tools/test_*.py; do python3 "$t" || break; done`
  - `node --test extensions/vscode/test/`

**Not verifiable in the coder's container**, because it has no VS Code. The user checks these after
installing the `.vsix`, and the README lists the steps:

- the sidebar shows 9 cards;
- Install works in a terminal;
- the skill manager tab opens in this repository and stays hidden elsewhere.

## Risks

| Risk | How it is handled |
| --- | --- |
| `catalog.json` goes stale after a skill edit | `--check` in the tests and CI, and the message names the fix command; archiving rebuilds it |
| The extension's commands drift from `skill_manager.py` | The shared `commands.json`, checked from both sides |
| A fetched catalog injects HTML or a shell argument | Strict schema and name regex, escaped text, CSP with a nonce, `shellPath`/`shellArgs` with no shell, re-validation on the host side |
| The iframe cannot open transcripts or new windows | "Open in browser" on the panel toolbar |
| Python buffers stdout, so the URL never appears | `-u`, plus a 15-second timeout with the last output shown |
| A leaked skill manager token | It stays in the webview, is masked in the log, and the server listens on 127.0.0.1 only |
| The store shows `main` while the user installed an older release | The card compares the installed and catalog versions and offers Update; the catalog shows the marketplace version |
| Node 18 lacks an API the code uses | CI runs the tests on Node 18 |

## Open questions

None.
