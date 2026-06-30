"""Netting-cycle lifecycle — the rail's operating rhythm, driven from the agent.

The maximal-netting settle (agent.net_settle.settle_real) settles the feasible subset
and DEFERS the rest. But "defer to the next cycle" only means something if there IS a
next cycle. This module is the on-ledger session container that makes that real:

    open  -> a NettingCycle (CycleOpen) starts accruing the book
    close -> CloseCycle snapshots the book (CycleOpen -> CycleClosed)
    settle-> run maximal netting; settle the feasible subset; RecordSettlement
             writes the durable, regulator-observable outcome (CycleClosed -> CycleSettled)
    roll  -> RollForward opens the successor cycle (n -> n+1); the deferred obligations
             are already live on the ledger and are caught at the next close.

The on-ledger NettingCycle enforces the state machine (you cannot record settlement on
an open cycle, cannot roll forward before settling), so the rhythm is not just a Python
convention — it is guaranteed by the ledger.
"""
from __future__ import annotations

from agent.real_client import RealLedgerClient, load_real_parties
from agent.net_settle import _err, _tree_created_cid

CYCLE_T = "TradeGuard.Netting:NettingCycle"


def current_cycle(parties: dict | None = None) -> dict | None:
    """Return the latest (highest-numbered) NettingCycle the operator can see, or None."""
    parties = parties or load_real_parties()
    op = RealLedgerClient(parties["operator"])
    rows = op.query(CYCLE_T)
    if not rows:
        return None
    best = max(rows, key=lambda c: int(c["payload"]["cycleNumber"]))
    pl = best["payload"]
    return {"cid": best["contractId"], "cycleNumber": int(pl["cycleNumber"]),
            "status": pl["status"], "settledCount": int(pl["settledCount"]),
            "deferredCount": int(pl["deferredCount"]),
            "settledValue": float(pl["settledValue"]),
            "deferredValue": float(pl["deferredValue"])}


def open_cycle(parties: dict | None = None) -> dict:
    """Open the first cycle (number 1) if none exists. Idempotent-ish: if an Open or
    Closed cycle already exists, returns it rather than creating a duplicate."""
    parties = parties or load_real_parties()
    operator = parties["operator"]
    cur = current_cycle(parties)
    if cur and cur["status"] in ("CycleOpen", "CycleClosed"):
        return {"ok": True, "cycle": cur, "note": "already in progress"}
    number = (cur["cycleNumber"] + 1) if cur else 1
    op = RealLedgerClient(operator)
    r = op.create_tree(CYCLE_T, {
        "operator": operator, "cycleNumber": number, "status": "CycleOpen",
        "regulator": parties.get("netreg"),
        "settledCount": 0, "deferredCount": 0,
        "settledValue": "0.0", "deferredValue": "0.0"})
    e = _err(r)
    if e:
        return {"ok": False, "error": e}
    return {"ok": True, "cycle": current_cycle(parties)}


def run_cycle(policy_text: str | None = None, parties: dict | None = None) -> dict:
    """Run ONE full cycle end-to-end on the live network:

      ensure an Open cycle -> CloseCycle -> maximal-netting settle (settle feasible
      subset, defer rest) -> RecordSettlement -> RollForward to the next Open cycle.

    Returns the settlement result plus the cycle numbers (this cycle settled, next
    cycle opened). The deferred obligations are caught by the next run_cycle().
    """
    parties = parties or load_real_parties()
    operator = parties["operator"]
    op = RealLedgerClient(operator)

    # 1. ensure an Open cycle
    cur = current_cycle(parties)
    if not cur or cur["status"] == "CycleSettled":
        opened = open_cycle(parties)
        if not opened["ok"]:
            return {"ok": False, "error": f"open failed: {opened.get('error')}"}
        cur = opened["cycle"]
    if cur["status"] == "CycleOpen":
        # 2. close the book
        rc = op.exercise(CYCLE_T, cur["cid"], "CloseCycle", {})
        if _err(rc):
            return {"ok": False, "error": f"close failed: {_err(rc)}"}
        cur = current_cycle(parties)
    if not cur or cur["status"] != "CycleClosed":
        return {"ok": False, "error": f"expected a Closed cycle, got {cur}"}
    # cur is now Closed
    cycle_number = cur["cycleNumber"]

    # 3. maximal-netting settle (settles the feasible subset; defers the rest)
    from agent.net_settle import settle_real
    settle = settle_real(policy_text, maximal=True)

    # extract settled/deferred from the settle result (works for ok or all-deferred)
    sc = settle.get("settled_obligations", 0) if settle.get("ok") else settle.get("settled", 0)
    dc = settle.get("deferred_obligations", 0) if settle.get("ok") else settle.get("deferred", 0)
    sv = settle.get("settled_gross", 0.0)
    dv = settle.get("deferred_gross", 0.0)

    # 4. record the outcome on the cycle (Closed -> Settled)
    closed = current_cycle(parties)
    if not closed:
        return {"ok": False, "error": "cycle vanished before RecordSettlement", "settle": settle}
    rr = op.exercise(CYCLE_T, closed["cid"], "RecordSettlement",
                     {"sc": int(sc), "dc": int(dc),
                      "sv": str(sv), "dv": str(dv)})
    if _err(rr):
        return {"ok": False, "error": f"record failed: {_err(rr)}", "settle": settle}

    # 5. roll forward to the next cycle
    settled = current_cycle(parties)
    if not settled:
        return {"ok": False, "error": "cycle vanished before RollForward", "settle": settle}
    rf = op.exercise(CYCLE_T, settled["cid"], "RollForward", {})
    if _err(rf):
        return {"ok": False, "error": f"roll-forward failed: {_err(rf)}", "settle": settle}
    nxt = current_cycle(parties)

    return {
        "ok": True,
        "cycle": cycle_number,
        "settled_obligations": int(sc),
        "deferred_obligations": int(dc),
        "settled_value": float(sv),
        "deferred_value": float(dv),
        "settlement_rate_pct": settle.get("settlement_rate_pct", 100.0),
        "deferral_reasons": settle.get("deferral_reasons", []),
        "next_cycle": nxt["cycleNumber"] if nxt else cycle_number + 1,
        "next_status": nxt["status"] if nxt else "CycleOpen",
        "settle": {k: settle.get(k) for k in
                   ("ok", "settled_gross", "deferred_gross", "residuals")},
    }


if __name__ == "__main__":
    import json
    import sys
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    if action == "open":
        print(json.dumps(open_cycle(), indent=2))
    elif action == "run":
        print(json.dumps(run_cycle(), indent=2))
    else:
        print(json.dumps(current_cycle() or {"note": "no cycle yet"}, indent=2))
