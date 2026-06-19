#!/usr/bin/env python3
"""Generate an insecure (unsigned) Daml JWT for a party, for the sandbox JSON API.
Usage: python3 make_token.py <partyKeyInInitResult> [outfile]
"""
import json, base64, sys, os

proj = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
init = json.load(open(os.path.join(proj, "tradeguard", "init-result.json")))
who = sys.argv[1] if len(sys.argv) > 1 else "coordinator"
party = init[who]

def b64(d):
    return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()

header = {"alg": "none", "typ": "JWT"}
payload = {"https://daml.com/ledger-api": {
    "ledgerId": "sandbox",
    "applicationId": "tradeguard-agent",
    "actAs": [party],
    "readAs": [party],
}}
token = f"{b64(header)}.{b64(payload)}."
out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(proj, "tradeguard", f"{who}-token.txt")
open(out, "w").write(token)
print(f"{who} -> {party[:36]}...")
print(f"token written to {out}")
