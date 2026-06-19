"""TradeGuard settlement agent — CLI + monitoring loop.

Commands:
  status   snapshot the coordinator's view of the ledger
  watch    monitor loop: reason over accepted trades, write recommendations
  approve  human gate: approve a pending recommendation (acts as the approver party)
  reject   human gate: reject a recommendation
  settle   orchestrate the atomic batch settlement for an approved trade

Run:  python3 -m agent.cli <command> [args]
"""
from __future__ import annotations
import sys
import time
import json
import os
import subprocess

from .ledger_client import LedgerClient, load_parties
from .reasoner import evaluate_trade, Decision

# Template short names (module:entity) — the client fully-qualifies with the pkgid.
T_PROPOSAL = "TradeGuard.Trade:TradeProposal"
T_ACCEPTED = "TradeGuard.Trade:AcceptedTrade"
T_ATTEST = "TradeGuard.Trade:DeliveryAttestation"
T_RECO = "TradeGuard.Agent:SettlementRecommendation"
T_APPROVED = "TradeGuard.Agent:ApprovedAction"
T_BATCH = "TradeGuard.Settlement:SettlementBatch"


def _coord() -> LedgerClient:
    parties = load_parties()
    return LedgerClient(party=parties["coordinator"])


def _approver() -> LedgerClient:
    # In this MVP the human approver is modeled as the coordinator's principal.
    # Using a distinct 'approver' identity is a one-line change (separate party).
    parties = load_parties()
    return LedgerClient(party=parties["coordinator"])


def cmd_status() -> None:
    c = _coord()
    if not c.ready():
        print("Ledger JSON API not reachable on", c.host)
        return
    accepted = c.query(T_ACCEPTED)
    attests = c.query(T_ATTEST)
    recos = c.query(T_RECO)
    batches = c.query(T_BATCH)
    print("=== TradeGuard ledger snapshot (coordinator view) ===")
    print(f"  accepted trades : {len(accepted)}")
    print(f"  attestations    : {len(attests)}")
    print(f"  recommendations : {len(recos)}")
    print(f"  settle batches  : {len(batches)}")
    for a in accepted:
        tid = _trade_id(a["payload"]["tradeId"])
        print(f"   - AcceptedTrade {tid}  legs={len(a['payload'].get('legs', []))}")


def cmd_watch(once: bool = False, interval: int = 5) -> None:
    c = _coord()
    print("Agent watching ledger as coordinator. Ctrl-C to stop.")
    seen: set[str] = set()
    while True:
        accepted = c.query(T_ACCEPTED)
        attests = c.query(T_ATTEST)
        existing_recos = {_trade_id(r["payload"]["tradeId"]) for r in c.query(T_RECO)}
        for a in accepted:
            tid = _trade_id(a["payload"]["tradeId"])
            if tid in existing_recos:
                continue  # already recommended
            # We treat attestation as required for live trades (conservative).
            r = evaluate_trade(a, attests, requires_attestation=True)
            print(f"\n[REASON] trade {tid} -> {r.decision.value}")
            for line in r.rationale:
                print("   " + line)
            if r.decision in (Decision.SETTLE, Decision.CANCEL):
                _write_reco(c, a, r)
                print(f"[RECOMMEND] wrote SettlementRecommendation for {tid} "
                      f"(awaiting human approval).")
        if once:
            break
        time.sleep(interval)


def _write_reco(c: LedgerClient, accepted: dict, reasoning) -> None:
    parties = load_parties()
    payload = {
        "agent": parties["coordinator"],
        "approver": parties["coordinator"],
        "tradeId": {"unpack": reasoning.trade_id},
        "decision": reasoning.decision.value,
        "rationale": reasoning.rationale,
        "confidence": f"{sum(reasoning.checks.values())}/{len(reasoning.checks)} checks passed",
    }
    resp = c.create(T_RECO, payload)
    if resp.get("status") != 200:
        print("  ! failed to write recommendation:", json.dumps(resp)[:300])


def cmd_approve(trade_id: str) -> None:
    a = _approver()
    recos = a.query(T_RECO)
    match = [r for r in recos if _trade_id(r["payload"]["tradeId"]) == trade_id]
    if not match:
        print(f"No recommendation found for trade {trade_id}")
        return
    cid = match[0]["contractId"]
    resp = a.exercise(T_RECO, cid, "Approve")
    if resp.get("status") == 200:
        print(f"APPROVED recommendation for {trade_id}. "
              f"Agent is now authorized to settle.")
    else:
        print("approve failed:", json.dumps(resp)[:300])


def cmd_reject(trade_id: str, reason: str = "rejected by approver") -> None:
    a = _approver()
    recos = a.query(T_RECO)
    match = [r for r in recos if _trade_id(r["payload"]["tradeId"]) == trade_id]
    if not match:
        print(f"No recommendation found for trade {trade_id}")
        return
    cid = match[0]["contractId"]
    resp = a.exercise(T_RECO, cid, "ProcessRejection", {"reason": reason})
    print("rejected." if resp.get("status") == 200 else f"reject failed: {json.dumps(resp)[:200]}")


def cmd_settle(trade_id: str = "TG-LIVE-001") -> None:
    """Orchestrate atomic settlement for an APPROVED trade.

    Verifies a human ApprovedAction exists, then invokes the on-ledger
    orchestration (lock -> assemble -> allocate -> settle atomically) via the
    tested Daml Script. The agent only ever calls this after human approval.
    """
    a = _coord()
    approvals = a.query(T_APPROVED)
    matched = [x for x in approvals
               if _trade_id(x["payload"]["tradeId"]) == trade_id
               and x["payload"].get("decision") == "SETTLE"]
    if not matched:
        print(f"REFUSED: no human-approved SETTLE action for {trade_id}. "
              f"A human must approve first (python3 -m agent.cli approve {trade_id}).")
        return
    print(f"Approval found for {trade_id}. Orchestrating atomic settlement...")
    daml_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "tradeguard")
    env = dict(os.environ)
    # ensure daml + java on PATH
    home = os.path.expanduser("~")
    env["PATH"] = (f"{home}/.daml/bin:"
                   f"/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin:"
                   + env.get("PATH", ""))
    cmd = [
        "daml", "script",
        "--dar", ".daml/dist/tradeguard-1.0.0.dar",
        "--script-name", "TradeGuard.Orchestrate:orchestrateLive",
        "--ledger-host", "localhost", "--ledger-port", "6865",
    ]
    proc = subprocess.run(cmd, cwd=daml_dir, env=env,
                          capture_output=True, text=True, timeout=180)
    out = (proc.stdout + proc.stderr)
    if proc.returncode == 0:
        print(f"SETTLED atomically. Asset -> buyer, cash -> seller, in one transaction.")
    else:
        err = [l for l in out.splitlines()
               if "error" in l.lower() or "exception" in l.lower()
               or "abort" in l.lower()][:4]
        print("settlement failed:")
        for l in err:
            print("  " + l[:160])


def cmd_net() -> None:
    """Demonstrate multilateral netting over a realistic multi-party book.

    Shows the settlement-optimization the agent performs BEFORE settling: net a set
    of bilateral obligations down to minimal residual transfers, then those residuals
    would settle atomically as one SettlementBatch.
    """
    from .netting import Obligation, netting_report
    # A realistic trade-finance circle: 3 firms with criss-crossing obligations.
    book = [
        Obligation("Importer Co.", "Exporter Ltd.", 100_000),
        Obligation("Exporter Ltd.", "Logistics SA", 100_000),
        Obligation("Logistics SA", "Importer Co.", 80_000),
        Obligation("Importer Co.", "Logistics SA", 50_000),
        Obligation("Logistics SA", "Exporter Ltd.", 30_000),
    ]
    rep = netting_report(book, instrument="USD")
    print("=== TradeGuard multilateral netting (agent optimization) ===")
    print(f"  gross: {rep['gross_obligations']} obligations, "
          f"{rep['gross_value']:,.0f} USD total")
    print("  net positions:")
    for p, v in rep["net_positions"].items():
        sign = "receives" if v > 0 else ("pays" if v < 0 else "flat")
        print(f"     {p:16s} {sign:8s} {abs(v):>10,.0f} USD")
    print(f"  residual transfers ({rep['residual_count']}, vs {rep['gross_obligations']} gross):")
    for t in rep["residual_transfers"]:
        print(f"     {t['sender']:16s} -> {t['receiver']:16s} {t['amount']:>10,.0f} USD")
    print(f"  >> {rep['netting_efficiency_pct']}% of gross value netted out "
          f"({rep['value_netted_out']:,.0f} of {rep['gross_value']:,.0f} USD)")
    print("  >> residuals settle atomically as ONE SettlementBatch (all-or-nothing)")


def _trade_id(idval) -> str:
    if isinstance(idval, dict):
        return str(idval.get("unpack", idval))
    return str(idval)


def main(argv: list[str]) -> None:
    if not argv:
        print(__doc__)
        return
    cmd = argv[0]
    if cmd == "status":
        cmd_status()
    elif cmd == "watch":
        cmd_watch(once="--once" in argv)
    elif cmd == "approve":
        cmd_approve(argv[1])
    elif cmd == "reject":
        cmd_reject(argv[1], argv[2] if len(argv) > 2 else "rejected")
    elif cmd == "settle":
        cmd_settle(argv[1] if len(argv) > 1 else "TG-LIVE-001")
    elif cmd == "net":
        cmd_net()
    else:
        print("unknown command:", cmd)
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
