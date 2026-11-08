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
