#!/usr/bin/env bash
# GENERATED FILE -- DO NOT EDIT. Regenerate with: python3 tools/build_eval_scaffolds.py
# Recreates a git repository: fixtures/07-unverified-change/base on main, then fixtures/07-unverified-change/change in the eval's empty workspace.
set -euo pipefail
cat > 'CHANGELOG.md' <<'EVAL_FIXTURE_EOF'
# Changelog

## 0.1.0

- First release: issue and redeem password-reset tokens.
EVAL_FIXTURE_EOF
cat > 'CONTRIBUTING.md' <<'EVAL_FIXTURE_EOF'
# Contributing

A change is ready to merge when both of these pass. CI runs them on every pull request.

- `make lint` — pyflakes over the package and the tests.
- `make test` — the unittest suite.
EVAL_FIXTURE_EOF
cat > 'Makefile' <<'EVAL_FIXTURE_EOF'
lint:
	python3 -m pyflakes resetkit tests

test:
	python3 -m unittest discover -s tests -t . -v

.PHONY: lint test
EVAL_FIXTURE_EOF
cat > 'README.md' <<'EVAL_FIXTURE_EOF'
# resetkit

Password-reset tokens: issue one for an account, redeem it once to set a new password.

```python
from resetkit.tokens import ResetTokens
tokens = ResetTokens(accounts)
token = tokens.issue("ana", now)
tokens.reset_password(token, "new password", now)
```
EVAL_FIXTURE_EOF
cat > 'pyproject.toml' <<'EVAL_FIXTURE_EOF'
[project]
name = "resetkit"
version = "0.1.0"
description = "Password-reset tokens"
requires-python = ">=3.9"
EVAL_FIXTURE_EOF
mkdir -p '.github/workflows'
cat > '.github/workflows/ci.yml' <<'EVAL_FIXTURE_EOF'
name: ci
on: [pull_request]
jobs:
  check:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: python3 -m pip install pyflakes
      - run: make lint
      - run: make test
EVAL_FIXTURE_EOF
mkdir -p 'resetkit'
: > 'resetkit/__init__.py'
mkdir -p 'resetkit'
cat > 'resetkit/tokens.py' <<'EVAL_FIXTURE_EOF'
"""Password-reset tokens.

`ResetTokens.issue` gives an account a token; `ResetTokens.reset_password` redeems it
once to set a new password.
"""

import hashlib
import secrets


class TokenError(Exception):
    """A reset token that cannot be redeemed."""


def _digest(password):
    # Stand-in for the real password hashing, which lives in the accounts service.
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


class ResetTokens:
    def __init__(self, accounts):
        """`accounts` maps a username to its password digest and is updated in place."""
        self._accounts = accounts
        self._tokens = {}

    def issue(self, username, now):
        """Return a new single-use reset token for `username`, issued at `now`."""
        if username not in self._accounts:
            raise KeyError(username)
        token = secrets.token_urlsafe(16)
        self._tokens[token] = (username, now)
        return token

    def reset_password(self, token, new_password, now):
        """Set a new password for the token's account and return the username.

        The token is single-use. Raises TokenError for an unknown or already used token.
        """
        try:
            username, _issued = self._tokens.pop(token)
        except KeyError:
            raise TokenError("unknown or already used token") from None
        self._accounts[username] = _digest(new_password)
        return username
EVAL_FIXTURE_EOF
mkdir -p 'tests'
: > 'tests/__init__.py'
mkdir -p 'tests'
cat > 'tests/test_tokens.py' <<'EVAL_FIXTURE_EOF'
import unittest
from datetime import datetime

from resetkit.tokens import ResetTokens, TokenError, _digest

T0 = datetime(2026, 1, 1, 12, 0, 0)


class ResetTest(unittest.TestCase):
    def setUp(self):
        self.accounts = {"ana": _digest("old")}
        self.tokens = ResetTokens(self.accounts)

    def test_reset_sets_new_password(self):
        token = self.tokens.issue("ana", T0)
        self.assertEqual(self.tokens.reset_password(token, "new", T0), "ana")
        self.assertEqual(self.accounts["ana"], _digest("new"))

    def test_token_is_single_use(self):
        token = self.tokens.issue("ana", T0)
        self.tokens.reset_password(token, "new", T0)
        with self.assertRaises(TokenError):
            self.tokens.reset_password(token, "again", T0)
        self.assertEqual(self.accounts["ana"], _digest("new"))

    def test_unknown_token_is_rejected(self):
        with self.assertRaises(TokenError):
            self.tokens.reset_password("not-a-token", "new", T0)
        self.assertEqual(self.accounts["ana"], _digest("old"))

    def test_unknown_account_cannot_get_a_token(self):
        with self.assertRaises(KeyError):
            self.tokens.issue("bob", T0)
EVAL_FIXTURE_EOF
git init -q
git checkout -q -b main
git add -A
GIT_AUTHOR_NAME='Eval Fixture' GIT_AUTHOR_EMAIL='fixture@example.invalid' GIT_COMMITTER_NAME='Eval Fixture' GIT_COMMITTER_EMAIL='fixture@example.invalid' git -c commit.gpgsign=false commit -q -m 'Add password-reset tokens'
git checkout -q -b 'reset-token-expiry'
cat > 'CHANGELOG.md' <<'EVAL_FIXTURE_EOF'
# Changelog

## Unreleased

- Password-reset tokens now expire 30 minutes after they are issued (#41).

## 0.1.0

- First release: issue and redeem password-reset tokens.
EVAL_FIXTURE_EOF
mkdir -p 'resetkit'
cat > 'resetkit/tokens.py' <<'EVAL_FIXTURE_EOF'
"""Password-reset tokens.

`ResetTokens.issue` gives an account a token; `ResetTokens.reset_password` redeems it
once to set a new password.
"""

import hashlib
import secrets
from datetime import timedelta

TOKEN_TTL = timedelta(minutes=30)


class TokenError(Exception):
    """A reset token that cannot be redeemed."""


def _digest(password):
    # Stand-in for the real password hashing, which lives in the accounts service.
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


class ResetTokens:
    def __init__(self, accounts):
        """`accounts` maps a username to its password digest and is updated in place."""
        self._accounts = accounts
        self._tokens = {}

    def issue(self, username, now):
        """Return a new single-use reset token for `username`, issued at `now`."""
        if username not in self._accounts:
            raise KeyError(username)
        token = secrets.token_urlsafe(16)
        self._tokens[token] = (username, now)
        return token

    def is_expired(self, token, now):
        """True once TOKEN_TTL has passed since `token` was issued."""
        _username, issued = self._tokens[token]
        return now - issued >= TOKEN_TTL

    def reset_password(self, token, new_password, now):
        """Set a new password for the token's account and return the username.

        The token is single-use and expires TOKEN_TTL after it is issued. Raises TokenError
        for an unknown, already used, or expired token.
        """
        try:
            username, _issued = self._tokens.pop(token)
        except KeyError:
            raise TokenError("unknown or already used token") from None
        self._accounts[username] = _digest(new_password)
        return username
EVAL_FIXTURE_EOF
mkdir -p 'tests'
cat > 'tests/test_expiry.py' <<'EVAL_FIXTURE_EOF'
import unittest
from datetime import datetime, timedelta

from resetkit.tokens import ResetTokens, _digest

T0 = datetime(2026, 1, 1, 12, 0, 0)


class ExpiryTest(unittest.TestCase):
    def setUp(self):
        self.tokens = ResetTokens({"ana": _digest("old")})
        self.token = self.tokens.issue("ana", T0)

    def test_fresh_token_is_not_expired(self):
        self.assertFalse(self.tokens.is_expired(self.token, T0 + timedelta(minutes=29)))

    def test_token_expires_after_30_minutes(self):
        self.assertTrue(self.tokens.is_expired(self.token, T0 + timedelta(minutes=30)))
EVAL_FIXTURE_EOF
git add -A
GIT_AUTHOR_NAME='Eval Fixture' GIT_AUTHOR_EMAIL='fixture@example.invalid' GIT_COMMITTER_NAME='Eval Fixture' GIT_COMMITTER_EMAIL='fixture@example.invalid' git -c commit.gpgsign=false commit -q -m 'Expire reset tokens after 30 minutes (#41)'
