"""The settlement reasoner: the agent's decision logic.

Given the Coordinator's view of the ledger, decide for each accepted trade whether
it is READY to settle, must WAIT (a condition is unmet), or should be CANCELLED
(a condition has failed/expired). Every decision carries an explicit, auditable
rationale — the agent never acts on a hunch.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Decision(str, Enum):
    SETTLE = "SETTLE"      # all conditions met -> recommend settlement
    WAIT = "WAIT"          # a condition is not yet met -> hold
    CANCEL = "CANCEL"      # a condition failed/expired -> recommend cancellation


@dataclass
class Reasoning:
    decision: Decision
    trade_id: str
    rationale: list[str] = field(default_factory=list)
    checks: dict[str, bool] = field(default_factory=dict)

    def add(self, name: str, passed: bool, detail: str) -> None:
        self.checks[name] = passed
        mark = "PASS" if passed else "WAIT"
        self.rationale.append(f"[{mark}] {name}: {detail}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "tradeId": self.trade_id,
            "decision": self.decision.value,
            "checks": self.checks,
            "rationale": self.rationale,
        }


def evaluate_trade(
    accepted: dict,
    attestations: list[dict],
    requires_attestation: bool,
) -> Reasoning:
    """Evaluate one AcceptedTrade for settlement readiness.

    `accepted` is the contract payload of an AcceptedTrade. `attestations` are the
    DeliveryAttestation payloads visible to the coordinator.
    """
    payload = accepted["payload"]
    trade_id = payload["tradeId"]
    if isinstance(trade_id, dict):  # Id is {"unpack": "..."} or plain
        trade_id = trade_id.get("unpack", str(trade_id))
    r = Reasoning(decision=Decision.WAIT, trade_id=str(trade_id))

    legs = payload.get("legs", [])

    # Check 1: structural — exactly two legs (asset + cash) for a bilateral DvP.
    two_legs = len(legs) == 2
    r.add("two_legs", two_legs,
          f"{len(legs)} leg(s) present (expect 2: asset + cash)")

    # Check 2: legs balance — each leg has a positive amount.
    amounts_ok = all(float(leg.get("amount", 0)) > 0 for leg in legs)
    r.add("positive_amounts", amounts_ok,
          "all leg amounts are positive" if amounts_ok else "a leg has non-positive amount")

    # Check 3: opposing direction — leg senders/receivers form a swap.
    swap_ok = False
    if two_legs:
        a, b = legs
        swap_ok = (a["sender"] == b["receiver"] and a["receiver"] == b["sender"])
    r.add("is_swap", swap_ok,
          "legs form a counterparty swap" if swap_ok else "legs do not form a clean swap")

    # Check 4: delivery attestation (conditional settlement gate).
    if requires_attestation:
        matched = [
            att for att in attestations
            if _norm(att["payload"].get("tradeId")) == str(trade_id)
        ]
        attested = len(matched) > 0
        r.add("delivery_attested", attested,
              f"delivery attestation present ({len(matched)} match)"
              if attested else "awaiting delivery attestation from registry")
    else:
        r.add("delivery_attested", True, "trade does not require attestation")

    # Decide.
    all_pass = all(r.checks.values())
    if all_pass:
        r.decision = Decision.SETTLE
        r.rationale.append("DECISION: all conditions met -> recommend SETTLE "
                           "(pending human authorization).")
    else:
        # If structural checks fail (not just a pending attestation), it's bad data.
        structural = ["two_legs", "positive_amounts", "is_swap"]
        if not all(r.checks.get(c, False) for c in structural):
            r.decision = Decision.CANCEL
            r.rationale.append("DECISION: structural validation failed -> recommend "
                               "CANCEL (release any locks).")
        else:
            r.decision = Decision.WAIT
            r.rationale.append("DECISION: conditions pending -> WAIT and keep monitoring.")
    return r


def _norm(idval: Any) -> str:
    if isinstance(idval, dict):
        return str(idval.get("unpack", idval))
    return str(idval)
