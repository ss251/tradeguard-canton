"""Focused fail-closed tests for on-ledger constraint reads and clears."""
from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from agent import limits


PARTIES = {"operator": "Operator::1", "firma": "FirmA::1"}


class LimitVerificationTests(unittest.TestCase):
    def test_load_limits_uses_strict_acs_read(self):
        ledger = Mock()
        ledger.query.return_value = []
        with patch.object(limits, "RealLedgerClient", return_value=ledger):
            self.assertEqual(limits.load_limits(PARTIES), [])
        ledger.query.assert_called_once_with(limits.CREDIT_LIMIT_T, strict=True)

    def test_clear_verified_counts_from_final_ledger_truth(self):
        ledger = Mock()
        contract = {"contractId": "limit-1", "payload": {"from": "FirmA::1"}}
        ledger.query.side_effect = [[contract], []]
        ledger.exercise.return_value = {"updateId": "archive-update"}
        with patch.object(limits, "RealLedgerClient", return_value=ledger):
            result = limits.clear_limits(PARTIES)

        self.assertTrue(result["ok"])
        self.assertEqual(result["cleared"], 1)
        self.assertEqual(result["failed_refs"], [])
        self.assertEqual(ledger.query.call_count, 2)

    def test_clear_verified_fails_closed_when_initial_query_fails(self):
        ledger = Mock()
        ledger.query.side_effect = RuntimeError("ACS unavailable")
        with patch.object(limits, "RealLedgerClient", return_value=ledger):
            result = limits.clear_limits(PARTIES)

        self.assertFalse(result["ok"])
        self.assertEqual(result["cleared"], 0)
        self.assertIn("initial constraint query failed", result["last_error"])
        ledger.exercise.assert_not_called()


if __name__ == "__main__":
    unittest.main()
