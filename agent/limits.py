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
    """Archive every CreditLimit on the ledger (clean slate for a fresh policy).
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
