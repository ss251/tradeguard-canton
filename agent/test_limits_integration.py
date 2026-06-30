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


def test_fx_lifecycle_live():
    """Seed a co-signed FXRate, load it, confirm the solver values the cross-currency
    book at that exact on-ledger rate, then clear it."""
    from agent.limits import (seed_fx_rate, load_fx_rates, clear_fx_rates, fx_triples)
    from agent.solver import solve_fx, FXRate
    clear_fx_rates()
    seed_fx_rate("EUR", "USD", 1.2, ["firma", "firmb", "firmc"])
    rates = load_fx_rates()
    assert len(rates) == 1, f"expected 1 on-ledger rate, got {len(rates)}"
    assert rates[0].base == "EUR" and rates[0].quote == "USD" and rates[0].rate == 1.2
    # the co-signers must include all three firms
    assert len([p for p in rates[0].parties]) >= 3, rates[0].parties

    solver_rates = [FXRate(b, q, r) for (b, q, r) in fx_triples(rates)]
    book = [Obligation("FirmA", "FirmB", 100.0, "USD"),
            Obligation("FirmB", "FirmA", 50.0, "EUR")]
    r = solve_fx(book, solver_rates, settle_ccy="USD")
    assert r.feasible, r.binding_constraints
    # A owes B 100 USD; B owes A 50 EUR = 60 USD -> net A->B 40 USD
    assert len(r.transfers) == 1 and abs(r.transfers[0].amount - 40.0) < 0.01, r.transfers
    print(f"test_fx_lifecycle_live PASSED — on-ledger rate 1 EUR=1.2 USD drives solver to A->B 40 USD")
    clear_fx_rates()
    assert load_fx_rates() == [], "fx rates should be cleared"
    print("test_fx_lifecycle_live PASSED — cleanup OK")


def test_liquidity_floor_lifecycle_live():
    """Seed an on-ledger LiquidityFloor, load it, confirm the solver enforces it."""
    from agent.limits import (seed_liquidity_floor, load_liquidity_floors,
                              clear_liquidity_floors)
    from agent.solver import solve_fx, FXRate, FloorConstraint
    clear_liquidity_floors()
    seed_liquidity_floor("firma", 50.0, "USD")
    floors = load_liquidity_floors()
    assert len(floors) == 1 and floors[0].floor == 50.0 and floors[0].currency == "USD"
    fc = [FloorConstraint(_short(f.party), f.currency, f.floor) for f in floors]

    # FirmA owes 100, holds 120 -> post 20 < 50 floor -> infeasible
    book = [Obligation("FirmA", "FirmB", 100.0, "USD")]
    rates = [FXRate("EUR", "USD", 1.2)]
    r = solve_fx(book, rates, settle_ccy="USD", floors=fc,
                 balances={("FirmA", "USD"): 120.0})
    assert not r.feasible, "floor breach must be infeasible"
    assert any("floor" in b.lower() for b in r.binding_constraints), r.binding_constraints
    print(f"test_liquidity_floor_lifecycle_live PASSED — {r.binding_constraints[0]}")
    clear_liquidity_floors()
    assert load_liquidity_floors() == [], "floors should be cleared"
    print("test_liquidity_floor_lifecycle_live PASSED — cleanup OK")


def test_maximal_partial_settle_live():
    """THE PRODUCT BEHAVIOUR live: a book + caps that force deferral -> settle_real
    settles the feasible subset and leaves the deferred obligation LIVE on the ledger."""
    from agent.net_settle import seed_partial_book, settle_real
    from agent.real_client import RealLedgerClient, load_real_parties
    seed = seed_partial_book()
    assert seed["ok"], seed
    r = settle_real()  # maximal=True by default
    assert r["ok"], r
    assert r["settled_obligations"] == 1 and r["deferred_obligations"] == 1, r
    assert abs(r["settled_gross"] - 30.0) < 0.01 and abs(r["deferred_gross"] - 25.0) < 0.01, r
    assert r["deferral_reasons"], "must explain the deferral"
    # the deferred obligation must still be live on the ledger (not lost)
    p = load_real_parties()
    live = RealLedgerClient(p["operator"]).query("TradeGuard.Netting:Obligation")
    assert len(live) == 1 and live[0]["payload"]["reference"] == "B->C p2", \
        f"deferred B->C must stay live: {[c['payload']['reference'] for c in live]}"
    print(f"test_maximal_partial_settle_live PASSED — settled 30 ({r['settlement_rate_pct']}%), "
          f"deferred 25 still live on-ledger; reason: {r['deferral_reasons'][0]}")
    # cleanup
    from agent import limits as limmod
    op = RealLedgerClient(p["operator"])
    for c in op.query("TradeGuard.Netting:Obligation"):
        op.exercise("TradeGuard.Netting:Obligation", c["contractId"], "Discharge", {})
    limmod.clear_all(p)
    print("test_maximal_partial_settle_live PASSED — cleanup OK")


if __name__ == "__main__":
    if os.environ.get("TG_INTEG") != "1":
        print("SKIPPED: set TG_INTEG=1 and TG_REAL=1 to run the live integration test")
        sys.exit(0)
    test_ledger_limits_drive_solver()
    test_fx_lifecycle_live()
    test_liquidity_floor_lifecycle_live()
    test_maximal_partial_settle_live()
    print("\nALL LIMITS INTEGRATION TESTS PASSED")
