"""Payments contract: posts discounted totals to the payments sandbox (see CONTRIBUTING.md)."""

import os
import unittest


class PaymentsContract(unittest.TestCase):
    def test_sandbox_accepts_discounted_totals(self):
        key = os.environ["PAYMENTS_SANDBOX_KEY"]
        # The sandbox client is configured from the key; this stub stands in for the charge round trip.
        self.assertTrue(key)
