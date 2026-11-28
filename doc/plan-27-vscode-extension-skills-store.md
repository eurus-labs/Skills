# Plan 27 — a VS Code extension: a skills store for everyone, eval runs for contributors

Status: draft
Date: 2026-11-28
Branch: `feat/vscode-extension-skills-store`
Baseline: `origin/main` at `e9d9b439280c2248ce5d5a122ac787d3e53337a8` (marketplace 0.7.0)
Target: a new `extensions/vscode/`; a new `tools/build_catalog.py` with its generated `catalog.json` and its
input `tools/featured.json`; one new endpoint in `tools/skill_manager.py`; the tests, CI, `.gitignore` and docs

## Goal

Today this marketplace has two separate faces:

- **Plugin users** type `copilot plugin install <name>@eurus-labs` and read the root `README.md`.
- **Contributors** run `python3 tools/skill_manager.py`, which opens a page in a browser.

The user wants one VS Code extension for both (2026-11-28), and has approved a design for it.

- **A store, for everyone.** A sidebar lists every plugin. Each plugin opens a page in the editor with its
  description, install state per host, eval score, skills and archived runs. The user installs, updates,
  enables and uninstalls from there, for Copilot CLI and Claude Code. It works without a checkout of this
  repository.
- **Eval runs, for contributors.** When the open folder is this repository, the same plugin page lists each
  skill's eval cases. A contributor runs a case, a skill or the whole plugin, answers grading questions, stops
  a run and opens transcripts there. Behind it, `tools/skill_manager.py` does the running, unchanged except for
  one read-only endpoint. The extension has no separate skill manager tab.

A public web page that shows the same catalog is a separate plan, plan 28. It reads the `catalog.json` this
plan adds.

## Decisions

1. **The extension lives in `extensions/vscode/`** (the user's choice, 2026-11-28).
   - Rejected: a separate repository. The catalog and the eval runner live here, and one PR reviews both.

2. **Plain JavaScript (CommonJS), no build step and no runtime dependency.**
   - `package.json` lists no `dependencies` and no `devDependencies`, and no lockfile is committed.
   - Tests use Node's built-in `node:test`, `node:assert` and `node:http`.
   - Packaging runs `npx --yes @vscode/vsce@<exact version> package --skip-license`. The coder pins a version
     that exists on npm and is at least two weeks old. The repository has no `LICENSE` file, hence
     `--skip-license`.
   - `engines.vscode` is `^1.85.0`, which bundles Node 18, so the code uses nothing newer than Node 18.
   - `extensionKind` is `["workspace"]`, so in a remote workspace the extension runs next to the files and
     next to Python.
   - Rejected: TypeScript with a bundler. That would add a compile step, `node_modules` and a lockfile to a
     repository that ships Markdown and stdlib Python.

3. **The data is one schema, served from two places. The scoring is in Python only.**
   - `tools/build_catalog.py` (stdlib only) builds the catalog. It reuses `build_eval_board.catalog()`,
     `load_results()`, `trusted()`, `result_files()` and `HOSTS`, and re-implements no manifest reading or
     scoring.
   - `python3 tools/build_catalog.py` writes the committed `catalog.json` at the repository root, **from
     `plugins/*/evals/archive/` only**, so a clean checkout gives the same bytes on every machine. The file
     holds no generation time. JSON is written with sorted keys, 2-space indentation and a final newline.
   - `--check` writes nothing. It exits 1 when `catalog.json` is out of date and prints
     `python3 tools/build_catalog.py`. `tools/test_build_catalog.py` runs it on the repository, so CI catches a
     forgotten rebuild, as it does for `materialize.py`.
   - `tools/archive_eval_results.py` runs the build at the end of a successful archive.
   - **The one change to `tools/skill_manager.py`** is a new `GET /api/catalog`. It returns the same schema
     built from `results/` *and* `archive/`, so a run finished a moment ago shows up. It uses the same token
     and Host checks as every other `/api/` route.
   - Rejected: scoring in JavaScript. Two copies of the rules would drift.
   - Rejected: building the catalog only in CI. A contributor could not see it locally, and plan 28 has no
     host yet.

4. **The schema, `schemaVersion: 1`:**

   ```json
   {
     "schemaVersion": 1,
     "marketplace": {"name": "eurus-labs", "version": "0.7.0", "source": "eurus-labs/Skills"},
     "hosts": [{"id": "copilot", "label": "Copilot CLI"}, {"id": "claude", "label": "Claude Code"}],
     "featured": {"plugin": "planning", "note": "New in 0.6.0", "text": "From a requirement to epics, with one living DoU for the Product Owner."},
     "plugins": [{
       "name": "planning", "version": "0.1.0", "description": "<its marketplace.json description>",
       "skills": [{
         "name": "analyze-requirements", "description": "<short description, as the board shows it>",
         "evals": {"cases": 4, "hosts": {"claude": {"cases": 4, "score": 0.98, "latest": "<stamp>"}}}
       }],
       "cases": [{
         "name": "analyze-requirements-compare-versions", "kind": "fires", "skills": ["analyze-requirements"],
         "description": "<prompt.md description>",
         "latest": {"claude": {"stamp": "<stamp>", "score": 1.0, "runs": 3, "trusted": true}}
       }],
       "runs": [{"stamp": "<stamp>", "host": "claude", "score": 0.69, "cases": 4}]
     }]
   }
   ```

   - **`hosts`** comes from `build_eval_board.HOSTS`, without `exe`.
   - **`featured`** comes from `tools/featured.json`, which has the same three keys. If the file is missing,
     `featured` is `null`. A `featured.plugin` that is not in the marketplace fails the build, with the reason
     printed.
   - **`skills[].evals.hosts.<host>`**: for each case tied to the skill (`case["skills"]`), take the newest
     trusted run on that host.
     - `cases` is how many cases have one.
     - `score` is the mean of their scores, rounded to two decimals.
     - `latest` is the newest of their stamps.

     A host with no trusted run is left out.
   - **`cases[].kind`**:
     - `fires` is a trigger case whose graders require the skill;
     - `quiet` is a trigger case whose graders forbid it;
     - `behavior` is any case under `evals/behavior/`.

     `cases[].latest.<host>` is the newest run of that case on that host, trusted or not, with `trusted` set
     by `build_eval_board.trusted`.
   - **`runs`**: one entry per result file of the plugin, oldest first.
     - `score` is the mean of the non-null case scores in that file, rounded to two decimals.
     - `cases` is how many cases it scored.
   - Plugins, skills and cases keep the marketplace, manifest and folder order.

5. **Where the extension gets its data.**
   - **The open folder is this repository.** The workspace folder holds `tools/skill_manager.py` and a
     `.github/plugin/marketplace.json` whose `name` is `eurus-labs`.
     - It calls `GET /api/catalog` of the running engine (Decision 9).
     - While the engine is not running, or cannot start, it reads that folder's `catalog.json` instead.
   - **Any other folder.** It fetches `https://raw.githubusercontent.com/eurus-labs/Skills/main/catalog.json`.
     - The setting `eurusSkills.catalogUrl` can change this URL, but only to an `https://` URL.
     - The last good copy is kept in `globalState` and shown with its date when offline.
   - **Validation, before anything is drawn.** A catalog is rejected when:
     - it is over 1 MB;
     - its `schemaVersion` is not 1;
     - a plugin, case or host name does not match `^[a-z0-9][a-z0-9-]*$`.
   - The extension sends no telemetry and makes no other network call.

6. **Two surfaces: a sidebar store and a plugin page.**
   - **Sidebar.** A `WebviewView` in its own Activity Bar container, "Eurus Skills". From top to bottom:
     1. the title row with Refresh;
     2. the search field (`/` focuses it, and its hint shows `/`), which matches plugin names, descriptions
        and skill names;
     3. a host switch (Copilot CLI / Claude Code), which decides the install state and scores shown in the
        list;
     4. the featured card, drawn from `featured`, with a dot-grid background and the note as a small badge;
        hidden while searching or filtering;
     5. filter tabs **All / Installed / Updates**, each with a count. The Updates count is filled when it is
        not zero;
     6. an **Update all** strip when updates exist for the chosen host;
     7. the list. Each row has the plugin mark (Decision 11), the name, a line with
        "N skills · vX" (or "vA → vB" for an update, or "Disabled"), and on the right one of:
        - a **Get** pill (not installed);
        - an **Update** pill, filled;
        - an **Enable** pill;
        - the eval score in its score color (installed and up to date).

        Rows are ordered by updates, then disabled, then installed, then not installed. The selected row is
        raised with a hairline and a soft shadow;
     8. the footer: the catalog source ("Catalog from this checkout" or "Catalog from GitHub · <date>") and
        the marketplace version.
   - **Plugin page.** One `WebviewPanel` in the editor, reused when another plugin is opened, titled with the
     plugin name. From top to bottom:
     1. **The hero.** A band with a dot-grid background, holding:
        - the large plugin mark, raised;
        - the line "eurus-labs · vX · README · Changelog", with links to the plugin folder and `CHANGELOG.md`
          on GitHub;
        - the name at 40 px;
        - the description;
        - one **status pill** per host where it is present: "● Installed in Claude Code", or "Update
          available in …", or "Disabled in …".

        On the right is a **split button**. Its main part runs the pending action for the chosen host, else
        for the other one: "Install in Copilot CLI", "Update in …", or "Enable in …". With nothing pending it
        reads "Up to date everywhere" and does nothing. Its arrow opens a menu with every action for both
        hosts, Uninstall included. Under it: "Runs in a terminal · you confirm first".
     2. **The eval row.** An "Eval on" host switch, independent of the sidebar's, plus **How scores work**,
        which opens a short explanation. Then four stat cards:
        - **Eval score**, with a ring;
        - **Cases run** "N / total", noting "trusted runs only";
        - **Last run**, with the run count;
        - **Skills**.

        With no run on that host, one dashed panel replaces the four cards and says so.
     3. **A card with tabs: Skills / Runs / Install**, each with a count.
        - **Skills.** One row per skill: the name in monospace, the description, a score bar with the
          percentage, and "N/total · date". A skill with fewer than 3 cases on that host is marked "low
          confidence" in the warning color.
        - **Runs.** A column chart of the plugin's `runs`, oldest first. Bar height is the score, bar color is
          the score color, and each bar is labelled with the percentage, the date with its number and its case
          count. The note under it says that one run may cover only a few cases, so one bar is not the
          plugin's score.
        - **Install.** One row per host: name, status, and the exact command. Two fixed button slots: the left
          slot is Uninstall (or empty), the right slot is Install, Update or Enable (or "✓ Up to date").
   - Rejected: expanding cards inside the sidebar. There is not enough room for stats and tabs.
   - Rejected: a TreeView. It cannot show descriptions, scores and buttons together.

7. **Install actions use the same CLI commands as `tools/skill_manager.py` `plugin_command`.**
   - **Install state.** It comes from `<exe> plugin list --json` and `<exe> plugin marketplace list --json`,
     run through `child_process.execFile` with no shell and a 60-second timeout, and read as
     `skill_manager.installed()` reads them. When the marketplace is missing, or the host's executable is not
     on PATH, the setup states of Decision 13 apply.
   - **The command runs in a VS Code terminal** created with `shellPath` set to the executable and `shellArgs`
     set to the arguments, so no shell parses them. When that terminal closes, the install state refreshes.
   - **Confirmation.** Every action asks first, in a modal dialog in the webview. The dialog shows the exact
     command or commands, with "Cancel" and the verb ("Install", or "Update all" for several).
     - The dialog for install, update and enable has a **Don't ask again** box, which sets
       `eurusSkills.confirmInstalls` to `false`.
     - Uninstall always asks, and its button uses the danger color.
   - **Validation.** Every argument is checked on the extension host before use:
     - the plugin must be in the loaded catalog (or, for Enable and Uninstall, listed by the host);
     - the host must be in `hosts`;
     - the action must be one of the six.
   - **One shared table keeps the two in step.** `extensions/vscode/test/commands.json` maps each
     `(host, action)` to its argument list. A new case in `tools/test_skill_manager.py` checks `plugin_command`
     against it, and a Node test checks the extension against it.
   - Rejected: installing through `skill_manager.py`'s `/api/install`. Plugin users have no checkout, and two
     install paths would differ.

8. **The contributor surface lives in the Skills tab.** It is shown only in this repository.
   - **Above the rows:**
     - a "Contributor" badge;
     - the case counts ("7 must fire · 3 must stay quiet · 3 behavior");
     - **Run all N cases**.
   - **Each skill row gets a chevron.** It opens the skill's cases, in an inset panel with
     "N eval cases on <host>" and **Run N cases**. Each case row shows:
     - a kind badge: *Must fire* (neutral), *Must stay quiet* (outlined) or *Behavior* (filled);
     - the case name in monospace, and its description;
     - the newest result on the chosen host: the percentage in its score color, "3 runs · date", or "partial"
       or "error" when it is not trusted;
     - a **Run** button.
   - **Running.** Every Run asks first, in the same dialog.
     - For Claude Code it says "Billed to your Claude key, with a $N ceiling". N is `eurusSkills.evalMaxCostUsd`,
       2 by default, and must be over 0 and at most 50, as the server requires.
     - For Copilot CLI it says "Billed to your Copilot plan".
     - Both add: "The agent runs commands in a scratch workspace as you. You may be asked to grade some runs."
     - The dialog shows the command the engine will run. It has no "Don't ask again".
   - **The Eval run tray** opens at the bottom of the plugin page:
     - "EVAL RUN", the title, the host, "k of n";
     - Stop while it runs, and Close;
     - a thin progress bar;
     - on the left, the cases with ○ queued, ● running (pulsing), ✓ passed, ✗ failed, – stopped, the score of
       each finished case, and a **Transcript** link;
     - on the right, the live output, and when the engine asks, a **"Waiting for you"** card with the
       question and one button per choice (Yes, No, Skip for `y/n/s`).
     - While a run is in progress, Run buttons are disabled with "…", because the engine runs one job at a
       time.
   - Rejected: a separate skill manager tab that embeds the old page. Its plugin list and install buttons
     repeat the store's, which is what the user objected to (2026-11-28).
   - Rejected: rewriting the runner in JavaScript. About 1,800 lines would be duplicated.

9. **The eval engine is `tools/skill_manager.py`, run headless and driven from the extension host.**
   - **Starting it.** On the first contributor action, the extension starts
     `<eurusSkills.python> -u tools/skill_manager.py --no-open`, with the repository as cwd.
     `eurusSkills.python` defaults to `python3`, and `-u` stops stdout from being buffered.
   - **Reading the URL.** It waits up to 15 seconds for the line
     `Skill manager: http://127.0.0.1:<port>/?token=<token>`, and accepts only that host.
   - **Calling it.** The extension host calls the API with Node `http`, sending `X-Board-Token`:
     - `GET /api/catalog` (new), `GET /api/job`;
     - `POST /api/run` with `{plugin, cases, host, arms: "both", max_cost_usd}`;
     - `POST /api/answer` with `{id, reply}`;
     - `POST /api/stop`.
   - **The token never reaches a webview.** The webview sends messages to the extension host, which
     re-validates them as in Decision 7 and calls the API.
   - **Polling.** It polls `/api/job` every second while a job runs, and `/api/catalog` every 5 seconds while
     the plugin page is visible.
   - **Transcripts.** Their paths come from the job log lines `transcript file: <path>`, as the existing page
     reads them. A path must match the regex of `skill_manager.transcript_path`. It is opened as a file in the
     editor (`.md` in Markdown preview).
   - **Stopping.** Deactivating the extension stops the process.
   - **Logging.** The output channel "Eurus Skills" logs the engine's output with the token replaced by `…`.
   - **Open skill manager in browser** stays available as a command, for anything the plugin page does not
     show.
   - **Remote workspaces** should work, because the extension and the engine run on the same side. They are
     not verified (Acceptance criteria).

10. **Look and themes.** The approved design is named "Combined". It takes its layout from direction A, its
    stats and tabs from direction B, and its warmth from direction C.
    - The extension ships three palettes of its own. `eurusSkills.theme` is `stone` (the default, the user's
      choice), `charcoal` or `black`.
    - In a high-contrast VS Code theme, the setting is ignored and every role reads the matching `--vscode-*`
      variable instead.
    - Fonts are `--vscode-font-family` and `--vscode-editor-font-family`. No font is bundled.
    - Corners are 6 px for controls, 8–10 px for rows and pills, and 12–16 px for cards and the dialog.
    - Buttons are 24–28 px in lists and 30–40 px elsewhere.
    - Color means something or is not used:
      - the accent marks the primary action;
      - green, amber and red are scores and states only;
      - plugins have no color of their own.

    | Role | stone | charcoal | black |
    | --- | --- | --- | --- |
    | page | `#f1eee8` | `#1b1916` | `#0a0a0a` |
    | chrome (tabs, title, activity) | `#e6e2da` | `#141210` | `#000000` |
    | sidebar and hero band | `#ebe7df` | `#181613` | `#0f0f0f` |
    | card | `#f8f6f1` | `#221f1b` | `#141414` |
    | raised (inputs, tiles, dialog) | `#fdfcfa` | `#2a2722` | `#1c1c1c` |
    | hairline | `rgba(60,50,35,.10)` | `rgba(255,240,220,.08)` | `rgba(255,255,255,.08)` |
    | strong hairline | `rgba(60,50,35,.18)` | `rgba(255,240,220,.15)` | `rgba(255,255,255,.15)` |
    | input border | `rgba(60,50,35,.50)` | `rgba(255,240,220,.38)` | `rgba(255,255,255,.36)` |
    | dot grid | `rgba(60,50,35,.13)` | `rgba(255,240,220,.09)` | `rgba(255,255,255,.08)` |
    | text | `#1f1d1a` | `#f2ede4` | `#f5f5f5` |
    | secondary text | `#5f5a52` | `#b0a898` | `#a3a3a3` |
    | primary button, and its text | `#1f1d1a` / `#fbfaf7` | `#f2ede4` / `#1b1916` | `#f5f5f5` / `#0a0a0a` |
    | score 90 % and up | `#2f7d4f` | `#5cc28a` | `#52c98a` |
    | score 60–89 %, warning | `#a35c0a` | `#e0a64a` | `#e8a838` |
    | score under 60 %, error | `#c0392b` | `#ef6a5a` | `#f26b5b` |
    | danger button, and its text | `#b93a2c` / `#ffffff` | `#b93a2c` / `#ffffff` | `#b93a2c` / `#ffffff` |

    - Rejected: following the VS Code theme's colors only. The user found it plain.
    - Rejected: bundling Inter. That adds binary assets and a font licence.

11. **Plugin marks are generated.** A new plugin needs no artwork.
    - The mark is two characters: the first letter in upper case and the next consonant (`planning` → `Pl`,
      `testing` → `Ts`, `review` → `Rv`), or the initials of a hyphenated name (`skill-authoring` → `SA`).
    - It is set in the editor font, on a neutral raised tile with a strong hairline.
    - Rejected: an icon per plugin (the user, 2026-11-28: every new plugin would need one).
    - Rejected: a color per plugin (the user found it ugly).

12. **Score rules shown to users.**
    - Score colors: 90 % and up is green, 60–89 % is amber, under 60 % is red.
    - Fewer than 3 cases is "low confidence".
    - **How scores work** says: "An eval runs a skill on fixed test prompts and grades what the agent did. The
      score is the mean over the skill's cases, each from its newest finished run on the chosen host. Fewer
      than 3 cases is marked low confidence. Runs that stopped early or errored are not counted."

13. **Setup and failure states.** Each one says what happened and gives one next step.
    1. **Marketplace not registered**, per host. A card: "Connect <host> to eurus-labs. One-time setup.
       Afterwards every plugin installs with one click."
       - Buttons: **Register from GitHub**, and **Use this checkout** (only in this repository).
       - The command is shown under them.
       - Get pills are disabled, with "Register first to install".
    2. **Host not on PATH.** A notice: "`<exe>` is not on PATH. Install <host>, then refresh. The catalog and
       <other host> keep working." Rows read "Install state unknown". Install buttons for that host are
       disabled.
    3. **Offline.** A warning card: "Showing the catalog from <date>. GitHub could not be reached. Install
       state is live; versions may be behind." With **Try again**.
    4. **Catalog rejected.** An error card that names the reason, for example "Plugin name `a;rm -rf` is not
       allowed", and says "Still showing the catalog from <date>". With **Try again** and **Settings**.
    5. **The eval engine did not start**, for contributors. Three causes:
       - `python3` is not found;
       - no URL appears within 15 s;
       - the engine exits while a run is open.

       An error card in the Skills tab names the cause and says that archived scores still show. Buttons:
       **Open setting** (`eurusSkills.python`) and **Retry**. The last output lines are in the output channel.
    6. **A run failed or was stopped**, for contributors. The tray keeps the finished cases, and shows an error
       card with the engine's exit message. For a refused folder, the card says: "If it says the folder is not
       trusted, run it once in a terminal and answer the prompt. The extension never passes --trust-plugin."
       Buttons: **Show output** and **Run the rest**.

14. **Webview safety.**
    - **CSP.** Both webviews use `default-src 'none'`, scripts only with a per-load nonce, and styles from
      `webview.cspSource` with a nonce.
    - **Text.** All catalog, case, log and question text is inserted as escaped text, never as HTML.
    - **Messages.** A message from a webview is an untrusted request. The extension host re-validates it
      (Decisions 7 and 9).

15. **No publishing.**
    - The extension is packaged as a `.vsix`, which is git-ignored.
    - The user attaches it to a GitHub Release, and people install it with
      `code --install-extension eurus-skills-<version>.vsix`.
    - `package.json` sets `"publisher": "eurus-labs"`, `"name": "eurus-skills"`, `"displayName": "Eurus Skills"`
      and `"version": "0.1.0"`. The extension's version is its own.
    - Rejected: the VS Code Marketplace. The user did not choose it, and it needs a publisher account and a
      token that only the user can create.

16. **CI.**
    - A new `extension` job in `validate.yml` runs `node --test extensions/vscode/test/` on Node 18 and on
      Node 22, through `actions/setup-node`.
    - `verify` needs both `validate` and `extension`, and checks that both succeeded. The required check keeps
      its name.
    - The Python job already runs every `tools/test_*.py`.

17. **Docs.**
    - `extensions/vscode/README.md` covers:
      - what it does, for each audience;
      - installing the `.vsix`;
      - where the data comes from, and the one network call;
      - the settings: `theme`, `catalogUrl`, `confirmInstalls`, `python`, `evalMaxCostUsd`;
      - how to package it;
      - the manual checks in the Acceptance criteria.
    - The root `README.md`: a short "VS Code extension" section.
    - `CONTRIBUTING.md`:
      - rebuild `catalog.json` after changing a skill description, a version, a case or the archive;
      - `tools/featured.json`;
      - run the extension tests.
    - `doc/running-evals.md`: running evals from the extension.
    - `AGENTS.md`: one line under "This Repository", saying that `extensions/vscode/` is the only JavaScript
      and has no dependencies. The file stays under 120 lines.
    - `CHANGELOG.md` `[Unreleased]`, under `### Added`: the extension, `catalog.json` and `/api/catalog`.
    - No plugin version changes.

## Scope

In:

- `extensions/vscode/`:
  - `package.json`, `README.md`, `.vscodeignore`, `media/` (one SVG Activity Bar icon);
  - `src/extension.js`, the `vscode` glue;
  - pure modules that do not import `vscode`, so `node --test` loads them:
    - `src/catalog.js`: validation, rows, filters, order, statuses and buttons;
    - `src/commands.js`: install arguments and their validation;
    - `src/engine.js`: the URL line, token masking, and an API client over `http`;
    - `src/evalview.js`: a job snapshot to the tray's view model, and transcript paths;
    - `src/theme.js`: palettes, high-contrast mapping and marks;
    - `src/html.js`: escaping, and the two webviews rendered with a nonce;
  - `test/*.test.js` and `test/commands.json`.
- `tools/build_catalog.py`, `tools/test_build_catalog.py`, `tools/featured.json`, the generated
  `catalog.json`.
- `tools/skill_manager.py`: `GET /api/catalog`, with cases in `tools/test_skill_manager.py`, plus the
  `commands.json` case.
- `tools/archive_eval_results.py`: the catalog build after a successful archive, and its test.
- `.github/workflows/validate.yml`, `.gitignore` (`*.vsix`, `node_modules/`).
- `README.md`, `CONTRIBUTING.md`, `doc/running-evals.md`, `AGENTS.md` (one line), `CHANGELOG.md`.

Out:

- **The public web page.** That is plan 28.
- **Publishing to the VS Code Marketplace**, and JetBrains.
- **Any other change to `skill_manager.py`, `build_eval_board.py` or the browser page's look.**
- **Editing skills from the extension.**
- **A Vietnamese UI.** See Open questions.
- **Any plugin or skill.**

## Baseline

| Existing | Keep, change, or remove |
| --- | --- |
| `tools/build_eval_board.py:123` `catalog()`, `:172` `load_results()`, `:219` `trusted()`, `:224` `result_files()`, `:239` `HOSTS` | Reuse from `build_catalog.py`; unchanged |
| `tools/skill_manager.py:245` `plugin_command`, `:286` `installed()` | Keep; the extension mirrors them, and `commands.json` pins both |
| `tools/skill_manager.py:163` `Job.snapshot()`: `status`, `question` `{id, text, choices}`, `log`, `progress` `{index, total, item}`, `tally` | Keep; the tray reads it |
| `tools/skill_manager.py:314` `transcript_path`; the board reads `transcript file: <path>` from the job log (`build_eval_board.py:823`) | Keep; the extension uses the same lines and the same path rule |
| `tools/skill_manager.py:504` `run_eval` validation (cases, host, arms, model, effort, cost 0–50) | Keep; the extension sends only these fields |
| `tools/skill_manager.py:593` Host check, `:610` token check | Keep; `/api/catalog` goes through them |
| `tools/skill_manager.py:704` prints `Skill manager: <url>` | Keep; the extension parses this line |
| `tools/archive_eval_results.py` | Add the catalog build after a successful archive |
| `.github/workflows/validate.yml` `verify`, the one required check | Add `extension` to its `needs` |
| No `LICENSE` file | Hence `vsce package --skip-license` |

## Tech stack and constraints

Default for Python: stdlib-only, Python 3.9 or later.

The deviation, which the user asked for on 2026-11-28, is JavaScript for the VS Code extension. It runs on
Node 18 or later, has no dependencies, and has no build step. `vsce` runs through `npx` for packaging and is
never a dependency.

## Acceptance criteria

- [ ] **The catalog is complete and reproducible.**
  - `python3 tools/build_catalog.py` writes `catalog.json`.
  - This prints `9 18`:

    ```bash
    python3 -c "import json;d=json.load(open('catalog.json'));print(len(d['plugins']),sum(len(p['skills']) for p in d['plugins']))"
    ```

  - On a clean checkout, `python3 tools/build_catalog.py --check` exits 0, and building twice changes no
    bytes.

  Checked by `tools/test_build_catalog.py`.
- [ ] **Failure cases in the catalog.**
  - With a skill description changed in a temporary copy, `--check` exits 1 and prints
    `python3 tools/build_catalog.py`.
  - A run only in `results/` does not change the output.
  - An untrusted run (partial, errored, or with skipped paid graders) does not count toward
    `skills[].evals`, but does appear in `cases[].latest` with `trusted: false`.
  - A `featured.json` naming an unknown plugin fails the build.

  Checked by `tools/test_build_catalog.py`, with a fixture archive of known scores.
- [ ] **`GET /api/catalog` includes local results.**
  - It returns the schema with a run from `results/`.
  - It is refused without the token, and with a foreign Host.

  Checked by `tools/test_skill_manager.py`.
- [ ] **Archiving rebuilds the catalog.** Checked by `tools/test_archive_eval_results.py`.
- [ ] **The two command builders agree.** `python3 tools/test_skill_manager.py` and
      `node --test extensions/vscode/test/` both pass against `test/commands.json`.
- [ ] **Extension logic, each with a Node test, failure cases included:**
  - the catalog is rejected when it is over 1 MB, has another `schemaVersion`, or has a plugin named
    `a;rm -rf` or `../x`;
  - arguments are refused for a plugin not in the catalog, an unknown host, or an unknown action;
  - rows show Get, Update, Enable or the score for not installed, older, disabled and up to date, and are
    ordered as Decision 6 says;
  - the split button's main action follows Decision 6 for each combination of the two hosts;
  - marks: `planning`→`Pl`, `testing`→`Ts`, `review`→`Rv`, `skill-authoring`→`SA`;
  - the theme resolves to stone by default, follows the setting, and in high contrast maps to `--vscode-*`;
  - a job snapshot with a `{id, text, choices: ["y", "n", "s"]}` question gives three buttons and one
    `/api/answer` body `{id, reply}`;
  - a stopped job marks its queued cases stopped;
  - transcript lines are parsed, and `../x.md` or a path outside `plugins/*/evals/results/` is refused;
  - the URL parser rejects `http://example.com:1/?token=x` and a line without a token;
  - the masked log contains no token;
  - the API client sends `X-Board-Token` to a fake `node:http` server, and reports a 409 "another job is in
    progress" as a message;
  - catalog, case, log and question text holding `<script>` renders as text.
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

**Not verifiable in the coder's container**, because it has no VS Code. The user checks these after installing
the `.vsix`, and the README lists the steps:

- the sidebar shows 9 plugins, and the planning page looks like the approved design in each of the three
  themes;
- Install works in a terminal;
- in this repository, one trigger case runs from the Skills tab, and its result shows within 5 s;
- outside this repository, the contributor parts are absent;
- a remote workspace (optional).

## Risks

| Risk | How it is handled |
| --- | --- |
| `catalog.json` goes stale after a skill or case edit | `--check` in the tests and CI, the message names the fix, and archiving rebuilds it |
| The extension's commands drift from `skill_manager.py` | The shared `commands.json`, checked from both sides |
| Scores differ between the store and the engine | One Python implementation serves both (`build_catalog.py` and `/api/catalog`) |
| A fetched catalog injects HTML or a shell argument | Schema and name rules, escaped text, CSP with a nonce, `shellPath`/`shellArgs` with no shell, re-validation on the host side |
| The engine token leaks into a webview or a log | Only the extension host holds it; the log is masked; the server listens on 127.0.0.1 |
| Python buffers stdout, so the URL never appears | `-u`, plus a 15-second timeout and error state 5 |
| A second run is started while one is running | Run buttons are disabled; a 409 from the engine is shown as a message |
| Own palettes clash with an unusual VS Code theme | Three palettes to choose from, and high contrast falls back to VS Code variables |
| Node 18 lacks an API the code uses | CI runs the tests on Node 18 |
| The webview design drifts from the approved one | The palette table and Decisions 6, 8 and 13 fix the layout and copy; the user checks the three themes |

## Open questions

1. **Should the UI also offer Vietnamese, like the browser skill manager?** Until the user answers, the UI is
   English, with every string in one table so a second language is one more table.
