"""Constrained netting solver — the engine the LLM policy steers and the ledger enforces.

The naive netting in `netting.py` answers "what is the minimal set of residual
transfers?" with a greedy debt-simplification. That is correct when there are NO
constraints. But a real fintech rail has constraints: each party caps how much it
will owe any single counterparty (a bilateral credit limit), and the operator may
want to optimize an objective (minimize a party's exposure to a risky counterparty,
minimize gross FX movement, prioritize a strategic relationship).

This module solves that as a real linear program (PuLP/CBC), per currency:

  variables : x[p][q] >= 0   = amount payer p sends receiver q (the residual flow)
  conserve  : for every party, (sum received) - (sum sent) == its net position
              (the SAME conservation the on-ledger guard enforces)
  limits    : x[p][q] <= creditLimit(p -> q)   for every capped ordered pair
  objective : minimize total gross flow + policy-weighted penalty terms

Key behaviours:
  * With no binding limits it reproduces a minimal-gross plan (matches the greedy
    result's gross, though the exact pairing can differ — both are optimal).
  * A credit limit that the naive plan would breach forces the LP to REROUTE the
    flow through other parties (a genuinely different, still-conserving plan).
  * If the constraints make settlement impossible, it returns INFEASIBLE plus the
    binding constraint — that is a first-class feature: it shows the limits have
    teeth. (The on-ledger guard is the backstop; the solver explains *why* up front.)

This is deterministic and unit-tested. The LLM never does arithmetic — it only emits
a small validated policy (objective weights / which pairs to favour), which becomes
penalty coefficients here. The solver + the on-ledger guards are the parts that
cannot be talked past.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pulp

# Reuse the obligation vocabulary from the existing netting module.
from agent.netting import Obligation, net_positions

# numeric tolerance for float/again rounding
EPS = 1e-6


@dataclass(frozen=True)
class CreditLimit:
    """Max `frm` may owe `to` in `currency` in the residual plan."""
    frm: str
    to: str
    limit: float
    currency: str = "USD"


@dataclass(frozen=True)
class FXRate:
    """A co-signed conversion rate: 1 unit of `base` = `rate` units of `quote`."""
    base: str
    quote: str
    rate: float


@dataclass(frozen=True)
class FloorConstraint:
    """`party` must hold >= `floor` of `currency` after settlement, given its
    pre-settle `balance` (provided separately via balances dict)."""
    party: str
    currency: str
    floor: float


def fx_factor(val_ccy: str, rates: list[FXRate], cur: str) -> float | None:
    """Value of 1 unit of `cur` in `val_ccy` via the agreed rates (mirrors the
    on-ledger fxFactor). None if no agreed path connects them."""
    if cur == val_ccy:
        return 1.0
    for r in rates:
        if r.base == cur and r.quote == val_ccy:
            return r.rate
    for r in rates:
        if r.base == val_ccy and r.quote == cur:
            return 1.0 / r.rate
    return None


@dataclass(frozen=True)
class SolvedTransfer:
    sender: str
    receiver: str
    amount: float
    currency: str = "USD"


@dataclass
class SolveResult:
    feasible: bool
    transfers: list[SolvedTransfer] = field(default_factory=list)
    # currency -> {party -> net position}
    net_positions: dict[str, dict[str, float]] = field(default_factory=dict)
    gross_obligations: float = 0.0
    gross_residual: float = 0.0
    objective_value: float = 0.0
    # populated when infeasible: human-readable binding constraint(s)
    binding_constraints: list[str] = field(default_factory=list)
    rationale: list[str] = field(default_factory=list)

    @property
    def netting_efficiency_pct(self) -> float:
        if self.gross_obligations <= 0:
            return 0.0
        return round((self.gross_obligations - self.gross_residual)
                     / self.gross_obligations * 100, 1)


def _by_currency(obligations: list[Obligation]) -> dict[str, list[Obligation]]:
    out: dict[str, list[Obligation]] = {}
    for o in obligations:
        out.setdefault(o.instrument, []).append(o)
    return out


def _solve_one_currency(
    currency: str,
    obligations: list[Obligation],
    limits: list[CreditLimit],
    objective_weights: dict[tuple[str, str], float],
) -> tuple[bool, list[SolvedTransfer], dict[str, float], list[str]]:
    """Solve the residual-flow LP for a single currency.

    Returns (feasible, transfers, net_positions, binding_constraints).
    """
    net = net_positions(obligations)  # party -> net (>0 receiver, <0 payer)
    parties = sorted(net.keys())
    payers = [p for p in parties if net[p] < -EPS]
    receivers = [p for p in parties if net[p] > EPS]

    # Degenerate: everything already nets to zero -> no residuals needed.
    if not payers or not receivers:
        return True, [], net, []

    prob = pulp.LpProblem(f"netting_{currency}", pulp.LpMinimize)

    # x[p][q] = amount payer p sends receiver q  (only payer->receiver arcs)
    x: dict[tuple[str, str], pulp.LpVariable] = {}
    for p in payers:
        for q in receivers:
            x[(p, q)] = pulp.LpVariable(f"x_{p}_{q}", lowBound=0)

    # Objective: minimize total gross residual flow, plus any policy penalties.
    # Default penalty 0; policy can up-weight a (payer,receiver) arc to discourage
    # it (e.g. "minimize FirmA's exposure to FirmC" => penalize x[A][C]).
    prob += pulp.lpSum(
        (1.0 + objective_weights.get((p, q), 0.0)) * x[(p, q)]
        for p in payers for q in receivers
    )

    # Conservation per party (this mirrors the on-ledger guard exactly):
    #   each payer sends exactly what it owes; each receiver receives exactly its due.
    for p in payers:
        prob += (pulp.lpSum(x[(p, q)] for q in receivers) == round(-net[p], 2),
                 f"conserve_payer_{p}")
    for q in receivers:
        prob += (pulp.lpSum(x[(p, q)] for p in payers) == round(net[q], 2),
                 f"conserve_receiver_{q}")

    # Credit limits: x[p][q] <= limit for any capped ordered pair in this currency.
    capped: dict[tuple[str, str], float] = {}
    for cl in limits:
        if cl.currency != currency:
            continue
        if cl.frm in payers and cl.to in receivers:
            capped[(cl.frm, cl.to)] = cl.limit
            prob += (x[(cl.frm, cl.to)] <= cl.limit,
                     f"limit_{cl.frm}_{cl.to}")

    status = prob.solve(pulp.PULP_CBC_CMD(msg=False))

    if pulp.LpStatus[status] != "Optimal":
        # INFEASIBLE: diagnose which limit(s) make it impossible.
        binding = _diagnose_infeasibility(currency, net, payers, receivers, capped)
        return False, [], net, binding

    transfers: list[SolvedTransfer] = []
    for (p, q), var in x.items():
        amt = round(var.value() or 0.0, 2)
        if amt > EPS:
            transfers.append(SolvedTransfer(sender=p, receiver=q,
                                            amount=amt, currency=currency))
    # stable order: largest first
    transfers.sort(key=lambda t: (-t.amount, t.sender, t.receiver))
    return True, transfers, net, []


def _diagnose_infeasibility(
    currency: str,
    net: dict[str, float],
    payers: list[str],
    receivers: list[str],
    capped: dict[tuple[str, str], float],
) -> list[str]:
    """Explain WHY the constrained problem has no solution.

    The classic binding case: a receiver q is owed `net[q]`, but the sum of credit
    limits on arcs INTO q (from every payer that is capped to q) plus the capacity
    of any uncapped arcs is < net[q]. We surface the receiver(s) that cannot be
    fully funded under the caps. This is the message a risk officer needs: "FirmC is
    owed 95 but can receive at most 50 under the current limits."
    """
    binding: list[str] = []
    for q in receivers:
        due = round(net[q], 2)
        # capacity into q: capped arcs use their cap; uncapped arcs are unbounded.
        has_uncapped = any((p, q) not in capped for p in payers)
        if has_uncapped:
            continue  # an uncapped arc can always absorb the remainder
        capacity = round(sum(capped[(p, q)] for p in payers if (p, q) in capped), 2)
        if capacity + EPS < due:
            binding.append(
                f"{q} is owed {due:g} {currency} but credit limits cap inbound flow "
                f"at {capacity:g} {currency} (short {round(due - capacity, 2):g})"
            )
    # symmetric check on payers (a payer that can't place all its debt)
    for p in payers:
        owed = round(-net[p], 2)
        has_uncapped = any((p, q) not in capped for q in receivers)
        if has_uncapped:
            continue
        capacity = round(sum(capped[(p, q)] for q in receivers if (p, q) in capped), 2)
        if capacity + EPS < owed:
            binding.append(
                f"{p} must pay {owed:g} {currency} but its credit limits cap outbound "
                f"flow at {capacity:g} {currency} (short {round(owed - capacity, 2):g})"
            )
    if not binding:
        binding.append(
            f"no feasible {currency} settlement under the current credit limits"
        )
    return binding


def solve(
    obligations: list[Obligation],
    limits: list[CreditLimit] | None = None,
    objective_weights: dict[tuple[str, str], float] | None = None,
) -> SolveResult:
    """Solve the constrained netting across ALL currencies.

    obligations       : the full multi-currency book.
    limits            : on-ledger bilateral credit limits to respect.
    objective_weights : optional policy penalties per (payer,receiver) arc; higher
                        => the solver avoids that arc. (Emitted by the LLM policy
                        layer; pure numbers here.)
    """
    limits = limits or []
    objective_weights = objective_weights or {}

    result = SolveResult(feasible=True)
    result.gross_obligations = round(sum(o.amount for o in obligations), 2)

    per_ccy = _by_currency(obligations)
    all_transfers: list[SolvedTransfer] = []
    all_binding: list[str] = []
    obj = 0.0

    for currency, obls in sorted(per_ccy.items()):
        feasible, transfers, net, binding = _solve_one_currency(
            currency, obls, limits, objective_weights)
        result.net_positions[currency] = {p: round(v, 2) for p, v in net.items()}
        if not feasible:
            result.feasible = False
            all_binding.extend(binding)
            continue
        all_transfers.extend(transfers)
        obj += sum(t.amount for t in transfers)

    result.transfers = all_transfers
    result.gross_residual = round(sum(t.amount for t in all_transfers), 2)
    result.objective_value = round(obj, 2)
    result.binding_constraints = all_binding

    if result.feasible:
        result.rationale = [
            f"{len(obligations)} obligations across {len(per_ccy)} "
            f"currency/currencies totaling {result.gross_obligations} gross",
            f"netted to {len(all_transfers)} residual transfer(s) totaling "
            f"{result.gross_residual} ({result.netting_efficiency_pct}% netted out)",
            "every residual respects the on-ledger credit limits"
            if limits else "no credit limits applied",
            "conservation holds per-currency (matches the on-ledger SettleNetting guard)",
        ]
    else:
        result.rationale = [
            "NO FEASIBLE SETTLEMENT under the current credit limits",
            *[f"binding: {b}" for b in all_binding],
            "this is the limits doing their job — relax a cap or add a counterparty",
        ]
    return result


def solve_fx(
    obligations: list[Obligation],
    rates: list[FXRate],
    settle_ccy: str = "USD",
    limits: list[CreditLimit] | None = None,
    floors: list[FloorConstraint] | None = None,
    balances: dict[tuple[str, str], float] | None = None,
    objective_weights: dict[tuple[str, str], float] | None = None,
) -> SolveResult:
    """CROSS-CURRENCY value netting at agreed FX rates.

    Each party's multi-currency net is valued into `settle_ccy` at the co-signed
    `rates`; residuals are then settled in `settle_ccy`. This mirrors the on-ledger
    value-conservation guard. Respects credit limits (in settle_ccy) and post-settle
    liquidity floors (in settle_ccy). Infeasible => binding constraints.
    """
    limits = limits or []
    floors = floors or []
    balances = balances or {}
    objective_weights = objective_weights or {}

    result = SolveResult(feasible=True)
    result.gross_obligations = round(sum(o.amount for o in obligations), 2)

    # value each party's net into settle_ccy
    currencies = sorted({o.instrument for o in obligations})
    for cur in currencies:
        if fx_factor(settle_ccy, rates, cur) is None:
            result.feasible = False
            result.binding_constraints.append(
                f"no agreed FX rate to value {cur} in {settle_ccy}")
    if not result.feasible:
        result.rationale = ["cannot value the book — missing co-signed FX rate(s)",
                            *result.binding_constraints]
        return result

    val_net: dict[str, float] = {}
    for o in obligations:
        f = fx_factor(settle_ccy, rates, o.instrument)
        assert f is not None  # guaranteed: validated above
        val_net[o.payer] = round(val_net.get(o.payer, 0.0) - o.amount * f, 2)
        val_net[o.payee] = round(val_net.get(o.payee, 0.0) + o.amount * f, 2)

    result.net_positions[settle_ccy] = dict(val_net)

    payers = [p for p, v in val_net.items() if v < -EPS]
    receivers = [p for p, v in val_net.items() if v > EPS]
    if not payers or not receivers:
        result.gross_residual = 0.0
        result.rationale = ["cross-currency book nets to zero value — no residual moves"]
        return result

    prob = pulp.LpProblem("netting_fx", pulp.LpMinimize)
    x = {(p, q): pulp.LpVariable(f"x_{p}_{q}", lowBound=0)
         for p in payers for q in receivers}
    prob += pulp.lpSum((1.0 + objective_weights.get((p, q), 0.0)) * x[(p, q)]
                       for p in payers for q in receivers)
    for p in payers:
        prob += (pulp.lpSum(x[(p, q)] for q in receivers) == round(-val_net[p], 2),
                 f"conserve_payer_{p}")
    for q in receivers:
        prob += (pulp.lpSum(x[(p, q)] for p in payers) == round(val_net[q], 2),
                 f"conserve_receiver_{q}")
    # credit limits in settle_ccy
    capped = {}
    for cl in limits:
        if cl.currency == settle_ccy and cl.frm in payers and cl.to in receivers:
            capped[(cl.frm, cl.to)] = cl.limit
            prob += (x[(cl.frm, cl.to)] <= cl.limit, f"limit_{cl.frm}_{cl.to}")
    # liquidity floors in settle_ccy: post = pre + (received - sent) >= floor
    for fl in floors:
        if fl.currency != settle_ccy:
            continue
        pre = balances.get((fl.party, settle_ccy), 0.0)
        recv = pulp.lpSum(x[(p, fl.party)] for p in payers if (p, fl.party) in x)
        sent = pulp.lpSum(x[(fl.party, q)] for q in receivers if (fl.party, q) in x)
        prob += (pre + recv - sent >= fl.floor, f"floor_{fl.party}")

    status = prob.solve(pulp.PULP_CBC_CMD(msg=False))
    if pulp.LpStatus[status] != "Optimal":
        result.feasible = False
        result.binding_constraints = _diagnose_fx_infeasibility(
            settle_ccy, val_net, payers, receivers, capped, floors, balances)
        result.rationale = ["NO FEASIBLE cross-currency settlement under the constraints",
                            *result.binding_constraints]
        return result

    transfers = []
    for (p, q), var in x.items():
        amt = round(var.value() or 0.0, 2)
        if amt > EPS:
            transfers.append(SolvedTransfer(sender=p, receiver=q, amount=amt,
                                            currency=settle_ccy))
    transfers.sort(key=lambda t: (-t.amount, t.sender, t.receiver))
    result.transfers = transfers
    result.gross_residual = round(sum(t.amount for t in transfers), 2)
    result.objective_value = result.gross_residual
    result.rationale = [
        f"{len(obligations)} obligations across {len(currencies)} currencies "
        f"valued in {settle_ccy} at agreed FX rates",
        f"netted to {len(transfers)} residual transfer(s) totaling "
        f"{result.gross_residual} {settle_ccy} ({result.netting_efficiency_pct}% netted out)",
        "cross-currency value conservation matches the on-ledger guard; rates are co-signed",
        f"{len(capped)} credit limit(s), {len([f for f in floors if f.currency==settle_ccy])} liquidity floor(s) enforced",
    ]
    return result


def _diagnose_fx_infeasibility(settle_ccy, val_net, payers, receivers, capped,
                               floors, balances):
    binding = []
    for q in receivers:
        due = round(val_net[q], 2)
        if any((p, q) not in capped for p in payers):
            continue
        cap = round(sum(capped[(p, q)] for p in payers if (p, q) in capped), 2)
        if cap + EPS < due:
            binding.append(f"{q} is owed {due:g} {settle_ccy} but credit limits cap "
                           f"inbound flow at {cap:g} (short {round(due-cap,2):g})")
    for fl in floors:
        if fl.currency != settle_ccy:
            continue
        pre = balances.get((fl.party, settle_ccy), 0.0)
        net_p = val_net.get(fl.party, 0.0)
        # worst case the party pays its full net out
        if pre + net_p + EPS < fl.floor:
            binding.append(f"{fl.party} would fall below its {fl.floor:g} {settle_ccy} "
                           f"liquidity floor (pre {pre:g}, net {net_p:g})")
    if not binding:
        binding.append(f"no feasible {settle_ccy} settlement under the current constraints")
    return binding


def solve_constrained(
    obligations: list[Obligation],
    limits: list[CreditLimit] | None = None,
    objective_weights: dict[tuple[str, str], float] | None = None,
    rates: list[FXRate] | None = None,
    floors: list[FloorConstraint] | None = None,
    balances: dict[tuple[str, str], float] | None = None,
    settle_ccy: str = "USD",
) -> SolveResult:
    """Unified entry point: cross-currency value netting when `rates` are provided,
    else strict per-currency netting. Both honor credit limits; FX mode also honors
    liquidity floors (the per-currency mode keeps the stronger isolation guarantee)."""
    if rates:
        return solve_fx(obligations, rates, settle_ccy, limits, floors, balances,
                        objective_weights)
    return solve(obligations, limits, objective_weights)


def solve_report(
    obligations: list[Obligation],
    limits: list[CreditLimit] | None = None,
    objective_weights: dict[tuple[str, str], float] | None = None,
) -> dict:
    """JSON-serializable report the agent attaches to its recommendation / the UI."""
    r = solve(obligations, limits, objective_weights)
    return {
        "feasible": r.feasible,
        "gross_obligations": r.gross_obligations,
        "gross_residual": r.gross_residual,
        "netting_efficiency_pct": r.netting_efficiency_pct,
        "net_positions": r.net_positions,
        "residual_transfers": [
            {"sender": t.sender, "receiver": t.receiver,
             "amount": t.amount, "currency": t.currency}
            for t in r.transfers
        ],
        "residual_count": len(r.transfers),
        "binding_constraints": r.binding_constraints,
        "rationale": r.rationale,
    }


if __name__ == "__main__":
    import json
    # demo 1: the canonical 3-firm book (A is the sole net payer).
    book = [
        Obligation("A", "B", 100.0), Obligation("B", "C", 100.0),
        Obligation("C", "A", 80.0), Obligation("A", "C", 50.0),
        Obligation("C", "B", 30.0),
    ]
    print("=== unconstrained (canonical 5-obligation book) ===")
    print(json.dumps(solve_report(book), indent=2))

    # demo 2: a 2-payer / 2-receiver book where a credit limit forces a REROUTE
    # (flow shifts between payers) rather than just failing.
    book2 = [
        Obligation("A", "C", 60.0), Obligation("B", "D", 40.0),
        Obligation("A", "D", 10.0), Obligation("B", "C", 20.0),
    ]  # net: A -70, B -60 (payers) ; C +80, D +50 (receivers)
    print("\n=== reroute: cap A->C <= 30 with 2 payers / 2 receivers ===")
    print(json.dumps(solve_report(book2, [CreditLimit("A", "C", 30.0)]), indent=2))

    # demo 3: an INFEASIBLE case — cap the sole payer's only viable arc.
    print("\n=== infeasible: cap A->C <= 20 in the canonical book (A is sole payer) ===")
    print(json.dumps(solve_report(book, [CreditLimit("A", "C", 20.0)]), indent=2))
