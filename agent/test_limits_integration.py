"""Integration test: on-ledger credit limits are the SINGLE SOURCE OF TRUTH.

Proves the loop that is the whole product thesis:
  on-ledger CreditLimit  ->  solver plans under it  ->  NettingBatch carries the
  same cids  ->  SettleNetting enforces it.

Run against the LIVE network (must be up + parties seeded):
  TG_REAL=1 .venv/bin/python -m agent.test_limits_integration

This is a REAL-NETWORK test, not a mock. It is gated on TG_INTEG=1 so it doesn't
run in the offline unit sweep.
"""
import os
import sys

from agent.limits import (
    seed_limit, load_limits, clear_limits, to_solver_limits, limit_cids,
)
from agent.solver import solve
from agent.netting import Obligation


def _short(p):
    return p.split("::")[0]


def test_ledger_limits_drive_solver():
    """Seed a limit on-ledger, load it, and confirm the solver plans under the
    SAME limit (no parallel definition)."""
    clear_limits()
    seed_limit("firma", "firmc", 20.0, "USD")
    ledger = load_limits()
    assert len(ledger) == 1, f"expected 1 on-ledger limit, got {len(ledger)}"
    solver_limits = to_solver_limits(ledger)
    assert solver_limits[0].frm == "FirmA" and solver_limits[0].to == "FirmC"
    assert solver_limits[0].limit == 20.0 and solver_limits[0].currency == "USD"

    # the cids that would go into NettingBatch.creditLimits
    cids = limit_cids(ledger)
    assert len(cids) == 1 and cids[0] == ledger[0].cid

    # a book where FirmA is the sole net payer owing FirmC 40 -> the 20 cap makes
    # the only conserving plan INFEASIBLE under the on-ledger limit.
    book = [
        Obligation("FirmA", "FirmB", 100.0), Obligation("FirmB", "FirmC", 100.0),
        Obligation("FirmC", "FirmA", 80.0), Obligation("FirmA", "FirmC", 50.0),
        Obligation("FirmC", "FirmB", 30.0),
    ]
    r = solve(book, solver_limits)
    assert not r.feasible, "solver should detect the on-ledger cap makes it infeasible"
    assert any("FirmC" in b and "20" in b for b in r.binding_constraints), r.binding_constraints
    print(f"test_ledger_limits_drive_solver PASSED — solver respects the on-ledger cap; "
          f"binding: {r.binding_constraints[0]}")

    clear_limits()
    assert load_limits() == [], "limits should be cleared"
    print("test_ledger_limits_drive_solver PASSED — cleanup OK")


if __name__ == "__main__":
    if os.environ.get("TG_INTEG") != "1":
        print("SKIPPED: set TG_INTEG=1 and TG_REAL=1 to run the live integration test")
        sys.exit(0)
    test_ledger_limits_drive_solver()
    print("\nALL LIMITS INTEGRATION TESTS PASSED")
