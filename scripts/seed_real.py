#!/usr/bin/env python3
"""Seed the TradeGuard scenario on the REAL Canton network (Canton Builder LocalNet).

Unlike the sandbox seed (Daml Script with auto party allocation), the real network
uses user-based authorization. This script:
  1. allocates the 7 TradeGuard parties via the admin JSON API,
  2. grants the ledger-api-user CanActAs rights for each (so the admin token can act
     as any party — the agent then drives the whole flow),
  3. creates the scenario contracts (instruments, accounts, holdings, authorities,
     proposal, attestation, accepted trade) via JSON API v2 /v2/commands/submit.

Writes the allocated party ids to real-init-result.json for the agent/UI to use.

Run (network must be up via `canton builder start` + DAR deployed):
  python3 scripts/seed_real.py
"""
from __future__ import annotations
import base64, hashlib, hmac, json, os, sys, urllib.request, urllib.error

APP_PROVIDER = "http://localhost:3975"
SECRET = "unsafe"
PKG = "#tradeguard"  # package-name reference, survives rebuilds
PARTIES = ["Seller", "Buyer", "Regulator", "Registry", "Bank", "Coordinator", "Outsider",
           # netting scenario parties
           "FirmA", "FirmB", "FirmC", "Operator", "NetBank", "NetReg", "NetOut"]
PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(PROJECT, "tradeguard-v3", "real-init-result.json")


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def admin_token() -> str:
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64(json.dumps({
        "sub": "ledger-api-user",
        "aud": "https://canton.network.global",
        "scope": "daml_ledger_api",
    }).encode())
    sig = _b64(hmac.new(SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
    return f"{header}.{payload}.{sig}"


TOKEN = admin_token()


def api(path: str, body: dict | None = None, method: str = "POST") -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(APP_PROVIDER + path, data=data, method=method,
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"_http_error": e.code, "_body": e.read().decode()[:500]}


def allocate_parties() -> dict[str, str]:
    out: dict[str, str] = {}
    # find any already-allocated TG parties to stay idempotent
    existing = api("/v2/parties", method="GET").get("partyDetails", [])
    by_prefix = {}
    for p in existing:
        pid = p["party"]
        by_prefix[pid.split("::")[0]] = pid
    for name in PARTIES:
        if name in by_prefix:
            out[name.lower()] = by_prefix[name]
            print(f"  {name}: exists")
            continue
        resp = api("/v2/parties", {"partyIdHint": name, "identityProviderId": ""})
        pid = resp.get("partyDetails", {}).get("party")
        if not pid:
            print(f"  {name}: ALLOC FAILED {resp}")
            continue
        out[name.lower()] = pid
        print(f"  {name}: allocated")
    return out


def grant_rights(parties: dict[str, str]) -> None:
    """Grant the user CanActAs for every TG party so the admin token can act as them."""
    rights = [{"kind": {"CanActAs": {"value": {"party": pid}}}} for pid in parties.values()]
    resp = api("/v2/users/ledger-api-user/rights",
               {"userId": "ledger-api-user", "rights": rights})
    if "_http_error" in resp:
        print("  grant rights:", resp.get("_http_error"), resp.get("_body", "")[:160])
    else:
        print(f"  granted CanActAs for {len(rights)} parties")


def main() -> None:
    print("=== allocate parties on real network ===")
    parties = allocate_parties()
    print("=== grant act-as rights ===")
    grant_rights(parties)
    with open(OUT, "w") as f:
        json.dump(parties, f, indent=1)
    print(f"=== wrote {OUT} ===")
    print(json.dumps(parties, indent=1))


if __name__ == "__main__":
    main()
