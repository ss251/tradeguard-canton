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
    def test_reset_demo_reuses_existing_book_batch_and_constraint_clears(self, _parties):
        ledger = Mock()
        ledger.query.side_effect = lambda template: (
            [{"contractId": "obl-1"}, {"contractId": "obl-2"}]
            if template == console_server.OBL_T else [{"contractId": "batch-1"}])
        ledger.exercise.return_value = {}
        constraints = {
            "credit_limits": {"ok": True, "cleared": 1},
            "aggregate_limits": {"ok": True, "cleared": 0},
            "fx_rates": {"ok": True, "cleared": 0},
            "liquidity_floors": {"ok": True, "cleared": 0},
        }
        with patch.object(console_server, "RealLedgerClient", return_value=ledger), \
                patch.object(console_server.limmod, "clear_all", return_value=constraints) as clear_all:
            result = console_server.reset_demo()

        self.assertTrue(result["ok"])
        self.assertEqual(result["cleared"], {"obligations": 2, "batches": 1})
        clear_all.assert_called_once_with(PARTIES)
        self.assertEqual(ledger.exercise.call_count, 3)


if __name__ == "__main__":
    unittest.main()
