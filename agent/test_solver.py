"""Tests for the constrained netting solver. Run: python3 -m agent.test_solver

Covers:
  * unconstrained solve reproduces the canonical 360->70 (80.6%) net,
  * conservation holds per-currency (residuals reproduce exact net positions),
  * multi-currency books net each currency INDEPENDENTLY,
  * a binding credit limit forces a genuine REROUTE (different valid plan),
  * an over-tight credit limit yields INFEASIBLE + the binding constraint,
  * objective weights steer the plan among equally-conserving options.
"""
from agent.netting import Obligation
from agent.solver import solve, solve_report, CreditLimit, SolvedTransfer


def approx(a, b, tol=0.01):
    return abs(a - b) < tol


def _reproduces_net(transfers: list[SolvedTransfer], net: dict[str, float]) -> bool:
    repro: dict[str, float] = {}
    for t in transfers:
        repro[t.sender] = repro.get(t.sender, 0.0) - t.amount
        repro[t.receiver] = repro.get(t.receiver, 0.0) + t.amount
    return all(approx(net.get(p, 0.0), repro.get(p, 0.0)) for p in net)


def test_unconstrained_matches_canonical():
    """No limits: the solver nets the canonical book to 70 residual (80.6%)."""
    book = [
        Obligation("A", "B", 100.0), Obligation("B", "C", 100.0),
        Obligation("C", "A", 80.0), Obligation("A", "C", 50.0),
        Obligation("C", "B", 30.0),
    ]
    r = solve(book)
    assert r.feasible
    assert approx(r.gross_obligations, 360.0)
    assert approx(r.gross_residual, 70.0), f"expected 70 residual, got {r.gross_residual}"
    assert approx(r.netting_efficiency_pct, 80.6), r.netting_efficiency_pct
    assert _reproduces_net(r.transfers, r.net_positions["USD"]), "residuals must reproduce net"
    print("test_unconstrained_matches_canonical PASSED — 360 -> 70 (80.6%)")


def test_multi_currency_independent():
    """USD and EUR net independently; a USD residual never offsets a EUR debt."""
    book = [
        Obligation("A", "B", 100.0, "USD"),
        Obligation("B", "A", 40.0, "USD"),
        Obligation("B", "A", 50.0, "EUR"),
    ]
    r = solve(book)
    assert r.feasible
    usd = [t for t in r.transfers if t.currency == "USD"]
    eur = [t for t in r.transfers if t.currency == "EUR"]
    # USD: A net -60 -> A pays B 60 ; EUR: B net -50 -> B pays A 50
    assert len(usd) == 1 and usd[0].sender == "A" and usd[0].receiver == "B" and approx(usd[0].amount, 60.0), usd
    assert len(eur) == 1 and eur[0].sender == "B" and eur[0].receiver == "A" and approx(eur[0].amount, 50.0), eur
    assert _reproduces_net(usd, r.net_positions["USD"])
    assert _reproduces_net(eur, r.net_positions["EUR"])
    print("test_multi_currency_independent PASSED — USD(A->B 60) & EUR(B->A 50) netted separately")


def test_credit_limit_reroute():
    """With 2 payers / 2 receivers, a credit limit on one arc forces a reroute.

    Book: A->C 60, B->D 40, A->D 10, B->C 20.
      net: A -70, B -60 (payers); C +80, D +50 (receivers).
    Unconstrained, the solver could send A->C up to 70. Cap A->C <= 30 and the
    solver must reroute C's funding through B instead — a different, still-conserving
    plan. C must still receive exactly 80, D exactly 50.
    """
    book = [
        Obligation("A", "C", 60.0), Obligation("B", "D", 40.0),
        Obligation("A", "D", 10.0), Obligation("B", "C", 20.0),
    ]
    r = solve(book, [CreditLimit("A", "C", 30.0)])
    assert r.feasible, f"should be feasible by rerouting: {r.binding_constraints}"
    a_to_c = sum(t.amount for t in r.transfers if t.sender == "A" and t.receiver == "C")
    assert a_to_c <= 30.0 + 1e-6, f"A->C must respect cap 30, got {a_to_c}"
    # receivers fully funded
    c_in = sum(t.amount for t in r.transfers if t.receiver == "C")
    d_in = sum(t.amount for t in r.transfers if t.receiver == "D")
    assert approx(c_in, 80.0), f"C must receive 80, got {c_in}"
    assert approx(d_in, 50.0), f"D must receive 50, got {d_in}"
    assert _reproduces_net(r.transfers, r.net_positions["USD"])
    print(f"test_credit_limit_reroute PASSED — A->C capped at 30 (was {a_to_c}), C still funded 80")


def test_infeasible_returns_binding_constraint():
    """Cap the sole payer's only viable arc below what a receiver is owed -> INFEASIBLE,
    and the solver explains exactly why (the binding constraint)."""
    book = [
        Obligation("A", "B", 100.0), Obligation("B", "C", 100.0),
        Obligation("C", "A", 80.0), Obligation("A", "C", 50.0),
        Obligation("C", "B", 30.0),
    ]  # A is sole payer; C owed 40, B owed 30
    r = solve(book, [CreditLimit("A", "C", 20.0)])
    assert not r.feasible, "capping A->C below C's due must be infeasible"
    assert r.binding_constraints, "must surface the binding constraint"
    joined = " ".join(r.binding_constraints)
    assert "C is owed 40" in joined and "20" in joined, joined
    print(f"test_infeasible_returns_binding_constraint PASSED — {r.binding_constraints[0]}")


def test_objective_weights_steer_plan():
    """Policy weights steer the plan among equally-conserving options without
    breaking conservation. Penalize A->C heavily; the solver should prefer to fund
    C via B (when a reroute exists) while still settling everyone exactly."""
    book = [
        Obligation("A", "C", 60.0), Obligation("B", "D", 40.0),
        Obligation("A", "D", 10.0), Obligation("B", "C", 20.0),
    ]
    # heavy penalty on A->C; B->C is the alternative funding path for C
    r = solve(book, objective_weights={("A", "C"): 100.0})
    assert r.feasible
    a_to_c = sum(t.amount for t in r.transfers if t.sender == "A" and t.receiver == "C")
    b_to_c = sum(t.amount for t in r.transfers if t.sender == "B" and t.receiver == "C")
    # with the penalty, the solver should route as much of C's funding via B as B can
    assert b_to_c >= a_to_c, f"policy should prefer B->C over A->C: A->C={a_to_c}, B->C={b_to_c}"
    assert _reproduces_net(r.transfers, r.net_positions["USD"]), "conservation must still hold"
    print(f"test_objective_weights_steer_plan PASSED — penalized A->C={a_to_c}, favored B->C={b_to_c}")


def test_report_shape():
    """solve_report returns a JSON-serializable dict with the fields the UI needs."""
    book = [Obligation("A", "B", 100.0), Obligation("B", "A", 40.0)]
    rep = solve_report(book)
    for key in ("feasible", "gross_obligations", "gross_residual",
                "netting_efficiency_pct", "net_positions", "residual_transfers",
                "binding_constraints", "rationale"):
        assert key in rep, f"missing {key}"
    import json
    json.dumps(rep)  # must be serializable
    print("test_report_shape PASSED — report is well-formed and JSON-serializable")


def test_fx_cross_currency_netting():
    """USD + EUR netted by VALUE at an agreed rate, settled in USD."""
    from agent.solver import FXRate, solve_fx
    book = [Obligation("A", "B", 100.0, "USD"), Obligation("B", "A", 50.0, "EUR")]
    rates = [FXRate("EUR", "USD", 1.2)]
    r = solve_fx(book, rates, settle_ccy="USD")
    assert r.feasible, r.binding_constraints
    # A owes B 100 USD; B owes A 50 EUR = 60 USD -> A net owes B 40 USD
    assert len(r.transfers) == 1, r.transfers
    t = r.transfers[0]
    assert t.sender == "A" and t.receiver == "B" and abs(t.amount - 40.0) < 0.01, r.transfers
    assert t.currency == "USD"
    print("test_fx_cross_currency_netting PASSED — 100 USD vs 50 EUR @1.2 -> A->B 40 USD")


def test_fx_inverse_rate():
    """The inverse direction (USD->EUR via a EUR->USD rate) values correctly."""
    from agent.solver import FXRate, fx_factor
    rates = [FXRate("EUR", "USD", 1.25)]
    assert abs(fx_factor("USD", rates, "EUR") - 1.25) < 1e-9
    assert abs(fx_factor("EUR", rates, "USD") - 0.8) < 1e-9   # 1/1.25
    assert fx_factor("USD", rates, "USD") == 1.0
    assert fx_factor("USD", rates, "GBP") is None             # no agreed path
    print("test_fx_inverse_rate PASSED — direct, inverse, identity, and missing-path all correct")


def test_fx_missing_rate_infeasible():
    """A currency with no agreed path to the settlement currency => infeasible."""
    from agent.solver import FXRate, solve_fx
    book = [Obligation("A", "B", 100.0, "USD"), Obligation("B", "A", 50.0, "GBP")]
    rates = [FXRate("EUR", "USD", 1.2)]  # nothing connects GBP
    r = solve_fx(book, rates, settle_ccy="USD")
    assert not r.feasible
    assert any("GBP" in b for b in r.binding_constraints), r.binding_constraints
    print("test_fx_missing_rate_infeasible PASSED — missing FX path correctly refused")


def test_liquidity_floor_constraint():
    """A liquidity floor the plan would breach => infeasible with the binding floor."""
    from agent.solver import FXRate, FloorConstraint, solve_fx
    book = [Obligation("A", "B", 100.0, "USD")]
    rates = [FXRate("EUR", "USD", 1.2)]  # unused but FX mode
    floors = [FloorConstraint("A", "USD", 50.0)]
    balances = {("A", "USD"): 120.0}     # 120 - 100 = 20 < 50
    r = solve_fx(book, rates, settle_ccy="USD", floors=floors, balances=balances)
    assert not r.feasible, "A draining below its floor must be infeasible"
    assert any("floor" in b.lower() for b in r.binding_constraints), r.binding_constraints
    print(f"test_liquidity_floor_constraint PASSED — {r.binding_constraints[0]}")


def test_liquidity_floor_satisfiable():
    """Same book but a higher pre-balance keeps the party above its floor."""
    from agent.solver import FXRate, FloorConstraint, solve_fx
    book = [Obligation("A", "B", 100.0, "USD")]
    rates = [FXRate("EUR", "USD", 1.2)]
    floors = [FloorConstraint("A", "USD", 50.0)]
    balances = {("A", "USD"): 200.0}     # 200 - 100 = 100 >= 50
    r = solve_fx(book, rates, settle_ccy="USD", floors=floors, balances=balances)
    assert r.feasible, r.binding_constraints
    assert len(r.transfers) == 1 and abs(r.transfers[0].amount - 100.0) < 0.01
    print("test_liquidity_floor_satisfiable PASSED — floor respected, settles normally")


if __name__ == "__main__":
    test_unconstrained_matches_canonical()
    test_multi_currency_independent()
    test_credit_limit_reroute()
    test_infeasible_returns_binding_constraint()
    test_objective_weights_steer_plan()
    test_report_shape()
    test_fx_cross_currency_netting()
    test_fx_inverse_rate()
    test_fx_missing_rate_infeasible()
    test_liquidity_floor_constraint()
    test_liquidity_floor_satisfiable()
    print("\nALL SOLVER TESTS PASSED")
