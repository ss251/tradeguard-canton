"""Instant v2 netting settlement + live on-ledger fraud rejection.

This replaces the slow `dpm script` subprocess path with direct JSON Ledger API v2
calls, so the Operator Console can:
  * settle_real(...)  -> settle the seeded book in ~2-3s instead of ~15s, and
  * attempt_fraud(...) -> submit a REAL value-violating NettingBatch to the LIVE
                          ledger and surface the actual on-chain rejection (the
                          conservation guard firing), not a unit-test runner.

Everything runs as the admin user with multi-party actAs (the user has CanActAs for
every TG party), so we can drive bank+firm+operator authority in one command. The
privacy story is unaffected: reads still use per-party filtersByParty.

The Daml -> v2 JSON encoding (learned from live payloads):
  Id          -> {"unpack": "USD"}
  Parties/Set -> {"map": []}            (we build sets as {"map":[[p,{}],...]} below)
  Optional    -> null | value
  Decimal     -> "100.0000000000" (string ok; we send plain numbers, server coerces)
  enum        -> bare string ("TransferableFungible", "Pending")
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent.real_client import RealLedgerClient, load_real_parties
from agent.netting import Obligation, minimal_settlement, net_positions

USD_ID = "USD"
FIRMS = ["firma", "firmb", "firmc", "firmd", "firme"]  # support up to 5 firms
ACC = {"firma": "A-cash", "firmb": "B-cash", "firmc": "C-cash",
       "firmd": "D-cash", "firme": "E-cash"}


def _id(t: str) -> dict:
    return {"unpack": t}


def _parties_set(parties: list[str]) -> dict:
    # GenMap encoding: list of [key, value] pairs; value is unit {}
    return {"map": [[p, {}] for p in parties]}


def _instr(bank: str) -> dict:
    return {"depository": bank, "issuer": bank, "id": _id(USD_ID),
            "version": "1", "holdingStandard": "TransferableFungible"}


def _err(resp: dict) -> str | None:
    if isinstance(resp, dict) and "_http_error" in resp:
        return resp.get("_body", "")[:400]
    return None


def _short(party: str) -> str:
    return party.split("::")[0]


def _present_firms(parties: dict) -> list[str]:
    return [f for f in FIRMS if f in parties]


def _book_facts(parties: dict) -> list[tuple[str, str, float]]:
    """The operator's view of the obligation book, as (payer, payee, amount)."""
    op = RealLedgerClient(parties["operator"])
    out = []
    for c in op.query("TradeGuard.Netting:Obligation"):
        pl = c["payload"]
        out.append((pl["payer"], pl["payee"], float(pl["amount"])))
    return out


def _ensure_account(parties: dict, bank: str, owner_party: str, acc_id: str):
    """Idempotently create an account for owner at bank."""
    bankc = RealLedgerClient(bank)
    for a in bankc.query("TradeGuard.Holding:Account"):
        pl = a["payload"]
        if pl["owner"] == owner_party and pl["id"]["unpack"] == acc_id:
            return
    bankc.create("TradeGuard.Holding:Account",
                 {"custodian": bank, "owner": owner_party, "id": _id(acc_id),
                  "observers": _parties_set([])},
                 act_as=[bank, owner_party])


def _instrument_cid(parties: dict, bank: str) -> str:
    bankc = RealLedgerClient(bank)
    for i in bankc.query("TradeGuard.Instrument:Instrument"):
        if i["payload"]["id"]["unpack"] == USD_ID:
            return i["contractId"]
    r = bankc.create("TradeGuard.Instrument:Instrument",
                     {"depository": bank, "issuer": bank, "id": _id(USD_ID),
                      "version": "1", "holdingStandard": "TransferableFungible",
                      "description": "USD", "observers": _parties_set([])})
    return _created_cid(r)


def _authority_cid(parties: dict, bank: str, operator: str) -> str:
    bankc = RealLedgerClient(bank)
    for a in bankc.query("TradeGuard.Settlement:SettlementAuthority"):
        if a["payload"]["coordinator"] == operator:
            return a["contractId"]
    r = bankc.create("TradeGuard.Settlement:SettlementAuthority",
                     {"custodian": bank, "coordinator": operator})
    return _created_cid(r)


def _created_cid(resp: dict) -> str:
    """Pull the created contract id out of a v2 submit-and-wait response."""
    if _err(resp):
        raise RuntimeError(f"create failed: {_err(resp)}")
    # v2 returns {"transaction"/"completionOffset"/...}; the created cid is in events
    # submit-and-wait (no transaction view) returns updateId only. We re-query instead
    # where needed; but CreateAndWait returns the cid under different shapes — try common ones.
    for key in ("contractId",):
        if key in resp:
            return resp[key]
    # fall through: caller should re-query
    return ""


def _leg(sender, receiver, bank, amount, s_acc, r_acc) -> dict:
    return {"sender": sender, "receiver": receiver, "custodian": bank,
            "instrument": _instr(bank), "amount": amount,
            "senderAccountId": _id(s_acc), "receiverAccountId": _id(r_acc)}


def _issue_and_lock(parties, bank, operator, instr_cid, owner_party, acc_id, amount, ctx):
    """Issue a holding of `amount` to owner and lock it to the operator. Returns locked cid."""
    bankc = RealLedgerClient(bank)
    r = bankc.exercise_tree("TradeGuard.Instrument:Instrument", instr_cid, "Issue",
                            {"custodian": bank, "owner": owner_party,
                             "accountId": _id(acc_id), "amount": amount},
                            act_as=[bank, owner_party])
    e = _err(r)
    if e:
        raise RuntimeError(f"issue failed: {e}")
    hcid = _tree_created_cid(r, "TradeGuard.Holding:Holding")
    # lock it
    r2 = bankc.exercise_tree("TradeGuard.Holding:Holding", hcid, "LockHolding",
                             {"locker": operator, "context": ctx}, act_as=[bank, owner_party])
    e2 = _err(r2)
    if e2:
        raise RuntimeError(f"lock failed: {e2}")
    return _tree_created_cid(r2, "TradeGuard.Holding:Holding")


def _tree_created_cid(resp: dict, template_suffix: str) -> str:
    """Extract the created contractId of `template_suffix` from a transaction-tree
    response. The tree's eventsById holds CreatedTreeEvents with contractId+templateId.
    We pick the newest created event whose templateId ends with the wanted suffix."""
    if _err(resp):
        raise RuntimeError(_err(resp))
    tree = resp.get("transactionTree", resp)
    events = tree.get("eventsById", {})
    matches = []
    for _, ev in sorted(events.items(), key=lambda kv: kv[0]):
        node = ev.get("CreatedTreeEvent", {}).get("value", ev)
        cid = node.get("contractId")
        tmpl = node.get("templateId", "")
        if cid and (tmpl.endswith(template_suffix) or not template_suffix):
            matches.append(cid)
    if not matches:
        # fall back: any contractId in the tree
        import re
        cids = re.findall(r'"contractId"\s*:\s*"([^"]+)"', json_dumps(resp))
        if cids:
            return cids[-1]
        raise RuntimeError(f"no created {template_suffix} in tree: {str(resp)[:300]}")
    return matches[-1]


def json_dumps(o):
    import json as _j
    return _j.dumps(o)


def _residual_legs_and_allocs(parties, bank, operator, instr_cid, residuals, auth_cid):
    """Build residualLegs + allocations (issuing & locking funding holdings) for a
    list of (sender_party, receiver_party, amount) residual transfers."""
    legs, allocs = [], []
    short2key = {}
    for k in _present_firms(parties):
        short2key[parties[k]] = k
    for (s_party, r_party, amt) in residuals:
        s_acc = ACC[short2key[s_party]]
        r_acc = ACC[short2key[r_party]]
        leg = _leg(s_party, r_party, bank, amt, s_acc, r_acc)
        legs.append(leg)
        locked = _issue_and_lock(parties, bank, operator, instr_cid, s_party, s_acc, amt, "console-net")
        allocs.append({"leg": leg, "holdingCid": locked, "authorityCid": auth_cid})
    return legs, allocs


def seed_book(dense: bool = True) -> dict:
    """Create a confidential obligation book on the live ledger via v2 creates.
    dense=True -> a richer 12-obligation book across the 3 firms (kills 'toy data');
    dense=False -> the canonical 5-obligation book. Idempotent-ish: clears first."""
    parties = load_real_parties()
    op = RealLedgerClient(parties["operator"])
    # clear any existing book first (clean slate for the demo)
    for c in op.query("TradeGuard.Netting:Obligation"):
        op.exercise("TradeGuard.Netting:Obligation", c["contractId"], "Discharge", {})
    for c in op.query("TradeGuard.Netting:NettingBatch"):
        op.exercise("TradeGuard.Netting:NettingBatch", c["contractId"], "CancelNetting",
                    {"actor": parties["operator"]})

    bank = parties["netbank"]
    opp = parties["operator"]
    A, B, C = parties["firma"], parties["firmb"], parties["firmc"]
    instr = _instr(bank)

    if dense:
        # 12 obligations, criss-crossing. Net positions still resolve to A as sole
        # net payer (so the on-ledger settle path holds), but the GROSS is much larger.
        # A out: 100+50+60+40=250 ; A in: 80+30+20=130 -> A net -120
        # B out: 100+30+25=155 ; B in: 100+60+20=180 -> B net +25
        # C out: 80+20+20=120 ; C in: 50+40+30+25=145 -> C net +95  (check: -120+25+95=0)
        book = [
            (A, B, 100.0, "A->B inv1"), (A, C, 50.0, "A->C inv2"),
            (A, B, 60.0, "A->B inv3"),  (A, C, 40.0, "A->C inv4"),
            (B, C, 100.0, "B->C inv5"), (B, A, 30.0, "B->A inv6"),
            (B, C, 25.0, "B->C inv7"),  (C, A, 80.0, "C->A inv8"),
            (C, B, 20.0, "C->B inv9"),  (C, A, 20.0, "C->A inv10"),
            (B, A, 20.0, "B->A inv11"), (C, B, 20.0, "C->B inv12"),
        ]
    else:
        book = [(A, B, 100.0, "A->B inv1"), (B, C, 100.0, "B->C inv2"),
                (C, A, 80.0, "C->A inv3"), (A, C, 50.0, "A->C inv4"),
                (C, B, 30.0, "C->B inv5")]

    created = 0
    for payer, payee, amt, ref in book:
        r = RealLedgerClient(payer).create(
            "TradeGuard.Netting:Obligation",
            {"payer": payer, "payee": payee, "operator": opp,
             "instrument": instr, "amount": amt, "reference": ref},
            act_as=[payer, payee])
        if not _err(r):
            created += 1
    return {"ok": created == len(book), "created": created, "total": len(book)}


def settle_real() -> dict:
    """Settle the existing seeded book atomically via v2. Fast (~2-3s)."""
    parties = load_real_parties()
    bank = parties["netbank"]
    operator = parties["operator"]
    facts_raw = _book_facts(parties)
    if not facts_raw:
        return {"ok": False, "error": "no seeded book to settle"}

    # compute the net + minimal residuals (off-chain agent brain)
    obs = [Obligation(payer=_short(p), payee=_short(q), amount=a) for (p, q, a) in facts_raw]
    residuals_short = minimal_settlement(obs)

    # map short names back to full party ids
    short2full = {_short(parties[k]): parties[k] for k in _present_firms(parties)}
    residuals = [(short2full[t.sender], short2full[t.receiver], t.amount) for t in residuals_short]

    instr_cid = _instrument_cid(parties, bank)
    if not instr_cid:
        instr_cid = next(i["contractId"] for i in RealLedgerClient(bank).query("TradeGuard.Instrument:Instrument")
                         if i["payload"]["id"]["unpack"] == USD_ID)
    auth_cid = _authority_cid(parties, bank, operator)
    if not auth_cid:
        auth_cid = next(a["contractId"] for a in RealLedgerClient(bank).query("TradeGuard.Settlement:SettlementAuthority")
                        if a["payload"]["coordinator"] == operator)

    # ensure cash accounts for every involved firm
    involved = set()
    for (p, q, a) in facts_raw:
        involved.add(p); involved.add(q)
    short2key = {parties[k]: k for k in _present_firms(parties)}
    for party in involved:
        _ensure_account(parties, bank, party, ACC[short2key[party]])

    # obligation cids + facts (NetTransfer encoding: sender/receiver/amount)
    op = RealLedgerClient(operator)
    obl_rows = op.query("TradeGuard.Netting:Obligation")
    obl_cids = [c["contractId"] for c in obl_rows]
    obl_facts = [{"sender": c["payload"]["payer"], "receiver": c["payload"]["payee"],
                  "amount": c["payload"]["amount"]} for c in obl_rows]

    legs, allocs = _residual_legs_and_allocs(parties, bank, operator, instr_cid, residuals, auth_cid)

    firm_parties = [short2full[s] for s in short2full]
    batch_payload = {
        "operator": operator, "obligations": obl_cids, "obligationFacts": obl_facts,
        "residualLegs": legs, "cashInstrument": _instr(bank),
        "parties": _parties_set(sorted(involved)),
        "regulator": parties.get("netreg"), "status": "Pending"}
    r = op.create_tree("TradeGuard.Netting:NettingBatch", batch_payload)
    if _err(r):
        return {"ok": False, "error": f"batch create failed: {_err(r)}"}
    batch_cid = _tree_created_cid(r, "TradeGuard.Netting:NettingBatch")

    # settle: controller = operator :: parties
    actors = [operator] + sorted(involved)
    rs = op.exercise("TradeGuard.Netting:NettingBatch", batch_cid, "SettleNetting",
                     {"allocations": allocs}, act_as=actors)
    e = _err(rs)
    if e:
        return {"ok": False, "error": f"settle failed: {e}"}
    gross = round(sum(a for (_, _, a) in facts_raw), 2)
    net = round(sum(t.amount for t in residuals_short), 2)
    return {"ok": True, "gross": gross, "net": net,
            "discharged": len(obl_cids), "residuals": len(residuals)}


def attempt_fraud() -> dict:
    """Submit a REAL fraudulent NettingBatch to the LIVE ledger: residuals that
    under-settle the netted positions. The on-ledger conservation guard MUST reject
    it. Returns the actual ledger error so the UI can show the guard firing.

    Non-destructive: even if (impossibly) it didn't reject, it only moves a tiny
    holding. In practice the SettleNetting choice aborts before discharging anything.
    """
    parties = load_real_parties()
    bank = parties["netbank"]
    operator = parties["operator"]
    facts_raw = _book_facts(parties)
    if not facts_raw:
        return {"ok": False, "error": "seed a book first"}

    op = RealLedgerClient(operator)
    obl_rows = op.query("TradeGuard.Netting:Obligation")
    obl_cids = [c["contractId"] for c in obl_rows]
    obl_facts = [{"sender": c["payload"]["payer"], "receiver": c["payload"]["payee"],
                  "amount": c["payload"]["amount"]} for c in obl_rows]

    instr_cid = _instrument_cid(parties, bank)
    auth_cid = _authority_cid(parties, bank, operator)
    involved = sorted({p for (p, q, a) in facts_raw} | {q for (p, q, a) in facts_raw})
    short2key = {parties[k]: k for k in _present_firms(parties)}
    for party in involved:
        _ensure_account(parties, bank, party, ACC[short2key[party]])

    # THE FRAUD: pick the true net payer, but propose a residual that pays only a
    # FRACTION of what's owed (under-settlement). Conservation guard must reject.
    obs = [Obligation(payer=_short(p), payee=_short(q), amount=a) for (p, q, a) in facts_raw]
    net = net_positions(obs)
    short2full = {_short(parties[k]): parties[k] for k in _present_firms(parties)}
    payer_short = min(net, key=lambda k: net[k])     # most-negative = biggest payer
    recv_short = max(net, key=lambda k: net[k])      # most-positive = biggest receiver
    full_owed = abs(net[recv_short])
    fraud_amt = round(max(1.0, full_owed * 0.1), 2)  # pay only 10%
    payer = short2full[payer_short]; receiver = short2full[recv_short]

    leg = _leg(payer, receiver, bank, fraud_amt, ACC[short2key[payer]], ACC[short2key[receiver]])
    locked = _issue_and_lock(parties, bank, operator, instr_cid, payer,
                             ACC[short2key[payer]], fraud_amt, "fraud-attempt")
    alloc = {"leg": leg, "holdingCid": locked, "authorityCid": auth_cid}

    batch_payload = {
        "operator": operator, "obligations": obl_cids, "obligationFacts": obl_facts,
        "residualLegs": [leg], "cashInstrument": _instr(bank),
        "parties": _parties_set(involved),
        "regulator": parties.get("netreg"), "status": "Pending"}
    rb = op.create_tree("TradeGuard.Netting:NettingBatch", batch_payload)
    if _err(rb):
        return {"ok": False, "error": f"batch create failed: {_err(rb)}"}
    batch_cid = _tree_created_cid(rb, "TradeGuard.Netting:NettingBatch")

    actors = [operator] + involved
    rs = op.exercise("TradeGuard.Netting:NettingBatch", batch_cid, "SettleNetting",
                     {"allocations": [alloc]}, act_as=actors)
    err = _err(rs)
    if err:
        # extract the human-readable guard message
        msg = err
        import re
        m = re.search(r"netting must conserve value[^\"\\]*", err)
        if m:
            msg = m.group(0)
        return {"ok": True, "rejected": True,
                "fraud": f"{payer_short} proposed to pay {recv_short} only {fraud_amt:.0f} "
                         f"of {full_owed:.0f} owed",
                "ledger_error": msg[:300]}
    # should not happen
    return {"ok": True, "rejected": False,
            "warn": "ledger accepted the under-settlement (unexpected!)"}


if __name__ == "__main__":
    import json
    action = sys.argv[1] if len(sys.argv) > 1 else "settle"
    print(json.dumps(settle_real() if action == "settle" else attempt_fraud(), indent=2))
