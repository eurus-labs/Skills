# Eurus Skills for VS Code

One extension for the two ways people use this marketplace.

- **A store, for everyone.** A sidebar lists every plugin. Each plugin opens a page in the editor with its
  description, install state per host, eval score, skills and archived runs. You install, update, enable and
  uninstall from there, for Copilot CLI and Claude Code. It needs no checkout of this repository.
- **Eval runs, for contributors.** When the open folder is a checkout of this repository, the same plugin page
  lists each skill's eval cases. You run a case, a skill or the whole plugin, answer grading questions, stop a run
  and open transcripts there. The running is done by `tools/skill_manager.py`, started headless.

It is plain JavaScript with no dependency and no build step. It sends no telemetry.

## Install it

The extension is not published to the VS Code Marketplace. Package it once, or take the `.vsix` from a GitHub
Release, then install the file:

```bash
code --install-extension eurus-skills-0.1.0.vsix
```

Open the **Eurus Skills** icon in the Activity Bar. VS Code 1.85 or later is required.

## What each audience sees

| You | The sidebar and the plugin page |
| --- | --- |
| Anyone | Search, a host switch, filters (All, Installed, Updates), **Update all**, a plugin page with the eval score, a Skills / Runs / Install card, and one-click install through a terminal you confirm first. |
| A contributor, with this repository open | The same, plus a **Contributor** badge on the Skills tab, a chevron on each skill that opens its eval cases, **Run** buttons, and the Eval run tray with grading questions, Stop and transcripts. |

Install state comes from `<host> plugin list --json` and `<host> plugin marketplace list --json`, run without a
shell. Every install, update, enable, uninstall and marketplace command opens a dialog that shows the exact command,
then runs it in a VS Code terminal (`shellPath` and `shellArgs`, so no shell parses it). Uninstall always asks.
The commands are the ones `tools/skill_manager.py` builds; `test/commands.json` pins both.

## Where the data comes from

The data is one schema, `catalog.json`, with `schemaVersion: 1`.

- **The open folder is this repository** (it holds `tools/skill_manager.py` and a marketplace named `eurus-labs`).
  The extension reads that folder's `catalog.json`. Once the engine is running, it reads `GET /api/catalog` from the
  engine instead, which also counts a run finished a moment ago.
- **Any other folder.** The extension fetches
  `https://raw.githubusercontent.com/eurus-labs/Skills/main/catalog.json`. This is the one network call it makes. The
  last good copy is kept and shown with its date when you are offline.
- **A catalog is rejected before anything is drawn** when it is over 1 MB, has a `schemaVersion` other than 1, or has
  a plugin, case or host name that is not lowercase letters, digits and hyphens. The extension then keeps showing the
  last good catalog and says why.

## Settings

| Setting | Default | Meaning |
| --- | --- | --- |
| `eurusSkills.theme` | `stone` | The palette: `stone`, `charcoal` or `black`. Ignored in a high-contrast VS Code theme. |
| `eurusSkills.catalogUrl` | the GitHub raw URL above | Where to fetch the catalog outside a checkout. Must be `https://`. Machine scope, so a workspace cannot change it. |
| `eurusSkills.confirmInstalls` | `true` | Ask before install, update and enable. The **Don't ask again** box sets it to `false`. Uninstall always asks. |
| `eurusSkills.python` | `python3` | The Python 3.9 or later that runs `tools/skill_manager.py`. Machine scope, because it is run as a program. |
| `eurusSkills.evalMaxCostUsd` | `2` | The cost ceiling for a Claude Code eval run. Over 0 and at most 50, as the engine requires. |

In a workspace you have not trusted, the store and the installs still work, but the eval engine is not started,
because it runs a Python script from the workspace.

## Running evals

Open this repository, open a plugin, and use the Skills tab.

1. **Run**, **Run N cases** or **Run all N cases** opens a dialog. It says who is billed (your Claude key with the
   `$N` ceiling, or your Copilot plan), that the agent runs commands in a scratch workspace as you, and shows the
   command the engine runs.
2. The extension starts `python3 -u tools/skill_manager.py --no-open` on the first run and reads its address. The
   token stays in the extension host. It is never sent to a webview or written to the log.
3. The tray lists each case (queued, running, passed, failed, stopped) with its score and a **Transcript** link.
   When Copilot CLI asks a grading question, a **Waiting for you** card shows it with Yes, No and Skip.
4. If `claude plugin eval` says the folder is not trusted, run it once in a terminal and answer the prompt. The
   extension never passes `--trust-plugin`.

The engine runs one job at a time, so Run buttons are disabled while a run is in progress. The Output channel
**Eurus Skills** holds the engine's output with the token masked. **Eurus Skills: Open skill manager in browser** opens
the old page for anything this one does not show.

## Package it

`vsce` is never a dependency. Run it through `npx`, with an exact version (this repository has no `LICENSE`, hence
`--skip-license`):

```bash
cd extensions/vscode
npx --yes @vscode/vsce@4.1.1 package --skip-license --out /tmp/eurus-skills.vsix
```

The `.vsix` is git-ignored. Attach it to a GitHub Release.

## Test it

```bash
node --test extensions/vscode/test/
```

The tests use Node's built-in runner and run on Node 18 and 22, in CI as the `extension` job. They load the pure
modules in `src/` without VS Code, and drive `src/extension.js` against a fake `vscode` module, fake `claude` and
`copilot` programs, and the real engine when `python3` is installed.

| Module | What it holds |
| --- | --- |
| `src/catalog.js` | Validation, rows, filters, order, statuses, the split button, and the view models |
| `src/commands.js` | Install arguments and their validation, and how install state is read |
| `src/engine.js` | The URL line, token masking, and the API client over `http`; starting the engine |
| `src/evalview.js` | A job snapshot to the tray, transcript paths, and the run dialog |
| `src/theme.js` | Palettes, the high-contrast mapping, plugin marks and score colors |
| `src/html.js` | Escaping, and the two webviews with their Content-Security-Policy |
| `src/extension.js` | The only file that imports `vscode` |

## Check it by hand

VS Code is not available where the tests run, so these steps are for you, after installing the `.vsix`:

1. The sidebar shows 9 plugins. Open `planning`. Its page looks like the approved design in each of the three themes
   (`eurusSkills.theme`: `stone`, `charcoal`, `black`).
2. Click **Get** on a plugin, confirm, and see the command run in a terminal. When the terminal closes the row
   updates.
3. With this repository open, expand a skill on the Skills tab and run one trigger case. Its result shows within
   5 seconds of the run ending.
4. Open a folder that is not this repository. The Contributor badge, the chevrons and the Run buttons are gone.
5. Optional: open a remote workspace (SSH, container, WSL). The extension and the engine run on the same side.
