# Plan 22 — align the `fixtures/04-security` answer key with `review-code`'s severity ladder

Status: approved
Date: 2026-11-25
Branch: `test/fixtures-security-severities`
Baseline: `origin/main` at `b26907b82c54ccb7b26ed1e9044003546e400f85`
Target: `fixtures/EXPECTED.md` section 04, the `review-code-finds-planted-vulnerabilities` `findings` grader,
`doc/eval-results.md`, `CHANGELOG.md`

## Goal

`fixtures/EXPECTED.md` section 04 rates three findings in `app.py` as "Should fix":

- the hardcoded `SESSION_SIGNING_KEY` (CWE-798);
- the open redirect (CWE-601);
- the MD5 password hash (CWE-327, CWE-916).

`review-code`'s severity ladder defines Blocking as "a security hole reaches users" and names "secret in
source" as an example (`plugins/review/skills/review-code/references/review-standard.md:28`). In the plan 19
eval, every reply with the plugin rated all three Blocking, and the grader failed them for it. The grader was
loosened, and the disagreement was left as an open item (`doc/eval-results.md`, 2026-11-23, "Open item").

When this is done, the answer key and the grader agree with the skill:

- the hardcoded key is Blocking;
- the open redirect and the MD5 hash may be rated either Blocking or Should fix;
- the open item is closed.

## Decisions

1. **The hardcoded key becomes Blocking; the other two accept either rating** (the user's choice,
   2026-11-25).
   - The ladder names "secret in source" outright.
   - "A security hole reaches users" fits the redirect and the hash, but so does Should fix's "real risk …
     not immediately harmful". The key therefore does not force one rating for them.
   - Rejected: all three Blocking, which would fail a defensible Should fix.
   - Rejected: changing the skill's ladder, which would ship a weaker rule for secrets.
2. **`EXPECTED.md` section 04.**
   - The `SESSION_SIGNING_KEY` row's severity becomes `Blocking`.
   - The redirect and MD5 rows become `Blocking or Should fix`.
   - **Pass** becomes: "all five blocking findings (the four above plus the hardcoded key), each with a CWE
     and a concrete exploit or abuse, ranked at the top severity. The open redirect and MD5 may sit with them
     or below them."
   - **Fail** keeps its items and adds: "missing the hardcoded key, or rating it below Blocking".
   - Nothing else in the fixture or the key changes.
3. **The grader follows the key.** `findings.md` requires five findings at the reply's top severity, each
   with a CWE: the four already named, plus the hardcoded `SESSION_SIGNING_KEY` (CWE-798) with an abuse,
   such as forging a session signature with the key from the source.
   - Keep the rule that the open redirect and MD5 may be rated either way.
   - Keep every other FAIL condition.
4. **The planner reruns the case during review**, with the plan 19 settings:
   `--model claude-sonnet-5-5 --judge-model haiku`, both arms, and `--max-cost-usd 2`. The plan 19 run cost
   $0.52.
   - The coder records the result from the planner's numbers in `doc/eval-results.md`, under a short dated
     section.
   - The coder replaces the 2026-11-23 "Open item" text with a line saying plan 22 settled it.
5. **Changelog, and no version.** Add one line under `[Unreleased]` `### Changed`, extending the existing
   "Eval results" bullet. Fixtures and eval cases are not skill behavior, as in plan 19, so no plugin version
   changes.

## Scope

In:

- `fixtures/EXPECTED.md` section 04.
- `plugins/review/evals/behavior/review-code-finds-planted-vulnerabilities/graders/findings.md`.
- `doc/eval-results.md` and `CHANGELOG.md`.

Out:

- **`fixtures/04-security/app.py` and its `README.md`.** The scaffold is unchanged, so
  `python3 tools/build_eval_scaffolds.py --check` must still pass.
- **`review-code`'s `SKILL.md` and its references.**
- **Every other fixture and answer key.**
- **Plugin versions.**

## Baseline

| Existing | Keep, change, or remove |
| --- | --- |
| `fixtures/EXPECTED.md` section 04 table, Pass and Fail lines | Change per Decision 2 |
| `graders/findings.md`: four required findings; redirect, key and MD5 "acceptable" as Blocking | Change per Decision 3 |
| `review-standard.md:28`, the Blocking row | Read only; the source of Decision 1 |
| `doc/eval-results.md`, 2026-11-23 section, "Open item" | Replace per Decision 4 |
| `CHANGELOG.md` `[Unreleased]` "Eval results" bullet | Extend |

## Tech stack and constraints

Default. Markdown only.

## Acceptance criteria

- [ ] **The key is Blocking in the answer key.** The `SESSION_SIGNING_KEY` row reads `Blocking`, and the
      redirect and MD5 rows read `Blocking or Should fix`. Checked by
      `awk '/^## 04/,/^## 05/' fixtures/EXPECTED.md` and by reading.
- [ ] **The grader requires the key.** `findings.md` names `SESSION_SIGNING_KEY` and CWE-798 among the
      required findings, and FAILs a reply that omits it or rates it below the top severity. Checked by
      reading.
- [ ] **Nothing else moved.** `git diff --stat origin/main...HEAD` lists only the files in Scope and this
      plan, and `python3 tools/build_eval_scaffolds.py --check` exits 0.
- [ ] **Failure case, by the planner during review.** Rerun the case:

      ```bash
      TMPDIR=<dir outside /tmp> claude plugin eval plugins/review --tag behavior --case 'review-code-*' --scaffold --allow-tools Bash Write Edit --no-publish --trust-plugin -j 3 --model claude-sonnet-5-5 --judge-model haiku --max-cost-usd 2
      ```

      - With the plugin it should still pass, since the plan 19 replies rated the key Blocking.
      - Without the plugin it should still fail.
      - A with-plugin run that fails is recorded with what its trace shows, and the planner reports it before
        the pull request opens.
- [ ] **Recorded.** `doc/eval-results.md` has the rerun numbers and no open item for section 04, and
      `CHANGELOG.md` has the line.
- [ ] **Required checks pass:** `python3 tools/validate.py`, `python3 tools/materialize.py --check`, and
      `for t in tools/test_*.py; do python3 "$t" || break; done`.

## Risks

| Risk | How it is handled |
| --- | --- |
| Requiring the key fails runs that rate it Should fix | That is now wrong by the skill's own ladder, so the failure is correct |
| The Haiku judge reads "top severity" loosely | The grader names each of the five findings, as before. The planner reads any failing trace before recording a score |
| The rerun costs more than planned | `--max-cost-usd 2`; the last run cost $0.52 |

## Open questions

None.
