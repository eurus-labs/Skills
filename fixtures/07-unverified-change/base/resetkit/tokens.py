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
