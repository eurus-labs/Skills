#!/usr/bin/env python3
"""The verification skills must speak one language.

`verify-change` judges a change; `setup-verification` writes a project skill that `verify-change` and
`implement` use. A pilot found the generated skill with its own verdict words (`met`, `not met`), a
description that competed with `verify-change`, and a CLI contract that let a required check vanish.
These checks keep the three skills' text from drifting apart again.

Stdlib only, no test framework -- see tools/test_check_env.py for why.

    python3 tools/test_verification_contract.py
"""

import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = {
    "verify-change": "plugins/verification/skills/verify-change/SKILL.md",
    "setup-verification": "plugins/verification/skills/setup-verification/SKILL.md",
    "implement": "plugins/development/skills/implement/SKILL.md",
}
RESULTS = ("`passed`", "`failed`", "`not applicable`", "`not run`")
VERDICTS = ("`verified`", "`verification incomplete`", "`failed`")

FAILURES = []


def check(name, condition, detail=""):
    if condition:
        print("ok   %s" % name)
    else:
        print("FAIL %s %s" % (name, detail))
        FAILURES.append(name)


def read(name):
    with open(os.path.join(REPO, SKILLS[name]), encoding="utf-8") as fh:
        return fh.read()


def template(text):
    """The generated SKILL.md template inside setup-verification."""
    start = text.index("### The generated `SKILL.md`")
    return text[start:text.index("### Feature map index line", start)]


def main():
    vc, sv, im = read("verify-change"), read("setup-verification"), read("implement")
    gen = template(sv)
    desc = re.search(r"^description: (.*?)\n---", gen, re.S | re.M).group(1)

    for word in RESULTS:
        check("verify-change names the result %s" % word, word in vc)
        check("setup-verification names the result %s" % word, word in sv)
    for word in VERDICTS:
        check("verify-change names the verdict %s" % word, word in vc)

    check("the generated skill has no verdicts of its own",
          not re.search(r"`met`|`not met`|conflicts with observed|touches suspected bug", sv + im),
          "old review-table vocabulary is back")
    check("the generated skill hands verdicts to verify-change", "verify-change" in gen)
    check("the generated skill's description does not claim to verify a change",
          not re.search(r"after a change|after implementing|Use after", desc), desc)
    check("the generated skill forbids stash and reset over the working tree",
          re.search(r"[Nn]ever stash, reset", gen) is not None)
    check("required never depends on whether a check can run here",
          "never from whether it can run here" in vc and "never from whether it can run here" in sv)
    check("a known failure is a hint until confirmed on the base",
          "Known failures" in sv and "hint, not evidence" in vc)
    check("skipped tests are not evidence", "skipped test" in vc and "skipped prove nothing" in im)
    check("check must print every row and fail on an unreadable one",
          "**every row**" in sv and "never skipped" in sv)
    check("affected accepts a commit range", "<a>..<b>" in sv)
    check("the fingerprint never includes the evidence it guards",
          "always excluding `.verify/`" in sv)
    check("verify-change passes a commit range's own endpoints, not HEAD",
          "`<a>..<b>` for a commit range" in vc and "<base>..HEAD` for a commit range" not in vc)
    check("verify-change ends with a JSON verdict", '"verdict":' in vc)
    check("affected follows shared code through uses:, and marks those areas",
          "`uses:`" in sv and "via <path>" in sv and "uses: `" in sv)
    check("verify-change and implement turn unmapped paths into criteria or gaps",
          "`unmapped:`" in vc and "**Not verified**" in vc and "`unmapped:`" in im)
    check("runs are isolated: own port and data, a url command, no fixed port in drive lines",
          "One run never touches another's" in sv and "| `url` |" in sv
          and "## Isolation" in gen and "localhost:8000" not in sv)
    check("old runs can be cleaned without touching a live one",
          "| `clean [--keep <n>] [--yes]` |" in sv and "nothing outside `.verify/`" in sv)
    check("cleaning deletes only after the user agrees to the list",
          "only with `--yes`" in sv and "only after the user agrees" in sv
          and "`$V clean --yes` only after they agree" in gen)
    check("a server never outlives its run",
          "also after a failed step" in gen and "also when a step failed" in vc
          and "even after a failed step" in im)
    check("implement no longer reads a review table from the project skill",
          "review-against-the-goal" not in im)

    print()
    if FAILURES:
        print("%d failure(s): %s" % (len(FAILURES), ", ".join(FAILURES)))
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
