"""Focused ledger-truth and ApprovedAction tests for the console settlement helpers."""
from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from agent import net_settle


PARTIES = {
    "operator": "Operator::1", "firma": "FirmA::1", "firmb": "FirmB::1",
    "firmc": "FirmC::1", "netbank": "Bank::1",
}


class _LedgerState:
    def __init__(self, obligations=None, missing_refs=None):
        self.obligations = list(obligations or [])
        self.batches = []
        self.missing_refs = set(missing_refs or [])
        self.next_cid = 1


class _FakeClient:
    def __init__(self, party, state):
        self.party = party
        self.state = state

    def query(self, template, strict=False):
        if template == net_settle.OBLIGATION_T:
            return [dict(c, payload=dict(c["payload"])) for c in self.state.obligations]
        if template == net_settle.BATCH_T:
            return list(self.state.batches)
        return []

    def exercise(self, template, contract_id, _choice, _argument, act_as=None):
        rows = self.state.obligations if template == net_settle.OBLIGATION_T else self.state.batches
        rows[:] = [c for c in rows if c["contractId"] != contract_id]
        return {"updateId": f"archive-{contract_id}"}

    def create(self, template, payload, act_as=None):
        reference = payload["reference"]
        if reference not in self.state.missing_refs:
            self.state.obligations.append({
                "contractId": f"new-{self.state.next_cid}",
                "payload": dict(payload),
            })
            self.state.next_cid += 1
        # The command response alone is deliberately not treated as proof by the helper.
        return {"updateId": f"create-{reference}"}


class NetSettleTruthTests(unittest.TestCase):
    def _factory(self, state):
        return lambda party: _FakeClient(party, state)

    def test_seed_sweeps_junk_and_counts_from_final_query(self):
        state = _LedgerState(obligations=[
            {"contractId": "junk-1", "payload": {"reference": "probe-verbatim"}},
        ])
        book = [
            (PARTIES["firma"], PARTIES["firmb"], 10.0, "ref-1"),
            (PARTIES["firmb"], PARTIES["firmc"], 20.0, "ref-2"),
        ]
        with patch.object(net_settle, "RealLedgerClient", side_effect=self._factory(state)):
            result = net_settle._seed_obligation_book(PARTIES, book)

        self.assertTrue(result["ok"])
        self.assertEqual(result["created"], 2)
        self.assertEqual(result["cleared"], {"obligations": 1, "batches": 0})
        self.assertEqual(result["book_refs"], ["ref-1", "ref-2"])
        self.assertNotIn("probe-verbatim", result["book_refs"])

    def test_seed_reports_missing_reference_even_when_create_response_succeeds(self):
        state = _LedgerState(missing_refs={"ref-2"})
        book = [
            (PARTIES["firma"], PARTIES["firmb"], 10.0, "ref-1"),
            (PARTIES["firmb"], PARTIES["firmc"], 20.0, "ref-2"),
        ]
        with patch.object(net_settle, "RealLedgerClient", side_effect=self._factory(state)):
            result = net_settle._seed_obligation_book(PARTIES, book)

        self.assertFalse(result["ok"])
        self.assertEqual(result["created"], 1)
        self.assertEqual(result["failed_refs"], ["ref-2"])
        self.assertIn("ledger book does not match", result["last_error"])

    @patch.object(net_settle.os, "urandom", return_value=b"abc")
    @patch.object(net_settle, "load_real_parties", return_value=PARTIES)
    def test_record_plan_approval_returns_approved_action_evidence(self, _parties, _random):
        operator = Mock()
        operator._ledger_end.return_value = 42
        operator.create_tree.return_value = {
            "updateId": "recommendation-update",
            "transactionTree": {"eventsById": {"0": {"CreatedTreeEvent": {"value": {
                "contractId": "recommendation-cid",
                "templateId": "#tradeguard:TradeGuard.Agent:SettlementRecommendation",
            }}}}},
        }
        operator.exercise_tree.return_value = {
            "updateId": "approval-update",
            "transactionTree": {"eventsById": {"0": {"CreatedTreeEvent": {"value": {
                "contractId": "approved-action-cid",
                "templateId": "#tradeguard:TradeGuard.Agent:ApprovedAction",
            }}}}},
        }
        plan = {
            "gross_obligations": 565.0,
            "gross_residual": 100.0,
            "netting_efficiency_pct": 82.3,
            "residual_transfers": [
                {"sender": "FirmA", "receiver": "FirmB", "amount": 25.0},
                {"sender": "FirmA", "receiver": "FirmC", "amount": 75.0},
            ],
        }
        with patch.object(net_settle, "RealLedgerClient", return_value=operator):
            result = net_settle.record_plan_approval(plan)

        self.assertTrue(result["ok"])
        self.assertEqual(result["approved_action_cid"], "approved-action-cid")
        self.assertEqual(result["approval_update_id"], "approval-update")
        create_payload = operator.create_tree.call_args.args[1]
        self.assertEqual(create_payload["decision"], "SETTLE")
        self.assertIn("Gross obligations: 565 USD", create_payload["rationale"])
        self.assertIn("Net residual: 100 USD", create_payload["rationale"])
        exercise = operator.exercise_tree.call_args
        self.assertEqual(exercise.args,
                         (net_settle.RECOMMENDATION_T, "recommendation-cid", "Approve", {}))
        self.assertEqual(exercise.kwargs["act_as"], [PARTIES["operator"]])
        self.assertTrue(callable(exercise.kwargs["before_retry"]))


if __name__ == "__main__":
    unittest.main()
