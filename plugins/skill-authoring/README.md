# skill-authoring

Tools for people who write Agent Skills. This plugin is for authors; installing it adds nothing to everyday
coding work.

## Install

```bash
copilot plugin marketplace add eurus-labs/Skills
copilot plugin install skill-authoring@eurus-labs
```

## Skills

- **`evaluate-skill`** — evaluates a skill, or every skill in a plugin, on three levels:
  - **static:** frontmatter, description, scope and structure;
  - **triggering:** whether it fires on the requests it should and stays quiet on its siblings' requests and
    near-misses;
  - **behavior:** whether an agent with the skill reaches the right outcome on a task whose answer was
    written beforehand, compared with the same task without the plugin.

  It writes the eval suite in the format `claude plugin eval` runs, runs it only with your agreement, and
  reports each failure with what it points to: the description for a trigger failure, the body for a behavior
  failure. Fires on "evaluate this skill", "will this skill trigger", "write evals for this plugin".

## Why a runner and not a self-check

An agent that has read a skill and is asked whether it would follow it nearly always says yes. So
`evaluate-skill` never grades behavior itself. Each case runs in a fresh, isolated session started by
`claude plugin eval`, and the result is scored against expected outcomes written before the run. The same
case runs again without the plugin, and the skill is credited only for the difference, `Δ`.

## Notes

- **Requires** Claude Code with `claude plugin eval` (v2.1.269 or later) to run a suite. Without it, the
  skill writes the suite and reports it as not run. Copilot CLI has no equivalent runner the skill knows of.
- **Costs and publishing:** every eval run and every judge-graded check is a model call on your account. By
  default each case runs three times with the plugin and three times without. The skill states the count,
  proposes a `--max-cost-usd` ceiling, and asks before running. It passes `--no-publish`, because the
  runner otherwise publishes its report to claude.ai, unless you agree to publish.
- **Side effects:** writes the suite under the plugin's eval directory (`evals/` by default), and with your
  agreement runs the evals, which write `evals/results/<timestamp>/`. It proposes adding that to
  `.gitignore`, and never edits the skill it evaluates unless asked.
