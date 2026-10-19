# Skills

[Agent Skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills) for GitHub Copilot,
grouped into installable **plugins**. They also work in Claude Code and any other skills-compatible agent.

## Quick start

```bash
copilot plugin marketplace add eurus-labs/Skills
copilot plugin install testing@CopilotBox
```

Then just ask — the matching skill loads on its own:

> *"Write tests for `src/parser.py`"* · *"Why is this test red?"* · *"Review my changes"* · *"Document this repo"*

Swap `testing` for any plugin below. `add` takes the repository; everything after it takes the marketplace
name, **`CopilotBox`** (case-sensitive). Inside an interactive session, use `/plugin install testing@CopilotBox`.

## Plugins

| Plugin | Skills | What it's for |
| ------ | ------ | ------------- |
| [`testing`](plugins/testing/) | `write-tests`, `review-tests`, `debug-failing-test` | Write, audit, and debug tests in the framework the repo already uses. **Can install your project's test runner** — with your agreement, never unattended |
| [`code-review`](plugins/code-review/) | `review-code`, `setup-review-rules` | Review code against Google's Standard of Code Review; generate a repo's agent/review rules files |
| [`docs`](plugins/docs/) | `document-codebase` | Write architecture docs, a product manual, or your own template, every claim checked against the real dependency graph; check existing docs against a template |
| [`implementation`](plugins/implementation/) | `design-solution`, `implement` | Plan a change without coding, or implement a feature, fix, or refactor and verify it against the request with evidence for every check |

<details>
<summary><b>Other ways to install, and troubleshooting</b></summary>

- **Unmerged branch:** `copilot plugin marketplace add eurus-labs/Skills#some-branch` — `#`, not `@`.
- **Local checkout:** `copilot plugin marketplace add .` — the directory, not the manifest file.
- **VS Code:** search `@agentPlugins` in Extensions, or run **Chat: Plugins**.
- **One skill, no CLI:** copy `plugins/<plugin>/skills/<skill>/` into `.github/skills/`, `.claude/skills/` or
  `.agents/skills/` (one repo), or `~/.copilot/skills/` / `~/.agents/skills/` (all projects).
- **Manage:** `copilot plugin marketplace list|browse|update|remove`, `copilot plugin list|update|uninstall`.

| Symptom | Fix |
| ------- | --- |
| `Available plugins: none` | `copilot plugin marketplace update CopilotBox`; for an unmerged branch, re-add with `#branch` |
| `Marketplace "CopilotBox" already registered` | `update`, or `remove` then `add` |
| `File not found: marketplace.json` with doubled paths | Pass the directory containing `.github/plugin/`, e.g. `.` |
| `Repository not found` on a ref | Use `owner/repo#ref`, not `@` |
| `Marketplace "eurus-skills" ...` | `copilot plugin marketplace remove eurus-skills --force`, then `add` again |

</details>

## Safety

Skills are injected into an agent's context and are **not verified by GitHub** — review anything you install.
Bundled scripts never install packages. The one exception is `testing`, which can install your project's
existing test runner: it tells you first, asks before anything that rewrites your files, and never runs where no
one can be asked (CI, coding agents, `-p` mode, subagents). See
[`plugins/testing/README.md`](plugins/testing/README.md#installing-packages).

## Contributing

Read [`CONTRIBUTING.md`](CONTRIBUTING.md); AI agents read [`AGENTS.md`](AGENTS.md) first. A new plugin needs an
entry in [`.github/plugin/marketplace.json`](.github/plugin/marketplace.json) **and** a row in the table above.
Content shared between plugins lives in [`shared/`](shared/) and is copied in by `tools/materialize.py` — edit
the source, never the copies. [`fixtures/`](fixtures/) holds deliberately broken projects for evaluating the
plugins. Before committing:

```bash
python3 tools/validate.py && python3 tools/materialize.py
for t in tools/test_*.py; do python3 "$t" || break; done
```
