"""Credit-limit lifecycle on the real Canton network — the single source of truth.

A `CreditLimit` is an on-ledger contract (a fintech's own bilateral exposure cap).
The whole point of the design is that the limits the SOLVER respects are the EXACT
same limits the LEDGER enforces — there is no second, parallel definition that could
drift. This module is the bridge:

  * seed_limit / clear_limits     — write/remove CreditLimit contracts on the ledger
  * load_limits                   — read the on-ledger limits the operator can see
  * to_solver_limits              — convert them to agent.solver.CreditLimit objects
  * limit_cids_for_settle         — the contractIds to pass into NettingBatch.creditLimits

So the flow is: seed limits on-ledger -> the solver plans UNDER those same limits ->
the NettingBatch carries those same limit cids -> SettleNetting enforces them. One
definition, three consumers (planner, batch, guard).

Limits are signed by `from` + `operator` (the obligor accepts its own cap, the
operator administers the rail) with `to` as observer. The admin token can act as any
party, so the agent can seed on a firm's behalf in the demo/operator context.
"""
from __future__ import annotations

from dataclasses import dataclass

from agent.real_client import RealLedgerClient, load_real_parties
from agent.solver import CreditLimit as SolverLimit

CREDIT_LIMIT_T = "TradeGuard.Netting:CreditLimit"
FX_RATE_T = "TradeGuard.Netting:FXRate"
LIQUIDITY_FLOOR_T = "TradeGuard.Netting:LiquidityFloor"


def _short(party: str) -> str:
    return party.split("::")[0]


def _err(resp: dict) -> str | None:
    if isinstance(resp, dict) and "_http_error" in resp:
        return resp.get("_body", "")[:400]
    return None


def _tree_created_cid(resp: dict, suffix: str) -> str:
    """Extract the created contractId of `suffix` from a transaction-tree response."""
    tree = resp.get("transactionTree", resp)
    events = tree.get("eventsById", {})
    matches = []
    for _, ev in sorted(events.items(), key=lambda kv: kv[0]):
        node = ev.get("CreatedTreeEvent", {}).get("value", ev)
        cid = node.get("contractId")
        tmpl = node.get("templateId", "")
        if cid and (tmpl.endswith(suffix) or not suffix):
            matches.append(cid)
    if not matches:
        import re
        import json as _j
        cids = re.findall(r'"contractId"\s*:\s*"([^"]+)"', _j.dumps(resp))
        if cids:
            return cids[-1]
        raise RuntimeError(f"no created {suffix} in tree: {str(resp)[:300]}")
    return matches[-1]


@dataclass
class LedgerLimit:
    """An on-ledger CreditLimit, with both its contractId and its parsed values."""
    cid: str
    frm: str            # full party id
    to: str             # full party id
    currency: str
    limit: float

    def short(self) -> str:
        return f"{_short(self.frm)}->{_short(self.to)} <= {self.limit:g} {self.currency}"


def seed_limit(frm_key: str, to_key: str, limit: float, currency: str = "USD",
               parties: dict | None = None) -> dict:
    """Create a CreditLimit on-ledger: `frm_key` may owe `to_key` at most `limit`
    in `currency`. Keys are short names ('firma','firmb',...). Returns {cid,...}."""
    parties = parties or load_real_parties()
    operator = parties["operator"]
    frm = parties[frm_key]
    to = parties[to_key]
    op = RealLedgerClient(operator)
    r = op.create_tree(CREDIT_LIMIT_T,
                       {"operator": operator, "from": frm, "to": to,
                        "currency": currency, "limit": limit},
                       act_as=[frm, operator])
    e = _err(r)
    if e:
        return {"ok": False, "error": e}
    cid = _tree_created_cid(r, CREDIT_LIMIT_T)
    return {"ok": True, "cid": cid, "from": _short(frm), "to": _short(to),
            "currency": currency, "limit": limit}


def load_limits(parties: dict | None = None) -> list[LedgerLimit]:
    """Read every CreditLimit the operator can see on the ledger (the live set)."""
    parties = parties or load_real_parties()
    op = RealLedgerClient(parties["operator"])
    out: list[LedgerLimit] = []
    for c in op.query(CREDIT_LIMIT_T):
        pl = c["payload"]
        out.append(LedgerLimit(
            cid=c["contractId"], frm=pl["from"], to=pl["to"],
            currency=pl.get("currency", "USD"), limit=float(pl["limit"])))
    return out


def to_solver_limits(ledger_limits: list[LedgerLimit]) -> list[SolverLimit]:
    """Convert on-ledger limits to solver CreditLimits keyed by SHORT party names
    (the solver works in short names, matching agent.netting.Obligation)."""
    return [SolverLimit(frm=_short(l.frm), to=_short(l.to),
                        limit=l.limit, currency=l.currency)
            for l in ledger_limits]


def limit_cids(ledger_limits: list[LedgerLimit]) -> list[str]:
    """The contractIds to pass into NettingBatch.creditLimits so SettleNetting
    enforces the SAME limits the solver planned under."""
    return [l.cid for l in ledger_limits]


def clear_limits(parties: dict | None = None) -> dict:
    """Archive every CreditLimit on the ledger (clean slate for a new policy).
    Archived via the operator using the generic Archive choice."""
    parties = parties or load_real_parties()
    op = RealLedgerClient(parties["operator"])
    cleared = 0
    errors = []
    for c in op.query(CREDIT_LIMIT_T):
        # CreditLimit signatories are from+operator; operator can archive with from's
        # consent. The admin token acts as both.
        frm = c["payload"]["from"]
        r = op.exercise(CREDIT_LIMIT_T, c["contractId"], "Archive", {},
                        act_as=[frm, parties["operator"]])
        if _err(r):
            errors.append(_err(r))
        else:
            cleared += 1
    return {"ok": not errors, "cleared": cleared, "errors": errors}


# ─────────────────────────  AGGREGATE exposure limits  ─────────────────────────
AGG_LIMIT_T = "TradeGuard.Netting:AggregateLimit"


@dataclass
class LedgerAggLimit:
    """An on-ledger AggregateLimit: cap on `party`'s TOTAL outflow in `currency`."""
    cid: str
    party: str           # full party id
    currency: str
    limit: float

    def short(self) -> str:
        return f"{_short(self.party)} TOTAL <= {self.limit:g} {self.currency}"


def seed_agg_limit(party_key: str, limit: float, currency: str = "USD",
                   parties: dict | None = None) -> dict:
    """Create an AggregateLimit on-ledger: `party_key`'s TOTAL residual outflow
    across ALL counterparties may not exceed `limit` in `currency`."""
    parties = parties or load_real_parties()
    operator = parties["operator"]
    party = parties[party_key]
    op = RealLedgerClient(operator)
    r = op.create_tree(AGG_LIMIT_T,
                       {"operator": operator, "party": party,
                        "currency": currency, "limit": limit},
                       act_as=[party, operator])
    e = _err(r)
    if e:
        return {"ok": False, "error": e}
    cid = _tree_created_cid(r, AGG_LIMIT_T)
    return {"ok": True, "cid": cid, "party": _short(party),
            "currency": currency, "limit": limit}


def load_agg_limits(parties: dict | None = None) -> list[LedgerAggLimit]:
    """Read every AggregateLimit the operator can see (the live set)."""
    parties = parties or load_real_parties()
    op = RealLedgerClient(parties["operator"])
    out: list[LedgerAggLimit] = []
    for c in op.query(AGG_LIMIT_T):
        pl = c["payload"]
        out.append(LedgerAggLimit(
            cid=c["contractId"], party=pl["party"],
            currency=pl.get("currency", "USD"), limit=float(pl["limit"])))
    return out


def to_solver_agg_limits(ledger_aggs: list[LedgerAggLimit]):
    """Convert on-ledger aggregate limits to solver AggLimits (short party names)."""
    from agent.solver import AggLimit
    return [AggLimit(party=_short(a.party), limit=a.limit, currency=a.currency)
            for a in ledger_aggs]


def agg_limit_cids(ledger_aggs: list[LedgerAggLimit]) -> list[str]:
    """ContractIds for NettingBatch.aggregateLimits so SettleNetting enforces the
    SAME aggregate caps the solver planned under."""
    return [a.cid for a in ledger_aggs]


def clear_agg_limits(parties: dict | None = None) -> dict:
    """Archive every AggregateLimit on the ledger."""
    parties = parties or load_real_parties()
    op = RealLedgerClient(parties["operator"])
    cleared = 0
    errors = []
    for c in op.query(AGG_LIMIT_T):
        pty = c["payload"]["party"]
        r = op.exercise(AGG_LIMIT_T, c["contractId"], "Archive", {},
                        act_as=[pty, parties["operator"]])
        if _err(r):
            errors.append(_err(r))
        else:
            cleared += 1
    return {"ok": not errors, "cleared": cleared, "errors": errors}


# --- FX rates (co-signed, on-ledger) ---------------------------------------------

@dataclass
class LedgerFXRate:
    cid: str
    base: str
    quote: str
    rate: float
    parties: list[str]   # full party ids that co-signed

    def short(self) -> str:
        return f"1 {self.base} = {self.rate:g} {self.quote}"


def seed_fx_rate(base: str, quote: str, rate: float, party_keys: list[str],
                 parties: dict | None = None) -> dict:
    """Create a co-signed FXRate on-ledger. EVERY party in `party_keys` (short names)
    plus the operator sign it, so cross-currency netting at this rate is mutually
    agreed and trustless. Returns {cid,...}."""
    parties = parties or load_real_parties()
    operator = parties["operator"]
    party_ids = [parties[k] for k in party_keys]
    op = RealLedgerClient(operator)
    r = op.create_tree(FX_RATE_T,
                       {"operator": operator, "base": base, "quote": quote,
                        "rate": rate, "parties": {"map": [[p, {}] for p in party_ids]}},
                       act_as=[operator] + party_ids)
    e = _err(r)
    if e:
        return {"ok": False, "error": e}
    return {"ok": True, "cid": _tree_created_cid(r, FX_RATE_T),
            "base": base, "quote": quote, "rate": rate,
            "parties": [_short(p) for p in party_ids]}


def load_fx_rates(parties: dict | None = None) -> list[LedgerFXRate]:
    """Read every FXRate the operator can see on the ledger."""
    parties = parties or load_real_parties()
    op = RealLedgerClient(parties["operator"])
    out: list[LedgerFXRate] = []
    for c in op.query(FX_RATE_T):
        pl = c["payload"]
        # parties is a GenMap encoding {"map":[[party,{}],...]}
        pmap = pl.get("parties", {})
        plist = [kv[0] for kv in pmap.get("map", [])] if isinstance(pmap, dict) else []
        out.append(LedgerFXRate(cid=c["contractId"], base=pl["base"], quote=pl["quote"],
                                rate=float(pl["rate"]), parties=plist))
    return out


def fx_rate_cids(rates: list[LedgerFXRate]) -> list[str]:
    return [r.cid for r in rates]


def fx_triples(rates: list[LedgerFXRate]) -> list[tuple[str, str, float]]:
    """(base, quote, rate) triples for the solver's value valuation."""
    return [(r.base, r.quote, r.rate) for r in rates]


def clear_fx_rates(parties: dict | None = None) -> dict:
    parties = parties or load_real_parties()
    op = RealLedgerClient(parties["operator"])
    cleared, errors = 0, []
    for c in op.query(FX_RATE_T):
        pl = c["payload"]
        pmap = pl.get("parties", {})
        signers = [kv[0] for kv in pmap.get("map", [])] if isinstance(pmap, dict) else []
        r = op.exercise(FX_RATE_T, c["contractId"], "Archive", {},
                        act_as=[parties["operator"]] + signers)
        if _err(r):
            errors.append(_err(r))
        else:
            cleared += 1
    return {"ok": not errors, "cleared": cleared, "errors": errors}


# --- liquidity floors (on-ledger) ------------------------------------------------

@dataclass
class LedgerFloor:
    cid: str
    party: str
    currency: str
    floor: float

    def short(self) -> str:
        return f"{_short(self.party)} >= {self.floor:g} {self.currency}"


def seed_liquidity_floor(party_key: str, floor: float, currency: str = "USD",
                         parties: dict | None = None) -> dict:
    """Create a LiquidityFloor on-ledger: `party_key` must retain >= floor."""
    parties = parties or load_real_parties()
    operator = parties["operator"]
    party = parties[party_key]
    op = RealLedgerClient(operator)
    r = op.create_tree(LIQUIDITY_FLOOR_T,
                       {"operator": operator, "party": party,
                        "currency": currency, "floor": floor},
                       act_as=[operator, party])
    e = _err(r)
    if e:
        return {"ok": False, "error": e}
    return {"ok": True, "cid": _tree_created_cid(r, LIQUIDITY_FLOOR_T),
            "party": _short(party), "currency": currency, "floor": floor}


def load_liquidity_floors(parties: dict | None = None) -> list[LedgerFloor]:
    parties = parties or load_real_parties()
    op = RealLedgerClient(parties["operator"])
    out: list[LedgerFloor] = []
    for c in op.query(LIQUIDITY_FLOOR_T):
        pl = c["payload"]
        out.append(LedgerFloor(cid=c["contractId"], party=pl["party"],
                               currency=pl.get("currency", "USD"), floor=float(pl["floor"])))
    return out


def floor_cids(floors: list[LedgerFloor]) -> list[str]:
    return [f.cid for f in floors]


def clear_liquidity_floors(parties: dict | None = None) -> dict:
    parties = parties or load_real_parties()
    op = RealLedgerClient(parties["operator"])
    cleared, errors = 0, []
    for c in op.query(LIQUIDITY_FLOOR_T):
        party = c["payload"]["party"]
        r = op.exercise(LIQUIDITY_FLOOR_T, c["contractId"], "Archive", {},
                        act_as=[parties["operator"], party])
        if _err(r):
            errors.append(_err(r))
        else:
            cleared += 1
    return {"ok": not errors, "cleared": cleared, "errors": errors}


def clear_all(parties: dict | None = None) -> dict:
    """Clear every on-ledger constraint (credit limits, aggregate limits, FX rates,
    liquidity floors)."""
    parties = parties or load_real_parties()
    return {"credit_limits": clear_limits(parties),
            "aggregate_limits": clear_agg_limits(parties),
            "fx_rates": clear_fx_rates(parties),
            "liquidity_floors": clear_liquidity_floors(parties)}


if __name__ == "__main__":
    import json
    import sys
    action = sys.argv[1] if len(sys.argv) > 1 else "list"
    if action == "list":
        lims = load_limits()
        print(json.dumps([l.short() for l in lims], indent=2))
    elif action == "seed":
        # seed FirmA->FirmC cap 20 USD as a demo
        print(json.dumps(seed_limit("firma", "firmc", 20.0, "USD"), indent=2))
    elif action == "clear":
        print(json.dumps(clear_limits(), indent=2))
