"""Tests for the LLM policy layer. Run: python3 -m agent.test_policy

These exercise the DETERMINISTIC rules backend (prefer_llm=False) so they pass
offline and are repeatable. The LLM backend is validated separately/manually
(test_llm_backend, only runs when TG_TEST_LLM=1) because it needs network + the
claude CLI and costs tokens.

The contract under test: NL policy -> validated structured Policy whose
(objective_weights, credit_limits) feed the solver, with unknown/garbled input
degrading to source='invalid' (never a fabricated plan).
"""
import os

from agent.policy import PolicyContext, parse_policy
from agent.solver import solve, Obligation

CTX = PolicyContext(parties=["FirmA", "FirmB", "FirmC", "FirmD"], currencies=["USD", "EUR"])


def test_minimize_exposure_to_weight():
    p = parse_policy("minimize FirmA's exposure to FirmC", CTX, prefer_llm=False)
    assert p.valid
    assert p.objective_weights.get(("FirmA", "FirmC"), 0) > 0, p.to_dict()
    assert not p.credit_limits
    print("test_minimize_exposure_to_weight PASSED")


def test_strongly_avoid_is_higher_weight():
    weak = parse_policy("avoid FirmA paying FirmC", CTX, prefer_llm=False)
    strong = parse_policy("strongly avoid FirmA paying FirmC", CTX, prefer_llm=False)
    assert strong.objective_weights[("FirmA", "FirmC")] > weak.objective_weights[("FirmA", "FirmC")]
    print("test_strongly_avoid_is_higher_weight PASSED")


def test_cap_clause_to_credit_limit():
    p = parse_policy("cap what FirmA owes FirmB at 50 USD", CTX, prefer_llm=False)
    assert p.valid and len(p.credit_limits) == 1, p.to_dict()
    cl = p.credit_limits[0]
    assert cl.frm == "FirmA" and cl.to == "FirmB" and cl.limit == 50.0 and cl.currency == "USD"
    print("test_cap_clause_to_credit_limit PASSED")


def test_currency_parsed():
    p = parse_policy("cap FirmA owes FirmB at 30 EUR", CTX, prefer_llm=False)
    assert p.credit_limits and p.credit_limits[0].currency == "EUR", p.to_dict()
    print("test_currency_parsed PASSED")


def test_compound_policy():
    p = parse_policy(
        "strongly avoid FirmB paying FirmC and cap FirmA owes FirmC at 20",
        CTX, prefer_llm=False)
    assert p.objective_weights.get(("FirmB", "FirmC"), 0) == 10.0
    assert any(cl.frm == "FirmA" and cl.to == "FirmC" and cl.limit == 20.0
               for cl in p.credit_limits), p.to_dict()
    print("test_compound_policy PASSED")


def test_unknown_party_dropped_or_invalid():
    # "FirmZ" is not in the book -> that clause is dropped; nothing else -> invalid
    p = parse_policy("minimize FirmA exposure to FirmZ", CTX, prefer_llm=False)
    assert not p.valid or ("FirmA", "FirmZ") not in p.objective_weights
    print("test_unknown_party_dropped_or_invalid PASSED")


def test_gibberish_is_invalid():
    p = parse_policy("make me a sandwich", CTX, prefer_llm=False)
    assert not p.valid, p.to_dict()
    assert p.errors
    print("test_gibberish_is_invalid PASSED")


def test_empty_policy_is_valid_noop():
    p = parse_policy("", CTX, prefer_llm=False)
    assert p.valid and not p.objective_weights and not p.credit_limits
    print("test_empty_policy_is_valid_noop PASSED")


def test_policy_feeds_solver_end_to_end():
    """The policy's outputs must actually steer the solver and stay conserving."""
    book = [
        Obligation("A", "C", 60.0), Obligation("B", "D", 40.0),
        Obligation("A", "D", 10.0), Obligation("B", "C", 20.0),
    ]
    ctx = PolicyContext(parties=["A", "B", "C", "D"])
    p = parse_policy("strongly avoid A paying C", ctx, prefer_llm=False)
    weights, limits = p.to_solver_inputs()
    r = solve(book, limits, weights)
    assert r.feasible
    a_to_c = sum(t.amount for t in r.transfers if t.sender == "A" and t.receiver == "C")
    b_to_c = sum(t.amount for t in r.transfers if t.sender == "B" and t.receiver == "C")
    assert b_to_c >= a_to_c, f"policy should push C's funding to B: A->C={a_to_c}, B->C={b_to_c}"
    # conservation must still hold
    c_in = sum(t.amount for t in r.transfers if t.receiver == "C")
    assert abs(c_in - 80.0) < 0.01, f"C must still receive 80, got {c_in}"
    print(f"test_policy_feeds_solver_end_to_end PASSED — A->C={a_to_c}, B->C={b_to_c}")


def test_llm_backend():
    """Real LLM backend — only runs with TG_TEST_LLM=1 (needs claude CLI + network)."""
    if os.environ.get("TG_TEST_LLM") != "1":
        print("test_llm_backend SKIPPED (set TG_TEST_LLM=1 to run)")
        return
    p = parse_policy("keep FirmA from owing FirmC more than 25 dollars", CTX, prefer_llm=True)
    assert p.valid, p.to_dict()
    assert p.source == "llm", f"expected llm backend, got {p.source}"
    assert any(cl.frm == "FirmA" and cl.to == "FirmC" and abs(cl.limit - 25.0) < 0.01
               for cl in p.credit_limits), p.to_dict()
    print(f"test_llm_backend PASSED — {p.interpretation}")


if __name__ == "__main__":
    test_minimize_exposure_to_weight()
    test_strongly_avoid_is_higher_weight()
    test_cap_clause_to_credit_limit()
    test_currency_parsed()
    test_compound_policy()
    test_unknown_party_dropped_or_invalid()
    test_gibberish_is_invalid()
    test_empty_policy_is_valid_noop()
    test_policy_feeds_solver_end_to_end()
    test_llm_backend()
    print("\nALL POLICY TESTS PASSED")
