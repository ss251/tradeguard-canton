"""Multilateral netting — the settlement-optimization brain.

Given a set of bilateral obligations between N parties in a common instrument,
compute each party's NET position and the minimal set of residual transfers that
settles everyone. This is the optimization that makes TradeGuard more than a DvP:
instead of settling every gross obligation, the agent nets them down and settles
only the residuals — atomically, in one batch.

Why this needs Canton: netting requires seeing every party's obligations. On a
transparent chain that means exposing all positions publicly. Here, the netting
operator is an authorized party that the obligations are disclosed to; outsiders
(and even non-involved parties) never see the book. The optimization is only
*possible* because privacy makes it *safe*.

Algorithm:
  1. net[p] = sum(incoming) - sum(outgoing) for each party
  2. parties with net < 0 are payers; net > 0 are receivers
  3. greedily match largest payer to largest receiver -> minimal residual transfers
     (this is the classic min-cash-flow / debt-simplification algorithm)
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Obligation:
    payer: str       # owes
    payee: str       # is owed
    amount: float
    instrument: str = "USD"


@dataclass(frozen=True)
class Transfer:
    sender: str
    receiver: str
    amount: float
    instrument: str = "USD"


def net_positions(obligations: list[Obligation]) -> dict[str, float]:
    """Net position per party: positive = net receiver, negative = net payer."""
    net: dict[str, float] = {}
    for o in obligations:
        net[o.payer] = net.get(o.payer, 0.0) - o.amount
        net[o.payee] = net.get(o.payee, 0.0) + o.amount
    # round to avoid float dust
    return {p: round(v, 2) for p, v in net.items()}


def minimal_settlement(obligations: list[Obligation],
                       instrument: str = "USD") -> list[Transfer]:
    """Compute the minimal set of residual transfers that settles all obligations.

    Classic debt-simplification: net everyone, then match payers to receivers
    greedily by magnitude. Produces at most N-1 transfers for N parties (vs. up to
    N*(N-1) gross), which is the netting efficiency win.
    """
    net = net_positions(obligations)
    payers = sorted(([p, -v] for p, v in net.items() if v < -1e-9),
                    key=lambda x: x[1], reverse=True)   # [party, amount_owed]
    receivers = sorted(([p, v] for p, v in net.items() if v > 1e-9),
                       key=lambda x: x[1], reverse=True)  # [party, amount_due]
    transfers: list[Transfer] = []
    i = j = 0
    while i < len(payers) and j < len(receivers):
        pay = payers[i]
        rec = receivers[j]
        amt = round(min(pay[1], rec[1]), 2)
        if amt > 1e-9:
            transfers.append(Transfer(sender=pay[0], receiver=rec[0],
                                      amount=amt, instrument=instrument))
        pay[1] = round(pay[1] - amt, 2)
        rec[1] = round(rec[1] - amt, 2)
        if pay[1] <= 1e-9:
            i += 1
        if rec[1] <= 1e-9:
            j += 1
    return transfers


def netting_report(obligations: list[Obligation],
                   instrument: str = "USD") -> dict:
    """A full, auditable netting report the agent attaches to its recommendation."""
    gross_count = len(obligations)
    gross_value = round(sum(o.amount for o in obligations), 2)
    net = net_positions(obligations)
    residuals = minimal_settlement(obligations, instrument)
    net_value = round(sum(t.amount for t in residuals), 2)
    saved = round(gross_value - net_value, 2)
    pct = round((saved / gross_value * 100) if gross_value else 0, 1)
    return {
        "instrument": instrument,
        "gross_obligations": gross_count,
        "gross_value": gross_value,
        "net_positions": net,
        "residual_transfers": [
            {"sender": t.sender, "receiver": t.receiver, "amount": t.amount}
            for t in residuals
        ],
        "residual_count": len(residuals),
        "net_value": net_value,
        "value_netted_out": saved,
        "netting_efficiency_pct": pct,
        "rationale": [
            f"{gross_count} gross obligations totaling {gross_value} {instrument}",
            f"netted to {len(residuals)} residual transfer(s) totaling {net_value} {instrument}",
            f"{pct}% of gross value netted out — only residuals must move on-ledger",
            "settled atomically as one SettlementBatch (all-or-nothing)",
        ],
    }
