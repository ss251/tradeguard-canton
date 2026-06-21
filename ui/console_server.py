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
from agent.netting import Obligation, netting_report  # noqa: E402
from agent import net_settle  # noqa: E402  (instant v2 settle + live fraud rejection)

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


def build_state() -> dict:
    """The full console state: the operator's book, the per-party privacy panel,
    the agent's computed net (if a book exists), and settlement status."""
    parties = load_real_parties()
    # operator sees the whole book — that's the canonical book
    book = _obligations_for("operator", parties)

    # per-party privacy panel: how many each viewer sees
    privacy = []
    for key, label in VIEWERS:
        obls = _obligations_for(key, parties)
        privacy.append({"key": key, "label": label, "count": len(obls),
                        "refs": [o["ref"] for o in obls]})

    # the agent's net (off-chain brain) over the operator's book
    plan = None
    if book:
        obs = [Obligation(payer=o["payer"], payee=o["payee"], amount=o["amount"]) for o in book]
        plan = netting_report(obs)

    # settlement status (operator's view). After settleSeededBook the obligations
    # are discharged (book -> 0) and residual cash holdings exist at the firms.
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

    def do_POST(self):
        u = urlparse(self.path)
        try:
            if u.path == "/api/console/seed":
                # create a dense 12-obligation book via instant v2 creates
                res = net_settle.seed_book(dense=True)
                res["state"] = build_state()
                self._send(200, res)
            elif u.path == "/api/console/compute":
                # pure read + off-chain net; no ledger write
                self._send(200, {"ok": True, "state": build_state()})
            elif u.path == "/api/console/settle":
                # human-approved atomic settle via the instant v2 client (~2-3s)
                res = net_settle.settle_real()
                res["state"] = build_state()
                self._send(200, res)
            elif u.path == "/api/console/adversarial":
                # submit a REAL fraudulent NettingBatch to the LIVE ledger; the
                # on-ledger conservation guard rejects it (returns the actual error)
                res = net_settle.attempt_fraud()
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
