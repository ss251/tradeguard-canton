#!/usr/bin/env python3
"""TradeGuard Operator Console — backend.

This turns TradeGuard from "scripts + a viewer" into an actual application you
operate. It drives the real private-netting workflow against the live Canton
network, step by step, the way an operator would:

  1. GET  /api/console/state            -> live book, per-party privacy, settlement status
  2. POST /api/console/seed             -> create the confidential obligation book on-ledger
  3. POST /api/console/compute          -> agent computes the multilateral net (off-chain brain)
  4. POST /api/console/settle           -> human-approved atomic settle of residuals (on-ledger)
  5. POST /api/console/adversarial      -> submit a fraudulent proposal; the ledger rejects it
  6. POST /api/console/reset            -> note: obligations are consumed by settle; reseed to replay

The settle/seed steps shell out to the deployed Daml Scripts (the same ones the
demo uses), so the console drives the *real* ledger — not a mock. Read steps use
the v2 client per-party, so the privacy panel is genuine sub-transaction privacy.

Run:  python3 ui/console_server.py     (real network must be up; parties seeded)
Open: http://localhost:8090
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
sys.path.insert(0, PROJECT)

from agent.real_client import RealLedgerClient, load_real_parties, admin_token  # noqa: E402
from agent.netting import Obligation  # noqa: E402
from agent.solver import solve, solve_maximal, Obligation as SolverObligation  # noqa: E402
from agent import net_settle  # noqa: E402  (instant v2 settle + live fraud rejection)
from agent import limits as limmod  # noqa: E402  (on-ledger credit-limit lifecycle)
from agent.policy import PolicyContext, parse_policy  # noqa: E402

V3_TEST = os.path.join(PROJECT, "tradeguard-v3", "test")
DAR = os.path.join(V3_TEST, ".daml", "dist", "tradeguard-test-1.0.0.dar")
TOKEN_FILE = "/tmp/tg-token.txt"
DPM = os.path.expanduser("~/.dpm/bin/dpm")

OBL_T = "TradeGuard.Netting:Obligation"
BATCH_T = "TradeGuard.Netting:NettingBatch"
SETTLED_T = "TradeGuard.Settlement:SettledTrade"
HOLDING_T = "TradeGuard.Holding:Holding"

# The 3 firms whose book we net, + the operator (agent) and an outsider.
FIRMS = ["firma", "firmb", "firmc"]
VIEWERS = [("firma", "Firm A"), ("firmb", "Firm B"), ("firmc", "Firm C"),
           ("operator", "Operator (agent)"), ("netout", "Outsider")]


def _write_token():
    with open(TOKEN_FILE, "w") as f:
        f.write(admin_token())


def _run_script(script_name: str, timeout: int = 200) -> tuple[bool, str]:
    """Run a deployed Daml Script against the real ledger via the gRPC port."""
    _write_token()
    cmd = [DPM, "script", "--dar", DAR, "--script-name", f"TradeGuard.NetLive:{script_name}",
           "--ledger-host", "localhost", "--ledger-port", "3901",
           "--access-token-file", TOKEN_FILE, "--wall-clock-time"]
    try:
        p = subprocess.run(cmd, cwd=V3_TEST, capture_output=True, text=True, timeout=timeout)
        ok = p.returncode == 0
        return ok, (p.stdout + p.stderr)[-1500:]
    except subprocess.TimeoutExpired:
        return False, "script timed out"


def _short(party: str) -> str:
    return party.split("::")[0]


def _obligations_for(party_key: str, parties: dict) -> list[dict]:
    """The obligations this party can see, shaped for the UI."""
    cli = RealLedgerClient(parties[party_key])
    out = []
    for c in cli.query(OBL_T):
        p = c["payload"]
        out.append({
            "payer": _short(p["payer"]),
            "payee": _short(p["payee"]),
            "amount": float(p["amount"]),
            "ref": p.get("reference", ""),
        })
    out.sort(key=lambda x: x["ref"])
    return out


def _solver_plan(book: list[dict], parties: dict, policy_text: str | None = None) -> dict | None:
    """Run the MAXIMAL-FEASIBLE solver over the book under the LIVE on-ledger limits
    (+ optional NL policy). Returns a JSON-serializable plan, or None if no book.

    Uses solve_maximal: settles the max-value subset that fits the constraints and
    DEFERS the rest (the product behaviour — the rail never just refuses)."""
    if not book:
        return None
    ledger_limits = limmod.load_limits(parties)
    solver_limits = limmod.to_solver_limits(ledger_limits)
    weights: dict = {}
    policy_info = None
    if policy_text:
        short_names = sorted({o["payer"] for o in book} | {o["payee"] for o in book})
        ctx = PolicyContext(parties=short_names, currencies=["USD"])
        pol = parse_policy(policy_text, ctx)
        policy_info = pol.to_dict()
        if pol.valid:
            weights, pol_limits = pol.to_solver_inputs()
            solver_limits = solver_limits + pol_limits
    obs = [SolverObligation(payer=o["payer"], payee=o["payee"], amount=o["amount"],
                            instrument="USD") for o in book]
    r = solve_maximal(obs, solver_limits, weights)
    # map settled/deferred solver indices back to the book rows (refs) for the UI
    settled_refs = [book[i].get("ref", f"#{i}") for i in r.settled_obligations]
    deferred_refs = [book[i].get("ref", f"#{i}") for i in r.deferred_obligations]
    out = {
        "feasible": r.feasible,
        "gross_obligations": r.gross_obligations,
        "gross_residual": r.gross_residual,
        "netting_efficiency_pct": r.netting_efficiency_pct,
        "net_positions": r.net_positions,
        "residual_transfers": [
            {"sender": t.sender, "receiver": t.receiver, "amount": t.amount,
             "currency": t.currency} for t in r.transfers],
        "residual_count": len(r.transfers),
        "binding_constraints": r.binding_constraints,
        "rationale": r.rationale,
        "credit_limits": [l.short() for l in ledger_limits],
        "policy": policy_info,
        # maximal-netting / graceful-degradation surface
        "settled_count": len(r.settled_obligations),
        "deferred_count": len(r.deferred_obligations),
        "settled_value": r.settled_value,
        "deferred_value": r.deferred_value,
        "settlement_rate_pct": r.settlement_rate_pct,
        "settled_refs": settled_refs,
        "deferred_refs": deferred_refs,
        "deferral_reasons": r.deferral_reasons,
        "partial": len(r.deferred_obligations) > 0,
    }
    return out


def build_state(policy_text: str | None = None) -> dict:
    """The full console state: the operator's book, the per-party privacy panel,
    the agent's CONSTRAINED plan (solver under live on-ledger limits), on-ledger
    credit limits, and settlement status."""
    parties = load_real_parties()
    # operator sees the whole book — that's the canonical book
    book = _obligations_for("operator", parties)

    # per-party privacy panel: how many each viewer sees
    privacy = []
    for key, label in VIEWERS:
        obls = _obligations_for(key, parties)
        privacy.append({"key": key, "label": label, "count": len(obls),
                        "refs": [o["ref"] for o in obls]})

    # the agent's plan: the CONSTRAINED solver over the operator's book under the
    # live on-ledger credit limits (+ optional policy steering)
    plan = _solver_plan(book, parties, policy_text)

    # on-ledger credit limits (the live risk constraints)
    ledger_limits = limmod.load_limits(parties)
    ledger_fx = limmod.load_fx_rates(parties)
    ledger_floors = limmod.load_liquidity_floors(parties)

    # settlement status (operator's view). After settle the obligations are
    # discharged (book -> 0) and residual cash holdings exist at the firms.
    op = RealLedgerClient(parties["operator"])
    settled = op.query(SETTLED_T)
    batches = op.query(BATCH_T)
    firm_holdings = sum(len(RealLedgerClient(parties[f]).query(HOLDING_T)) for f in FIRMS)

    return {
        "network": "Canton LocalNet · 3 validators · JSON Ledger API v2",
        "book": book,
        "book_size": len(book),
        "privacy": privacy,
        "plan": plan,
        "credit_limits": [
            {"from": l.frm.split("::")[0], "to": l.to.split("::")[0],
             "currency": l.currency, "limit": l.limit} for l in ledger_limits],
        "fx_rates": [
            {"base": r.base, "quote": r.quote, "rate": r.rate,
             "signers": len(r.parties)} for r in ledger_fx],
        "liquidity_floors": [
            {"party": f.party.split("::")[0], "currency": f.currency,
             "floor": f.floor} for f in ledger_floors],
        "settled_count": len(settled),
        "open_batches": len(batches),
        "residual_holdings": firm_holdings,
        "ts": time.strftime("%H:%M:%S"),
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode()
        elif isinstance(body, str):
            body = body.encode()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/":
            with open(os.path.join(HERE, "console.html")) as f:
                self._send(200, f.read(), "text/html")
        elif u.path == "/api/console/state":
            try:
                self._send(200, build_state())
            except Exception as e:
                self._send(500, {"error": str(e)})
        else:
            self._send(404, {"error": "not found"})

    def _read_body(self) -> dict:
        try:
            n = int(self.headers.get("Content-Length", 0))
            if n <= 0:
                return {}
            return json.loads(self.rfile.read(n).decode() or "{}")
        except (ValueError, json.JSONDecodeError):
            return {}

    def do_POST(self):
        u = urlparse(self.path)
        try:
            body = self._read_body()
            policy_text = (body.get("policy") or "").strip() or None

            if u.path == "/api/console/seed":
                # create a dense 12-obligation book via instant v2 creates
                res = net_settle.seed_book(dense=True)
                res["state"] = build_state()
                self._send(200, res)
            elif u.path == "/api/console/seed-partial":
                # seed the forcing scenario: a book + caps that require deferral, so the
                # console shows MAXIMAL netting settle-some / defer-some (graceful degradation)
                res = net_settle.seed_partial_book()
                res["state"] = build_state()
                self._send(200, res)
            elif u.path == "/api/console/compute":
                # pure read + CONSTRAINED solver plan (no ledger write); policy-aware
                self._send(200, {"ok": True, "state": build_state(policy_text)})
            elif u.path == "/api/console/policy":
                # parse a NL policy and show the resulting plan (no write)
                state = build_state(policy_text)
                plan = state.get("plan") or {}
                self._send(200, {"ok": True, "policy": plan.get("policy"),
                                 "state": state})
            elif u.path == "/api/console/limits":
                # seed an on-ledger CreditLimit: {from,to,limit,currency}
                res = limmod.seed_limit(
                    body.get("from", "firma"), body.get("to", "firmc"),
                    float(body.get("limit", 20.0)), body.get("currency", "USD"))
                res["state"] = build_state()
                self._send(200, res)
            elif u.path == "/api/console/limits/clear":
                res = limmod.clear_limits()
                res["state"] = build_state()
                self._send(200, res)
            elif u.path == "/api/console/settle":
                # human-approved atomic settle via the constrained solver under the
                # live on-ledger limits (~2-3s); policy-aware. Infeasible => no settle.
                res = net_settle.settle_real(policy_text)
                res["state"] = build_state()
                self._send(200, res)
            elif u.path == "/api/console/adversarial":
                # submit a REAL fraudulent NettingBatch to the LIVE ledger; the
                # on-ledger conservation guard rejects it (returns the actual error)
                res = net_settle.attempt_fraud()
                res["state"] = build_state()
                self._send(200, res)
            elif u.path == "/api/console/credit-breach":
                # seed an on-ledger CreditLimit the true plan breaches, submit the
                # conserving plan, show the ledger reject it on the credit limit
                res = net_settle.attempt_credit_breach()
                res["state"] = build_state()
                self._send(200, res)
            elif u.path == "/api/console/seed-fx":
                # seed a 2-currency book + a co-signed FX rate (cross-currency demo)
                res = net_settle.seed_fx_book()
                res["state"] = build_state()
                self._send(200, res)
            elif u.path == "/api/console/settle-fx":
                # value-net the cross-currency book at the co-signed rate and settle
                res = net_settle.settle_cross_currency()
                res["state"] = build_state()
                self._send(200, res)
            elif u.path == "/api/console/floors":
                # seed an on-ledger LiquidityFloor: {party,floor,currency}
                res = limmod.seed_liquidity_floor(
                    body.get("party", "firma"), float(body.get("floor", 50.0)),
                    body.get("currency", "USD"))
                res["state"] = build_state()
                self._send(200, res)
            elif u.path == "/api/console/clear-all":
                # clear every on-ledger constraint (limits, fx, floors)
                res = limmod.clear_all()
                res["state"] = build_state()
                self._send(200, res)
            else:
                self._send(404, {"error": "not found"})
        except Exception as e:
            self._send(500, {"error": str(e)})

    def _run_adversarial(self) -> bool:
        try:
            p = subprocess.run(
                [DPM, "test"], cwd=V3_TEST, capture_output=True, text=True, timeout=240)
            out = p.stdout + p.stderr
            return "testNettingRejectsValueViolation: ok" in out
        except Exception:
            return False


if __name__ == "__main__":
    port = 8090
    print(f"TradeGuard Operator Console on http://localhost:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
