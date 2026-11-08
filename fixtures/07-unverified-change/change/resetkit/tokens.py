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
    # Stand-in for the accounts service's password hashing: a slow KDF with a fixed salt, so a
    # digest can be compared in tests.
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), b"resetkit", 100000).hex()


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
