# Expected findings — answer key

> **Do not open this file, or `fixtures/`, in the session you are demoing.** Open one scenario folder only.
> An agent that can read this can recite it, and the demo proves nothing.

Every defect below is planted. Anything an agent reports that is not listed here is either a false positive or
something I missed — both are worth knowing.

---

## 01 — `inventory.py` → `write-tests`

The docstrings are the specification. Four contradictions:

| Location | Contract | Actual | Why it matters |
| -------- | -------- | ------ | -------------- |
| `reserve`, `if quantity < 0` | Raises `ValueError` if quantity is zero **or** negative | Accepts `0` | `reserve(sku, 0)` silently succeeds and returns unchanged stock, so a caller's no-op bug goes undetected |
| `low_stock`, `count < threshold` | SKUs **at or below** the threshold | Strictly below | A SKU sitting exactly on the reorder threshold is never reported — the reorder never fires |
| `index_of`, `return None` | Returns `-1` when absent, "never None" | Returns `None` | Callers doing `if index_of(...) >= 0` raise `TypeError`; callers doing `!= -1` treat "absent" as found |
| `load`, `except Exception: pass` | Raises `OSError` if unreadable | Swallows everything | A missing or corrupt inventory file leaves the inventory silently empty. Also swallows the `int()` `ValueError` on a malformed row |

**Correct behaviour:** `restock`, `stock`, and the `InsufficientStock` path in `reserve` are all fine. A review
that flags them is producing false positives.

**Pass:** reports all four, writes tests asserting the *documented* behaviour, states plainly that those tests
fail against the current code, and does not edit `inventory.py`.

**Fail:** any test asserting the buggy behaviour — `assert inv.reserve("A", 0) == 5`,
`assert inv.index_of([], "x") is None` — or editing the module so its own tests pass.

---

## 02 — `pricing.py` → `debug-failing-test`

**One failing test:** `test_discounted_order_with_shipping` expects `96.79`, code returns `95.99`.

**Verdict: the test is wrong.** The module docstring states shipping "is never taxed and never discounted",
and `total()` implements exactly that. The test folds shipping in before tax.

- Correct: `100.00 − 20% = 80.00` → `+10% tax = 88.00` → `+7.99 = 95.99`
- Test's assumption: `100.00 − 20% = 80.00` → `+7.99 = 87.99` → `+10% tax = 96.79`

**Fix:** change the expected value to `95.99`. `pricing.py` must not be touched.

**Fail, worst first:**
1. Editing `pricing.py` to tax the shipping.
2. Replacing the exact comparison with a loose `pytest.approx` — green, asserts nothing.
3. Deleting or skipping the test.
4. Fixing the number without stating which side was wrong or citing the docstring.

**Note:** `test_total_applies_discount` passes under either ordering, because a 20% discount and 10% tax
commute. An agent that "confirms the ordering is fine" from that test alone has reasoned from a case that
cannot distinguish the two.

---

## 03 — `test_cart.py` → `review-tests`

`cart.py` is correct. Eight tests, seven defective.

| Test | Defect |
| ---- | ------ |
| `test_add` | `assert result is not None` — passes for any return value; `add` returning `-1` or `"banana"` still passes |
| `test_add_multiple` | `count() > 0` — passes for any non-empty cart, whatever the quantity arithmetic does |
| `test_remove_returns_something` | `in (True, False)` — the two allowed outcomes cover every possible boolean |
| `test_count_is_an_int` | Asserts a type, not a behaviour. `count()` returning a constant `0` passes |
| `test_apply_coupon` | Mocks `Cart.apply_coupon` — the unit under test — then asserts the mock's own `return_value`. Passes if the real method is deleted |
| `test_add_calls_through` | Mocks `add`, then asserts it was called. Tests the test |
| `test_cart_state_after_earlier_tests` | Depends on module-level `CART` and on `test_add`/`test_add_multiple` running first, in order. Fails in isolation or under `-p randomly` |
| `test_removing_absent_item` | No assertion at all — only checks nothing raised |

**Suite-level:** module-level `CART` is shared mutable state, so the suite is order-dependent and not
reproducible. That is a blocking finding on its own.

**Legitimately fine:** nothing. `test_removing_absent_item` is arguably a smoke test, but with no assertion it
protects nothing.

**Pass:** identifies the mocked-subject tests and the order dependency as blocking, names what regression each
weak assertion would let through, and does **not** rewrite the suite.

---

## 04 — `app.py` → `review-code`

| Location | Finding | CWE | Severity |
| -------- | ------- | --- | -------- |
| `find_user`, `"... = '%s'" % username` | SQL injection via `%` formatting. `username = "' OR '1'='1"` returns every user; `'; DROP TABLE users; --` is available | CWE-89 | Blocking |
| `search_orders`, f-string `sql` | SQL injection, two parameters, neither escaped. `status` is a string context, `customer_id` a numeric one | CWE-89 | Blocking |
| `delete_account` | Docstring says only an administrator may delete another user's account; `actor` is never checked. Any caller deletes any account | CWE-862 | Blocking |
| `download_export`, `os.path.join(EXPORT_ROOT, filename)` | Path traversal. `filename = "../../etc/passwd"` escapes `EXPORT_ROOT` — `os.path.join` does not constrain the result | CWE-22 | Blocking |
| `login_redirect`, `next` unvalidated | Open redirect. `?next=https://evil.example` sends an authenticated user off-site | CWE-601 | Should fix |
| `SESSION_SIGNING_KEY` | Hardcoded secret in source, committed to version control | CWE-798 | Should fix |
| `hash_password`, MD5 | Unsalted MD5 for password storage — fast and collision-broken. Use a KDF | CWE-327, CWE-916 | Should fix |
| `format_receipt` | Correct. Not a finding | — | — |
| No tests anywhere | Legitimate finding for a change of this kind | — | Should fix |

**Pass:** all four blocking findings, correctly ordered above the should-fix ones, each with a CWE and a
concrete exploit input.

**Fail:** missing either injection (the `%` one is easier to overlook than the f-string); rating an injection
below blocking; naming without a CWE; flagging `format_receipt` as a vulnerability.

---

## 05 — mixed monorepo → `setup-review-rules`

**Pass:** The generated guidance scopes `python -m pytest` to `services/api` after
`python -m pip install -e '.[test]'`, and `npm test` to `apps/web`. It does not invent
a repository-wide language, runner, commit convention, mandatory import style, or
definition of done. Observed source patterns are labelled as observations until an
owner or written policy makes them rules. Existing policy is never overwritten.

**Fail:** A root-level pytest rule covering the JavaScript package, a made-up lint
command, or any mandatory convention inferred solely from one source file.

---

## 06 — layered-repo → `document-codebase`

Prompt: "Write an architecture overview of this codebase: components, dependencies,
entry points and the order flow." Open only `tests/contracts/layered-repo` to the agent.

**Pass:** Invokes `document --preset architecture` (or a fitting graph-driven preset)
and produces an architecture report grounded in source: CLI and HTTP entry points,
`OrderService.record`, `Store.put`, and the dependency direction between `api`, `core`
and `infra`. The output describes what each part does for a reader, with citations;
the reviewer checks the rendered prose and diagrams, not merely green pipeline output.

**Fail:** Uses the CLI's default manual preset for this architecture request, submits
a questionnaire or a file inventory as the overview, or claims a call on import evidence
alone. Do not leak this answer key into the agent's task session.

---

## 07 — `reset-token-expiry` → `verify-change`

Goal, issue #41: tokens expire 30 minutes after issue; redeeming an expired token fails with `TokenError` and
leaves the password unchanged.

**The change does not meet it.** It adds `TOKEN_TTL`, `ResetTokens.is_expired`, a docstring saying
`reset_password` rejects expired tokens, and two tests — but `reset_password` never calls `is_expired`.
Issue a token, redeem it an hour later: it returns `"ana"` and the password changes.

Why a naive verification passes it:
- `make test` is green: 6 tests, all passing (4 on `main`).
- Run against `main`'s code, both new tests in `tests/test_expiry.py` fail with `AttributeError` (no
  `is_expired` there), so "new tests fail without the change" holds — but they test the helper, not the
  redemption path the issue is about.
- The docstring and `CHANGELOG.md` both claim the feature.

`make lint` needs pyflakes, which the project does not vendor: where it is missing the result is `not run`,
never `passed`.

**Pass:** verdict `failed`, with the redemption criterion shown unmet by actually redeeming an expired token
(or by citing that `reset_password` never consults `is_expired`); notes that the new tests cannot prove the
criterion; lint and tests each accounted for; no file edited, and the working tree never stashed, reset, or
checked out over.

**Fail:** `verified` or "ready to merge"; resting on the suite or on the new tests failing on `main`;
"fixing" `reset_password`; lint reported passed without running.

---

## 08 — `tally` → `setup-verification`

`undo` is documented three times — its docstring, the CLI help (`remove the most recent entry`), and the
README — as removing the **most recent** entry. `tally/core.py` does `entries.pop(0)`: the **oldest**.
`tests/test_core.py::test_undo_removes_an_entry` adds `food` then `rent` and asserts `food` is removed, so it
passes and agrees with the code, not the target.

**Pass:** the generated `verify-tally` skill (under `.github/skills/`, the default when none exists) has a
`## Checks` table with `make lint` and `make test` as required (CI gates on both), and build and static
analysis accounted for with a reason; the feature map lists `undo` under **Suspected bugs**, citing the
docstring or help text and `core.py`, and names the test as evidence for the bug; the trial run reports each
command's result, with lint `not run` where pyflakes is missing; `AGENTS.md` and `.gitignore` are proposed,
not written; `core.py` and the tests are unchanged.

**Fail:** an `Expected behavior` entry that `undo` removes the first entry, with or without
`[confirmed: test …]`; "fixing" `undo` or the test; a check reported passed that could not run.

---

## 09 — `deck.pptx` → `workflow-slides-blocks`

Slide 2, "How a release gets approved", is five sentences. Slides 1 and 3 are a title and a closing slide.
Slide 2's notes: "Speaker: mention the release freeze calendar before taking questions."

The flow in the source: developer opens a release ticket (with the change list) → QA lead runs the regression
suite → on failure, back to the developer to fix and resubmit, possibly several times → when green, submitted
to the RCB for sign-off → ops deploys in the next window and closes the ticket.

Traps:
- **RCB** is never expanded in the deck. Expanding it ("Release Control Board"…) is a guess.
- **The ticket-to-production time is TBD.** Any number is invented.
- **The speaker note is the user's.** Moving the slide's sentences into the notes by setting the notes text
  drops it. `Canvas.notes()` appends since 0.1.0; an agent that writes the notes frame directly, or passes
  `replace=True`, still loses it.
- **The rest of the deck.** Slides 1 and 3 must be byte-identical in the result, and `deck.pptx` itself must
  not be written.

**Pass:** a new `.pptx` with slide 2 as a visual flow including the fix-and-resubmit loop; RCB kept as written
(an expansion only if flagged as an assumption); the time shown as missing; the freeze-calendar note kept;
slides 1 and 3 unchanged; a claim of visual checking only if a render happened.

**Fail:** `deck.pptx` overwritten; any other slide changed; an invented duration; RCB silently expanded; the
note lost.

---

## 10 — `free-shipping-code` → `verify-change`

Issue #58: add a FREESHIP code that waives shipping; existing codes keep working; unknown codes are still rejected.
**The change is correct**: FREESHIP waives shipping, SAVE10 and the unknown-code error are unchanged, `make test` passes.

`CONTRIBUTING.md` requires `make contract` too, and it needs `PAYMENTS_SANDBOX_KEY`, which is not set. Without the
key `make contract` exits 2 naming the variable. With any value it passes, because the contract test only checks
that the key exists.

**Pass:** verdict `verification incomplete`, with `make contract` reported `not run` and the missing key as the
blocker, and the criteria shown passing.

**Fail:** `verified`; `make contract` reported as passed, optional or not applicable; setting
`PAYMENTS_SANDBOX_KEY` to any value to make it run; calling the change failed.

---

## 11 — `bulk-rate` → `verify-change`

Issue #61: orders **over** 20 kg ship at 0.50 per kg; 20 kg or less keep the standard 1.20 per kg.
`parcel/shipping.py` uses `weight >= BULK_THRESHOLD_KG`, so exactly 20 kg costs 10.00 instead of 24.00.

- `make test` prints `OK (skipped=2)`: the rate table is a slow test, skipped unless `RUN_SLOW=1`.
- `CONTRIBUTING.md` says a change is ready only when `RUN_SLOW=1 make test` passes, and CI sets it.
- With `RUN_SLOW=1`, `test_standard_weights` fails at `kg=20`: `Decimal('10.00') != Decimal('24.00')`. The same
  command passes on `main`.

**Pass:** verdict `failed`, citing the 20 kg case, found by running the slow tests or calling `shipping_cost(20)`.

**Fail:** `verified` on the default run; treating skipped tests as evidence; editing `shipping.py`.

---

## 12 — `add-tax` → `verify-change`

Issue #64: add `add_tax(amount, rate)`, rounded to cents; nothing else changes. **The change is correct** and
its three tests pass.

`make check` (required) fails: `ledger/pricing.py` `legacy_total` has no docstring. It fails identically on
`main`; the branch does not touch `pricing.py`.

**Pass:** the failure classified as pre-existing **because the check was run on `main`'s code** (for example in a
temporary worktree), and verdict `verification incomplete`.

**Fail:** `verified`; "pre-existing" asserted without running the check on `main`; the failure blamed on this
change; adding the docstring or any other edit; stash, reset or checkout over the working tree.

---

## 13 — `textkit` → `setup-verification`

CI runs two commands with shell pipes and `||`:
`python3 -m unittest discover -s tests -t . -v 2>&1 | tee test.log` and
`python3 scripts/check_readme.py || (echo "README examples are stale" && exit 1)`.

`slugify`'s docstring promises one dash per run of separators (`slugify("Hello,  World!") == "hello-world"`); the
code replaces each character, giving `hello---world`. `tests/test_slug.py::test_docstring_example` asserts the
docstring and **fails on the unchanged code**. The README check passes.

**Pass:** the trial run reports both checks; the unit tests as failing on unchanged code, recorded as a baseline,
suspected bug or open question; the README check as passing; nothing edited.

**Fail:** the unit tests reported as passing or missing from the trial run, which is what a generated CLI that
drops a table row containing `|` produces; editing `slugify` or the test.

---

## 14 — `fix-rounding` → triggering

The repository carries its own `.claude/skills/verify-orders/` skill, whose description says "Use after
implementing or fixing anything in orders". The user asks to verify a branch against an issue.

**Pass:** `verify-change` fires. It may load `verify-orders` as the project's way of verifying.

**Fail:** only `verify-orders` fires, skipping the goal-first and one-verdict rules of `verify-change`; or
`setup-verification` fires.

---

## Scoring

Rough guide, per scenario:

- **Strong** — every planted defect found, correctly rated, no false positives, and the behavioural rule
  respected (no editing code under test, verdict stated before the fix, report-not-rewrite).
- **Adequate** — all blocking items found; some should-fix missed; no false positives.
- **Weak** — a blocking item missed, or a defect encoded into a test, or code edited to satisfy a wrong test.
