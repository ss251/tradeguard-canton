"""CIP-56 token-standard settlement backend for TradeGuard.

This is the settlement layer rebuild (spec: research/CIP56_SETTLEMENT_REBUILD_SPEC.md).
The netting BRAIN (agent.netting / agent.solver) is unchanged: it turns a book of
obligations into a minimal residual set of transfers. This backend settles those
residuals over REAL Canton Network Token Standard (CIP-56) holdings:

  * TGHolding implements Splice.Api.Token.HoldingV1:Holding (same package-id deployed on
    DevNet), so TradeGuard holdings are readable by any compliant wallet via the standard
    interface.
  * The residual legs are executed atomically by NettingSettlement_Execute — each leg
    splits the sender's TGHolding and moves it to the receiver, all in one transaction.

Runs on both networks via agent.real_client (TG_NET=local|devnet).

Verification is done through the STANDARD Holding interface (InterfaceFilter), proving the
holdings are genuinely CIP-56 — not just TradeGuard-internal state.
"""
from __future__ import annotations

import os
from agent.real_client import RealLedgerClient, load_real_parties, HOST, _auth_token
from agent.netting import Obligation, netting_report, minimal_settlement

TG = "#tradeguard-token:TradeGuard.TokenSettlement"
HOLDING_IFACE = "#splice-api-token-holding-v1:Splice.Api.Token.HoldingV1:Holding"

# The canonical single-instrument demo book (USDCx), same magnitudes as the LocalNet
# obligation demo so the numbers line up across backends.
DEMO_BOOK = [
    ("firma", "firmb", 100.0),
    ("firmb", "firmc", 60.0),
    ("firmc", "firma", 40.0),
    ("firma", "firmc", 50.0),
    ("firmb", "firma", 30.0),
]


def _op() -> RealLedgerClient:
    p = load_real_parties()
    return RealLedgerClient(p["operator"])


def clear_tg_holdings():
    """Archive all TGHoldings + open NettingSettlements across ANY package generation
    (idempotent reset). Uses a wildcard ACS scan + exact-template-id archival, so orphans
    left by earlier package versions are cleaned too."""
    import json, urllib.request
    p = load_real_parties()
    op = RealLedgerClient(p["operator"])
    tok = _auth_token()
    end = op._ledger_end()
    body = {"filter": {"filtersByParty": {p["operator"]: {"cumulative": [
        {"identifierFilter": {"WildcardFilter": {"value": {"includeCreatedEventBlob": False}}}}]}}},
        "verbose": False, "activeAtOffset": end}
    req = urllib.request.Request(HOST + "/v2/state/active-contracts",
        data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    items = json.loads(urllib.request.urlopen(req, timeout=60).read())
    items = items if isinstance(items, list) else items.get("result", [])
    n = 0
    for it in items:
        ce = it.get("contractEntry", {}).get("JsActiveContract", {}).get("createdEvent")
        if not ce:
            continue
        tid = ce.get("templateId", "")
        cid = ce.get("contractId")
        if "TradeGuard.TokenSettlement:TGHolding" in tid:
            choice = "Archive"
        elif "TradeGuard.TokenSettlement:NettingSettlement" in tid:
            choice = "NettingSettlement_Cancel"
        else:
            continue
        b = {"commands": [{"ExerciseCommand": {"templateId": tid, "contractId": cid,
            "choice": choice, "choiceArgument": {}}}], "commandId": f"wipe-{cid[:8]}",
            "actAs": [p["operator"]], "readAs": [p["operator"]]}
        try:
            urllib.request.urlopen(urllib.request.Request(HOST + "/v2/commands/submit-and-wait",
                data=json.dumps(b).encode(), method="POST",
                headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}), timeout=60)
            n += 1
        except Exception:
            pass
    return n


def mint_book(instrument: str = "USDCx", book=None) -> dict:
    """Fund each party with a TGHolding sized to exactly cover its GROSS outflow in the
    book, so every residual leg is fundable. Registry (operator) is issuer/signatory."""
    p = load_real_parties()
    op = RealLedgerClient(p["operator"])
    book = book or DEMO_BOOK
    # gross outflow per party
    out: dict[str, float] = {}
    for payer, _payee, amt in book:
        out[payer] = out.get(payer, 0.0) + amt
    minted = {}
    for party_key, amount in out.items():
        r = op.create(f"{TG}:TGHolding", {
            "registry": p["operator"],
            "instrumentId": instrument,
            "owner": p[party_key],
            "amount": amount,
            "locked": False,
        }, act_as=[p["operator"], p[party_key]])
        minted[party_key] = "ok" if not r.get("_http_error") else r
    return {"minted": minted, "instrument": instrument}


def _holding_cid_for(op: RealLedgerClient, party_id: str, instrument: str) -> str | None:
    """Find a TGHolding owned by party_id of the given instrument (largest first)."""
    best = None
    best_amt = -1.0
    for c in op.query(f"{TG}:TGHolding"):
        pl = c["payload"]
        if pl.get("owner") == party_id and pl.get("instrumentId") == instrument:
            amt = float(pl.get("amount", 0))
            if amt > best_amt:
                best_amt, best = amt, c["contractId"]
    return best


def settle_token(instrument: str = "USDCx", book=None) -> dict:
    """Run the brain over the book, then settle the residual legs atomically over CIP-56
    TGHoldings via NettingSettlement_Execute. Single source of truth: the same minimal
    residual set the brain computes is what settles on-ledger."""
    p = load_real_parties()
    op = RealLedgerClient(p["operator"])
    book = book or DEMO_BOOK

    # 1. brain: obligations -> minimal residual transfers
    obls = [Obligation(payer=s, payee=r, amount=a, instrument=instrument)
            for (s, r, a) in book]
    report = netting_report(obls, instrument)
    residuals = minimal_settlement(obls, instrument)
    if not residuals:
        return {"ok": True, "note": "book already nets to zero", "report": report}

    # 2. build NetLegs (party keys -> party ids); collect ONE funding holding per distinct
    #    sender (the settlement threads each sender's holding through all their legs).
    legs = []
    senders_seen: dict[str, str] = {}   # sender_id -> holding_cid
    for t in residuals:
        sender_id = p[t.sender]
        receiver_id = p[t.receiver]
        legs.append({
            "sender": sender_id, "receiver": receiver_id,
            "amount": t.amount, "instrumentId": instrument,
        })
        if sender_id not in senders_seen:
            hcid = _holding_cid_for(op, sender_id, instrument)
            if not hcid:
                return {"ok": False, "error": f"no TGHolding to fund {t.sender}; mint first"}
            senders_seen[sender_id] = hcid
    sender_holdings = [{"_1": sid, "_2": hcid} for sid, hcid in senders_seen.items()]

    party_ids = [p[k] for k in ("firma", "firmb", "firmc")]

    # 3. create the NettingSettlement (registry signs)
    cr = op.create(f"{TG}:NettingSettlement", {
        "registry": p["operator"],
        "settlementRef": f"token-{instrument}",
        "legs": legs,
        "parties": party_ids,
    })
    if cr.get("_http_error"):
        return {"ok": False, "error": f"create settlement failed: {cr}"}
    scid = _created_cid(cr, "NettingSettlement")
    if not scid:
        # fall back: query it
        found = op.query(f"{TG}:NettingSettlement")
        scid = found[-1]["contractId"] if found else None
    if not scid:
        return {"ok": False, "error": "could not resolve NettingSettlement cid"}

    # 4. execute atomically (senderHoldings is a list of [Party, ContractId] tuples)
    ex = op.exercise(f"{TG}:NettingSettlement", scid, "NettingSettlement_Execute",
                     {"senderHoldings": sender_holdings})
    if ex.get("_http_error"):
        return {"ok": False, "error": f"execute failed: {ex}", "report": report}

    return {
        "ok": True,
        "instrument": instrument,
        "gross_value": report["gross_value"],
        "residual_count": report["residual_count"],
        "net_value": report["net_value"],
        "netting_efficiency_pct": report["netting_efficiency_pct"],
        "residual_legs": legs,
        "settlement_cid": scid,
    }


def _created_cid(resp: dict, entity_suffix: str) -> str | None:
    """Pull a created contractId of the given entity from a submit-and-wait response."""
    def walk(o):
        found = []
        if isinstance(o, dict):
            ce = o.get("CreatedTreeEvent", {}).get("value") or o.get("created") or {}
            tid = (o.get("templateId") or ce.get("templateId") or "")
            cid = (o.get("contractId") or ce.get("contractId"))
            if cid and entity_suffix in str(tid):
                found.append(cid)
            for v in o.values():
                found += walk(v)
        elif isinstance(o, list):
            for v in o:
                found += walk(v)
        return found
    hits = walk(resp)
    return hits[0] if hits else None


def verify_via_standard_interface(instrument: str = "USDCx") -> dict:
    """Read TGHoldings back through the STANDARD CIP-56 Holding interface (InterfaceFilter),
    proving they are genuinely token-standard holdings, and report per-owner balances."""
    import json, urllib.request
    p = load_real_parties()
    op = RealLedgerClient(p["operator"])
    tok = _auth_token()
    end = op._ledger_end()
    balances: dict[str, float] = {}
    count = 0
    # Query only as the operator (registry) — it is a stakeholder on EVERY TGHolding, so it
    # sees them all exactly once. (Summing across owner+operator would double-count.)
    for key in ("operator",):
        party = p[key]
        body = {"filter": {"filtersByParty": {party: {"cumulative": [
            {"identifierFilter": {"InterfaceFilter": {"value": {
                "interfaceId": HOLDING_IFACE,
                "includeInterfaceView": True,
                "includeCreatedEventBlob": False}}}}]}}},
            "verbose": False, "activeAtOffset": end}
        req = urllib.request.Request(HOST + "/v2/state/active-contracts",
            data=json.dumps(body).encode(), method="POST",
            headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
        try:
            raw = urllib.request.urlopen(req, timeout=60).read().decode()
        except Exception as e:
            return {"ok": False, "error": f"interface query failed for {key}: {e}"}
        for line in _iter_created(raw):
            for v in line.get("interfaceViews", []):
                vv = v.get("viewValue", {})
                if vv.get("instrumentId", {}).get("id") == instrument:
                    owner = vv.get("owner", "")
                    balances[owner] = round(balances.get(owner, 0.0) + float(vv.get("amount", 0)), 4)
                    count += 1
    return {"ok": True, "instrument": instrument,
            "holdings_via_standard_interface": count, "balances_by_owner": balances}


def _iter_created(raw: str):
    import json
    try:
        data = json.loads(raw)
    except Exception:
        return
    items = data if isinstance(data, list) else data.get("result", [])
    for it in items:
        ce = (it.get("contractEntry", {}).get("JsActiveContract", {}).get("createdEvent")
              if isinstance(it, dict) else None)
        if ce:
            yield ce


if __name__ == "__main__":
    import json
    print("=== reset ==="); print(clear_tg_holdings(), "contracts archived")
    print("=== mint book ==="); print(json.dumps(mint_book(), indent=1))
    print("=== settle over CIP-56 ==="); print(json.dumps(settle_token(), indent=1))
    print("=== verify via STANDARD interface ==="); print(json.dumps(verify_via_standard_interface(), indent=1))
