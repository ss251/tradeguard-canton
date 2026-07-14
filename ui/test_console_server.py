"""Focused tests for the console state/view switcher and judge reset route support."""
from __future__ import annotations

import unittest
from unittest.mock import Mock, call, patch

from ui import console_server


PARTIES = {
    "operator": "Operator::1", "firma": "FirmA::1", "firmb": "FirmB::1",
    "firmc": "FirmC::1", "netout": "Outsider::1", "netbank": "Bank::1",
}


class ConsoleServerStateTests(unittest.TestCase):
    @patch.object(console_server, "token_state", return_value={"instruments": [], "holdings_total": 0})
    @patch.object(console_server.limmod, "load_agg_limits", return_value=[])
    @patch.object(console_server.limmod, "load_liquidity_floors", return_value=[])
    @patch.object(console_server.limmod, "load_fx_rates", return_value=[])
    @patch.object(console_server.limmod, "load_limits", return_value=[])
    @patch.object(console_server, "_solver_plan", return_value={"feasible": True})
    @patch.object(console_server, "load_real_parties", return_value=PARTIES)
    def test_build_state_exposes_compact_books_by_party(
            self, _parties, _plan, _limits, _fx, _floors, _aggs, _tokens):
        rows = {
            "operator": [{"payer": "FirmA", "payee": "FirmB", "amount": 10.0, "ref": "all"}],
            "firma": [{"payer": "FirmA", "payee": "FirmB", "amount": 10.0, "ref": "all"}],
            "firmb": [{"payer": "FirmA", "payee": "FirmB", "amount": 10.0, "ref": "all"}],
            "firmc": [], "netout": [],
        }
        ledger = Mock()
        ledger.query.return_value = []
        ledger._ledger_end.return_value = 42
        with patch.object(console_server, "_obligations_for", side_effect=lambda key, _p: rows[key]) as books, \
                patch.object(console_server, "RealLedgerClient", return_value=ledger):
            state = console_server.build_state()

        self.assertEqual(set(state["books_by_party"]),
                         {"operator", "firma", "firmb", "firmc", "outsider"})
        self.assertEqual(state["books_by_party"]["operator"], rows["operator"])
        self.assertEqual(state["books_by_party"]["outsider"], [])
        self.assertEqual(state["ledger_offset"], 42)
        self.assertEqual(books.call_args_list, [
            call("operator", PARTIES), call("firma", PARTIES), call("firmb", PARTIES),
            call("firmc", PARTIES), call("netout", PARTIES),
        ])

    @patch.object(console_server, "load_real_parties", return_value=PARTIES)
    def test_reset_demo_uses_ledger_verified_clear_result(self, _parties):
        book = {
            "ok": True,
            "cleared": {"obligations": 2, "batches": 1},
            "book_refs": [],
            "failed_refs": [],
            "last_error": None,
            "errors": [],
        }
        constraints = {
            "credit_limits": {"ok": True, "cleared": 1},
            "aggregate_limits": {"ok": True, "cleared": 0},
            "fx_rates": {"ok": True, "cleared": 0},
            "liquidity_floors": {"ok": True, "cleared": 0},
        }
        with patch.object(console_server.net_settle, "clear_book", return_value=book) as clear_book, \
                patch.object(console_server.limmod, "clear_all", return_value=constraints) as clear_all:
            result = console_server.reset_demo()

        self.assertTrue(result["ok"])
        self.assertEqual(result["cleared"], {"obligations": 2, "batches": 1})
        self.assertEqual(result["failed_refs"], [])
        clear_book.assert_called_once_with(PARTIES)
        clear_all.assert_called_once_with(PARTIES)

    @patch.object(console_server, "_solver_plan", return_value={"feasible": True})
    @patch.object(console_server, "_obligations_for", return_value=[{"ref": "ref-1"}])
    @patch.object(console_server, "load_real_parties", return_value=PARTIES)
    def test_settle_with_approval_stops_before_settlement_on_approval_failure(
            self, _parties, _book, _plan):
        approval = {"ok": False, "approval_recorded": False,
                    "error": "approval write failed: PERMISSION_DENIED"}
        with patch.object(console_server.net_settle, "record_plan_approval",
                          return_value=approval), \
                patch.object(console_server.net_settle, "settle_real") as settle:
            result = console_server.settle_with_approval()

        self.assertFalse(result["ok"])
        self.assertFalse(result["approval_recorded"])
        self.assertIn("PERMISSION_DENIED", result["error"])
        settle.assert_not_called()

    @patch.object(console_server, "_solver_plan", return_value={"feasible": True})
    @patch.object(console_server, "_obligations_for", return_value=[{"ref": "ref-1"}])
    @patch.object(console_server, "load_real_parties", return_value=PARTIES)
    def test_settle_with_approval_threads_receipt_evidence(self, _parties, _book, _plan):
        approval = {
            "ok": True, "approval_recorded": True,
            "approval_trade_id": "NET-1", "approved_action_cid": "approved-cid",
            "approval_update_id": "approval-update",
            "recommendation_cid": "recommendation-cid",
            "recommendation_update_id": "recommendation-update",
        }
        with patch.object(console_server.net_settle, "record_plan_approval",
                          return_value=approval), \
                patch.object(console_server.net_settle, "settle_real",
                             return_value={"ok": True, "batch_cid": "batch-cid"}) as settle:
            result = console_server.settle_with_approval("policy")

        settle.assert_called_once_with(
            "policy", expected_book=[{"ref": "ref-1"}],
            approved_plan={"feasible": True}, approved_action_cid="approved-cid",
            approval_trade_id="NET-1")
        self.assertTrue(result["ok"])
        self.assertTrue(result["approval_recorded"])
        self.assertEqual(result["approved_action_cid"], "approved-cid")
        self.assertEqual(result["approval_update_id"], "approval-update")
        self.assertEqual(result["batch_cid"], "batch-cid")

    @patch.object(console_server, "_solver_plan", return_value={"feasible": True})
    @patch.object(console_server, "_obligations_for", return_value=[{"ref": "ref-1"}])
    @patch.object(console_server, "load_real_parties", return_value=PARTIES)
    def test_settle_failure_after_approval_is_reported_exactly(self, _parties, _book, _plan):
        approval = {
            "ok": True, "approval_recorded": True,
            "approved_action_cid": "approved-cid", "approval_update_id": "approval-update",
        }
        with patch.object(console_server.net_settle, "record_plan_approval",
                          return_value=approval), \
                patch.object(console_server.net_settle, "settle_real",
                             return_value={"ok": False, "error": "settle failed: ABORTED"}):
            result = console_server.settle_with_approval()

        self.assertFalse(result["ok"])
        self.assertTrue(result["approval_recorded"])
        self.assertIn("approval recorded on-ledger", result["error"])
        self.assertIn("nothing moved", result["error"])
        self.assertEqual(result["settlement_error"], "settle failed: ABORTED")

    def test_attach_state_preserves_receipt_when_refresh_fails(self):
        receipt = {"ok": True, "approved_action_cid": "approved-cid"}
        with patch.object(console_server, "build_state", side_effect=RuntimeError("read failed")):
            result = console_server._attach_state(receipt)

        self.assertTrue(result["ok"])
        self.assertEqual(result["approved_action_cid"], "approved-cid")
        self.assertEqual(result["state_error"], "read failed")
        self.assertNotIn("state", result)


if __name__ == "__main__":
    unittest.main()
