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
