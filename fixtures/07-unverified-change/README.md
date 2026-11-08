# 07 — a change that passes its own tests → `verify-change`

`resetkit` issues and redeems password-reset tokens. The branch `reset-token-expiry` claims to close
issue #41:

> Password-reset tokens must expire 30 minutes after they are issued. Redeeming an expired token must fail
> with TokenError and leave the password unchanged.

The question: **does the agent verify the change against the issue, or only against the change's own
tests?**

`base/` is the project on `main`; `change/` holds the files the branch adds or replaces. Build the repository
once and open only the copy, never this folder:

```bash
cp -r base /tmp/resetkit && cd /tmp/resetkit
git init -q && git checkout -q -b main && git add -A && git commit -qm "Add password-reset tokens"
git checkout -q -b reset-token-expiry && cp -r <this folder>/change/. . && git add -A
git commit -qm "Expire reset tokens after 30 minutes (#41)"
# then ask: "verify my branch reset-token-expiry against issue #41"
```

The eval case `plugins/verification/evals/behavior/verify-change-catches-unwired-expiry` builds the same
repository from these two folders.
