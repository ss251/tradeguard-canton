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


def test_maximal_whole_book_when_feasible():
    """When the whole book fits, solve_maximal settles everything (reduces to solve)."""
    from agent.solver import solve_maximal
    book = [Obligation("A", "B", 100.0), Obligation("B", "C", 100.0),
            Obligation("C", "A", 80.0), Obligation("A", "C", 50.0),
            Obligation("C", "B", 30.0)]
    r = solve_maximal(book)
    assert r.feasible
    assert len(r.deferred_obligations) == 0, r.deferred_obligations
    assert len(r.settled_obligations) == 5
    assert r.settlement_rate_pct == 100.0
    assert abs(r.gross_residual - 70.0) < 0.01, r.gross_residual
    print(f"test_maximal_whole_book_when_feasible PASSED — 5/5 settled, {r.gross_residual} residual")


def test_maximal_reroutes_before_deferring():
    """SMART behaviour: when a cap binds but the value can be rerouted (transshipment
    through another party), solve_maximal settles the WHOLE book via the reroute rather
    than deferring — even in cases the simpler solve() refuses."""
    from agent.solver import solve, solve_maximal, CreditLimit
    # canonical book, A is sole net payer (owes C 40, B 30). Cap A->C at 20.
    book = [Obligation("A", "B", 100.0), Obligation("B", "C", 100.0),
            Obligation("C", "A", 80.0), Obligation("A", "C", 50.0),
            Obligation("C", "B", 30.0)]
    cap = [CreditLimit("A", "C", 20.0)]
    # solve() refuses (its residual model only allows payer->receiver arcs)
    assert not solve(book, cap).feasible
    # solve_maximal reroutes A->B->C and settles everything within the cap
    r = solve_maximal(book, cap)
    assert r.feasible and not r.deferred_obligations, \
        f"should reroute, not defer: deferred={r.deferred_obligations}"
    a_to_c = sum(t.amount for t in r.transfers if t.sender == "A" and t.receiver == "C")
    assert a_to_c <= 20.0 + 1e-6, f"A->C {a_to_c} must respect the cap"
    print(f"test_maximal_reroutes_before_deferring PASSED — whole book settled via "
          f"transshipment, A->C held to {a_to_c} (cap 20), 0 deferred")


def test_maximal_degrades_instead_of_refusing():
    """THE PRODUCT BEHAVIOUR: when caps make even a reroute impossible, solve_maximal
    settles the max-value feasible SUBSET and DEFERS the rest with a reason — it never
    hard-fails. Here C is the sole receiver of two obligations and BOTH its inbound arcs
    are capped below what it's owed, so no reroute exists; the rail must defer."""
    from agent.solver import solve, solve_maximal, CreditLimit
    book = [Obligation("A", "C", 30.0), Obligation("B", "C", 25.0)]
    caps = [CreditLimit("A", "C", 30.0), CreditLimit("B", "C", 20.0)]
    # both settled => C owed 55, max inbound 30+20=50 < 55 => infeasible whole-book
    assert not solve(book, caps).feasible
    r = solve_maximal(book, caps)
    assert r.feasible, "maximal never hard-fails"
    # only feasible non-empty subset is {A->C 30} (B->C 25 alone exceeds its 20 cap)
    assert r.settled_obligations == [0], r.settled_obligations
    assert r.deferred_obligations == [1], r.deferred_obligations
    assert abs(r.settled_value - 30.0) < 0.01 and abs(r.deferred_value - 25.0) < 0.01
    assert r.deferral_reasons, "must explain why it deferred"
    print(f"test_maximal_degrades_instead_of_refusing PASSED — "
          f"settled 30 ({r.settlement_rate_pct}% of value), deferred 25; "
          f"reason: {r.deferral_reasons[0]}")


def test_maximal_settled_subset_conserves():
    """The settled subset must itself conserve value per party (so the on-ledger guard,
    which checks conservation over exactly the batch, accepts it)."""
    from agent.solver import solve_maximal, CreditLimit
    book = [Obligation("A", "C", 60.0), Obligation("B", "D", 40.0),
            Obligation("A", "D", 10.0), Obligation("B", "C", 20.0)]
    r = solve_maximal(book, [CreditLimit("A", "C", 30.0)])
    # reconstruct net of the SETTLED obligations and confirm residual reproduces it
    settled = [book[i] for i in r.settled_obligations]
    net = {}
    for o in settled:
        net[o.payer] = net.get(o.payer, 0.0) - o.amount
        net[o.payee] = net.get(o.payee, 0.0) + o.amount
    res_net = {}
    for t in r.transfers:
        res_net[t.sender] = res_net.get(t.sender, 0.0) - t.amount
        res_net[t.receiver] = res_net.get(t.receiver, 0.0) + t.amount
    for p in set(net) | set(res_net):
        assert abs(net.get(p, 0.0) - res_net.get(p, 0.0)) < 0.01, \
            f"settled subset must conserve for {p}: net={net.get(p,0)} res={res_net.get(p,0)}"
    print(f"test_maximal_settled_subset_conserves PASSED — settled subset conserves per-party")


def test_aggregate_limit_defers():
    """AGGREGATE exposure cap: bilateral caps alone cannot catch a firm over-exposed
    in TOTAL. A owes B 60 and C 60 (bilateral caps 80 each — both fine); A's aggregate
    cap of 100 must force a partial settle with total outflow <= 100."""
    from agent.solver import solve_maximal, CreditLimit, AggLimit
    book = [Obligation("A", "B", 60.0), Obligation("A", "C", 60.0)]
    lims = [CreditLimit("A", "B", 80.0), CreditLimit("A", "C", 80.0)]
    aggs = [AggLimit(party="A", limit=100.0)]
    r = solve_maximal(book, lims, agg_limits=aggs)
    total_out = sum(t.amount for t in r.transfers if t.sender == "A")
    assert total_out <= 100.0 + 0.01, f"A's total outflow {total_out} must respect the 100 cap"
    assert len(r.deferred_obligations) >= 1, "must defer at least one obligation"
    assert any("AGGREGATE" in x for x in r.deferral_reasons), \
        f"deferral reason must name the aggregate cap: {r.deferral_reasons}"
    # and with no aggregate cap the whole book settles
    r2 = solve_maximal(book, lims)
    assert not r2.deferred_obligations, "without the agg cap the whole book must settle"
    print(f"test_aggregate_limit_defers PASSED — bilateral caps pass, aggregate cap "
          f"defers (outflow {total_out:g} <= 100); reason: {r.deferral_reasons[0]}")


def test_aggregate_limit_non_binding():
    """An aggregate cap ABOVE the firm's total outflow changes nothing."""
    from agent.solver import solve_maximal, AggLimit
    book = [Obligation("A", "B", 60.0), Obligation("A", "C", 60.0)]
    r = solve_maximal(book, [], agg_limits=[AggLimit(party="A", limit=200.0)])
    assert not r.deferred_obligations, "cap 200 > outflow 120 must not defer anything"
    assert r.settled_value == 120.0
    print("test_aggregate_limit_non_binding PASSED — non-binding aggregate cap is a no-op")


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
    test_maximal_whole_book_when_feasible()
    test_maximal_reroutes_before_deferring()
    test_maximal_degrades_instead_of_refusing()
    test_maximal_settled_subset_conserves()
    test_aggregate_limit_defers()
    test_aggregate_limit_non_binding()
    print("\nALL SOLVER TESTS PASSED")
