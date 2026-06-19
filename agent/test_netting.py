"""Tests for the multilateral netting algorithm. Run: python3 -m agent.test_netting"""
from agent.netting import (
    Obligation, net_positions, minimal_settlement, netting_report,
)


def approx(a, b, tol=0.01):
    return abs(a - b) < tol


def test_three_party_cycle():
    """A owes B 100, B owes C 100, C owes A 100 -> nets to ZERO. The classic win."""
    obs = [
        Obligation("A", "B", 100),
        Obligation("B", "C", 100),
        Obligation("C", "A", 100),
    ]
    net = net_positions(obs)
    assert all(approx(v, 0) for v in net.values()), f"cycle should net to 0, got {net}"
    transfers = minimal_settlement(obs)
    assert len(transfers) == 0, f"perfect cycle needs 0 transfers, got {transfers}"
    print("test_three_party_cycle PASSED — 3 obligations netted to 0 transfers")


def test_partial_netting():
    """A owes B 100, B owes A 60 -> A pays B net 40 (1 transfer instead of 2)."""
    obs = [Obligation("A", "B", 100), Obligation("B", "A", 60)]
    transfers = minimal_settlement(obs)
    assert len(transfers) == 1, f"expected 1 residual, got {transfers}"
    t = transfers[0]
    assert t.sender == "A" and t.receiver == "B" and approx(t.amount, 40), str(t)
    print("test_partial_netting PASSED — 2 obligations netted to 1 transfer of 40")


def test_chain_netting():
    """A->B 100, B->C 100 -> A->C 100 (B is a pass-through, drops out)."""
    obs = [Obligation("A", "B", 100), Obligation("B", "C", 100)]
    transfers = minimal_settlement(obs)
    assert len(transfers) == 1, f"expected 1 residual, got {transfers}"
    t = transfers[0]
    assert t.sender == "A" and t.receiver == "C" and approx(t.amount, 100), str(t)
    print("test_chain_netting PASSED — pass-through party B nets out")


def test_report_efficiency():
    """Report should show meaningful netting efficiency on a dense book."""
    obs = [
        Obligation("A", "B", 100),
        Obligation("B", "C", 100),
        Obligation("C", "A", 80),
        Obligation("A", "C", 50),
        Obligation("C", "B", 30),
    ]
    rep = netting_report(obs)
    assert rep["gross_obligations"] == 5
    assert rep["residual_count"] < 5, "netting should reduce transfer count"
    assert rep["value_netted_out"] > 0, "should net out some value"
    # conservation: net positions must sum to zero
    assert approx(sum(rep["net_positions"].values()), 0), "net must conserve"
    print(f"test_report_efficiency PASSED — {rep['gross_obligations']} gross -> "
          f"{rep['residual_count']} residuals, {rep['netting_efficiency_pct']}% netted out")


def test_conservation_random():
    """Net positions always sum to zero (value is conserved)."""
    obs = [
        Obligation("X", "Y", 250), Obligation("Y", "Z", 120),
        Obligation("Z", "X", 90), Obligation("X", "Z", 40),
        Obligation("Y", "X", 75),
    ]
    net = net_positions(obs)
    assert approx(sum(net.values()), 0), f"value must conserve, got {sum(net.values())}"
    # residual transfers must also reproduce the same net positions
    transfers = minimal_settlement(obs)
    repro: dict[str, float] = {}
    for t in transfers:
        repro[t.sender] = repro.get(t.sender, 0) - t.amount
        repro[t.receiver] = repro.get(t.receiver, 0) + t.amount
    for p in net:
        assert approx(net.get(p, 0), repro.get(p, 0)), \
            f"residuals must reproduce net for {p}: {net.get(p)} vs {repro.get(p)}"
    print("test_conservation_random PASSED — residuals reproduce exact net positions")


if __name__ == "__main__":
    test_three_party_cycle()
    test_partial_netting()
    test_chain_netting()
    test_report_efficiency()
    test_conservation_random()
    print("\nALL NETTING TESTS PASSED")
