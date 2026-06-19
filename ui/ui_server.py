#!/usr/bin/env python3
"""TradeGuard UI bridge server.

Serves the role-based UI and proxies queries to the Canton JSON Ledger API,
injecting the correct party JWT per requested role. This lets the browser show
LIVE ledger data with real sub-transaction privacy: switching role in the UI
switches the party token, so each role genuinely sees only its own slice.

Endpoints:
  GET  /                      -> the live settlement UI
  GET  /api/view?role=buyer   -> that role's view of trade TG-LIVE-001 (live)
  GET  /api/roles             -> available roles

Run: python3 ui_server.py   (after sandbox + json-api + seed are up)
"""
from __future__ import annotations
import json
import os
import sys
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
DAML_DIR = os.path.join(PROJECT, "tradeguard")
JSON_API = "http://localhost:7575"
ROLES = ["buyer", "seller", "regulator", "outsider"]

# Real-network mode (Canton Builder LocalNet, JSON API v2) when TG_REAL=1.
# Reuses the agent's proven v2 client. Privacy is still genuinely enforced: the v2
# filtersByParty query returns only contracts where that party is a stakeholder,
# regardless of the admin token's breadth (verified: outsider sees 0/0/0).
REAL = os.environ.get("TG_REAL") == "1"
if REAL:
    sys.path.insert(0, PROJECT)
    from agent.real_client import RealLedgerClient, load_real_parties

import base64


def _b64(d: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()


def token_for(party: str) -> str:
    header = {"alg": "none", "typ": "JWT"}
    payload = {"https://daml.com/ledger-api": {
        "ledgerId": "sandbox", "applicationId": "tradeguard-ui",
        "actAs": [party], "readAs": [party]}}
    return f"{_b64(header)}.{_b64(payload)}."


def load_parties() -> dict:
    if REAL:
        return load_real_parties()
    with open(os.path.join(DAML_DIR, "init-result.json")) as f:
        return json.load(f)


def ledger_query(party: str, template: str) -> list:
    if REAL:
        # v2 client: returns [{"contractId":..., "payload":...}] (same shape as v1 result)
        return RealLedgerClient(party).query(template)
    # sandbox: v1 query with package-name reference (survives DAR rebuilds)
    body = json.dumps({"templateIds": [f"#tradeguard:{template}"]}).encode()
    req = urllib.request.Request(
        JSON_API + "/v1/query", data=body,
        headers={"Authorization": f"Bearer {token_for(party)}",
                 "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r).get("result", [])
    except urllib.error.HTTPError as e:
        return []


def build_view(role: str) -> dict:
    """Build a role's live view of the settled trade from real ledger data."""
    parties = load_parties()
    party = parties[role]
    holdings = ledger_query(party, "TradeGuard.Holding:Holding")
    trades = ledger_query(party, "TradeGuard.Settlement:SettlementBatch")
    settled = ledger_query(party, "TradeGuard.Settlement:SettledTrade")
    recos = ledger_query(party, "TradeGuard.Agent:SettlementRecommendation")
    approved = ledger_query(party, "TradeGuard.Agent:ApprovedAction")
    # shape holdings for display
    hview = []
    for h in holdings:
        p = h["payload"]
        hview.append({
            "instrument": p["instrument"]["id"]["unpack"],
            "amount": p["amount"],
            "owner_is_me": p["account"]["owner"] == party,
        })
    return {
        "role": role,
        "party_short": party.split("::")[0],
        "network": "Canton LocalNet (3 validators)" if REAL else "Canton sandbox",
        "endpoint": "localhost:3975 · JSON API v2" if REAL else "localhost:7575 · JSON API v1",
        "holdings": hview,
        "holding_count": len(hview),
        "sees_settlement": len(trades) > 0 or len(settled) > 0 or len(approved) > 0,
        "settled_count": len(settled),
        "recommendation_count": len(recos),
        "approved_count": len(approved),
        # the centerpiece signal: does this role see ANYTHING about the trade?
        "sees_anything": (len(hview) > 0 or len(trades) > 0 or len(recos) > 0
                          or len(settled) > 0),
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):  # quiet
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
            with open(os.path.join(HERE, "live.html")) as f:
                self._send(200, f.read(), "text/html")
        elif u.path == "/api/roles":
            self._send(200, {"roles": ROLES})
        elif u.path == "/api/view":
            q = parse_qs(u.query)
            role = (q.get("role", ["buyer"])[0]).lower()
            if role not in ROLES:
                self._send(400, {"error": "unknown role"})
                return
            try:
                self._send(200, build_view(role))
            except Exception as e:
                self._send(500, {"error": str(e)})
        else:
            self._send(404, {"error": "not found"})


if __name__ == "__main__":
    port = 8080
    print(f"TradeGuard live UI on http://localhost:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
