# Skills

[Agent Skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills) for GitHub Copilot,
grouped into installable **plugins**. Agent Skills are an open standard, so they also work in Claude Code and
any other skills-compatible agent.

## Plugin catalog

| Plugin | Skills | What it's for |
| ------ | ------ | ------------- |
| [`testing`](plugins/testing/) | `write-tests`, `review-tests`, `debug-failing-test` | Write, audit, and debug automated tests in whatever framework the repo already uses. **Can install your project's test runner** — with your agreement, never unattended |
| [`code-review`](plugins/code-review/) | `review-code`, `setup-review-rules` | Review code against Google's Standard of Code Review, and generate a repo's agent/review rules files |
| [`docs`](plugins/docs/) | `document-codebase` | Write a repository's architecture documentation, a product manual, or a document following your own template — you choose the outline, none is mandatory — with every claim checked against the real dependency graph; and check existing docs against a template |

## Install

```bash
copilot plugin marketplace add eurus-labs/Skills
copilot plugin install <plugin-name>@CopilotBox
```

`add` takes the repository; everything after takes the manifest name, **`CopilotBox`** (case-sensitive).
In an interactive session use `/plugin install <plugin-name>@CopilotBox`. Other commands: `copilot plugin
marketplace list|browse|update|remove`, `copilot plugin list|update|uninstall`.

- **Unmerged branch:** `copilot plugin marketplace add eurus-labs/Skills#some-branch` — `#`, not `@`.
- **Local checkout:** `copilot plugin marketplace add .` — the directory, not the manifest file.
- **VS Code:** search `@agentPlugins` in Extensions, or run **Chat: Plugins**.
- **Single skill, no CLI:** copy `plugins/<plugin>/skills/<skill>/` into `.github/skills/`, `.claude/skills/`
  or `.agents/skills/` (one repo), or `~/.copilot/skills/` / `~/.agents/skills/` (all projects).

| Symptom | Fix |
| ------- | --- |
| `Available plugins: none` | `copilot plugin marketplace update CopilotBox`; for an unmerged branch, re-add with `#branch` |
| `Marketplace "CopilotBox" already registered` | `update`, or `remove` then `add` |
| `File not found: marketplace.json` with doubled paths | Pass the directory containing `.github/plugin/`, e.g. `.` |
| `Repository not found` on a ref | Use `owner/repo#ref`, not `@` |
| `Marketplace "eurus-skills" ...` | `copilot plugin marketplace remove eurus-skills --force`, then `add` again |

## Repository layout

| Path | Purpose |
| ---- | ------- |
| [`plugins/<name>/`](plugins/) | One plugin: `.github/plugin/plugin.json`, `README.md`, `skills/<skill>/SKILL.md` |
| [`plugins/_template/`](plugins/_template/) | Scaffold for a new plugin — not installable |
| [`.github/plugin/marketplace.json`](.github/plugin/marketplace.json) | Marketplace manifest — a new plugin needs an entry here **and** a catalog row above |
| [`shared/`](shared/) | Source for content used by several plugins; copied in by `tools/materialize.py` per `shared.manifest`. Edit here, never the copies |
| [`tools/`](tools/) | `validate.py`, `materialize.py`, and the behavioural tests |
| [`fixtures/`](fixtures/) | Deliberately broken sample projects for evaluating the plugins — keep `EXPECTED.md` out of a demo session |

## Checks

```bash
python3 tools/validate.py
python3 tools/materialize.py
for t in tools/test_*.py; do python3 "$t" || break; done
```

CI runs all three on Python 3.9 and 3.13.

## Contributing

Read [`CONTRIBUTING.md`](CONTRIBUTING.md); AI agents read [`AGENTS.md`](AGENTS.md) first.

## Safety

Skills are injected into an agent's context and are **not verified by GitHub** — review anything you install.
Bundled scripts never install packages; they read files, print JSON and exit. The one exception is `testing`,
which can install your project's existing test runner, telling you first, asking before anything that rewrites your files, and never where no one can be
asked (CI, coding agents, `-p` mode, subagents). See
[`plugins/testing/README.md`](plugins/testing/README.md#installing-packages).
