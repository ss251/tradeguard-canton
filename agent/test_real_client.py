"""Focused command-write resilience tests for the JSON Ledger API client."""
from __future__ import annotations

import io
import json
import unittest
import urllib.error
from unittest.mock import MagicMock, patch

from agent import real_client


class RealLedgerClientWriteTests(unittest.TestCase):
    def setUp(self):
        self.client = real_client.RealLedgerClient("Operator::1")

    @staticmethod
    def _response(body: dict):
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = json.dumps(body).encode()
        return response

    @patch.object(real_client.time, "sleep")
    @patch.object(real_client.urllib.request, "urlopen")
    def test_command_timeout_retries_once_with_90_second_timeout(self, urlopen, sleep):
        urlopen.side_effect = [TimeoutError("timed out"), self._response({"updateId": "u-1"})]

        result = self.client.exercise("TradeGuard.Netting:Obligation", "cid", "Discharge")

        self.assertEqual(result["updateId"], "u-1")
        self.assertEqual(urlopen.call_count, 2)
        self.assertEqual([c.kwargs["timeout"] for c in urlopen.call_args_list], [90, 90])
        sleep.assert_called_once_with(3.0)

    @patch.object(real_client.time, "sleep")
    @patch.object(real_client.urllib.request, "urlopen", side_effect=TimeoutError("timed out"))
    def test_exhausted_timeout_is_an_explicit_write_error(self, urlopen, sleep):
        result = self.client.exercise("TradeGuard.Netting:Obligation", "cid", "Discharge")

        self.assertEqual(result["_http_error"], 598)
        self.assertTrue(result["_timeout"])
        self.assertEqual(urlopen.call_count, 2)
        sleep.assert_called_once_with(3.0)

    @patch.object(real_client.time, "sleep")
    @patch.object(real_client.urllib.request, "urlopen", side_effect=TimeoutError("timed out"))
    def test_exercise_timeout_can_reconcile_committed_ledger_state(self, urlopen, sleep):
        reconciled = MagicMock(return_value={"updateId": None, "_reconciled": True})

        result = self.client.exercise(
            "TradeGuard.Netting:NettingBatch", "batch", "SettleNetting",
            before_retry=reconciled)

        self.assertTrue(result["_reconciled"])
        self.assertEqual(urlopen.call_count, 1)
        reconciled.assert_called_once_with()
        sleep.assert_not_called()

    @patch.object(real_client.time, "sleep")
    @patch.object(real_client.urllib.request, "urlopen")
    def test_logical_4xx_is_not_retried(self, urlopen, sleep):
        urlopen.side_effect = urllib.error.HTTPError(
            "http://ledger", 400, "bad request", {}, io.BytesIO(b"INVALID_ARGUMENT"))

        result = self.client.exercise("TradeGuard.Netting:Obligation", "cid", "Discharge")

        self.assertEqual(result["_http_error"], 400)
        self.assertEqual(urlopen.call_count, 1)
        sleep.assert_not_called()

    @patch.object(real_client.time, "sleep")
    @patch.object(real_client.urllib.request, "urlopen")
    def test_retryable_5xx_retries_once(self, urlopen, sleep):
        urlopen.side_effect = [
            urllib.error.HTTPError(
                "http://ledger", 503, "unavailable", {}, io.BytesIO(b"busy")),
            self._response({"updateId": "u-2"}),
        ]

        result = self.client.exercise("TradeGuard.Netting:Obligation", "cid", "Discharge")

        self.assertEqual(result["updateId"], "u-2")
        self.assertEqual(urlopen.call_count, 2)
        sleep.assert_called_once_with(3.0)

    @patch.object(real_client.time, "sleep")
    @patch.object(real_client.urllib.request, "urlopen", side_effect=TimeoutError("timed out"))
    def test_timed_out_obligation_create_resolves_existing_reference(self, urlopen, sleep):
        existing = {"contractId": "obl-existing", "payload": {
            "payer": "A", "payee": "B", "reference": "A->B inv1"}}
        with patch.object(self.client, "query", return_value=[existing]) as query:
            result = self.client.create(
                "TradeGuard.Netting:Obligation",
                {"payer": "A", "payee": "B", "reference": "A->B inv1"})

        self.assertTrue(result["deduplicatedByReference"])
        self.assertEqual(result["contractId"], "obl-existing")
        self.assertEqual(urlopen.call_count, 1)
        query.assert_called_once_with("TradeGuard.Netting:Obligation", strict=True)
        sleep.assert_not_called()

    @patch.object(real_client.urllib.request, "urlopen")
    def test_strict_query_surfaces_http_failure(self, urlopen):
        urlopen.side_effect = urllib.error.HTTPError(
            "http://ledger", 503, "unavailable", {}, io.BytesIO(b"query failed"))
        with patch.object(self.client, "_ledger_end", return_value=42):
            with self.assertRaisesRegex(RuntimeError, "query failed"):
                self.client.query("TradeGuard.Netting:Obligation", strict=True)

    @patch.object(real_client.time, "sleep")
    @patch.object(real_client.urllib.request, "urlopen", side_effect=TimeoutError("timed out"))
    def test_same_reference_with_different_payload_is_not_certified(self, urlopen, sleep):
        existing = {"contractId": "obl-conflict", "payload": {
            "payer": "A", "payee": "B", "amount": "20", "reference": "ref-1"}}
        with patch.object(self.client, "query", return_value=[existing]):
            result = self.client.create(
                "TradeGuard.Netting:Obligation",
                {"payer": "A", "payee": "B", "amount": 10, "reference": "ref-1"})

        self.assertEqual(result["_http_error"], 409)
        self.assertTrue(result["_reference_conflict"])
        self.assertEqual(urlopen.call_count, 1)
        sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
