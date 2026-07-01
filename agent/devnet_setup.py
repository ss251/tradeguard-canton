"""Allocate TradeGuard's parties on the DevNet validator + grant the ledger-api user
CanActAs, then write devnet-parties.json (same key names as the LocalNet parties file
so all downstream agent code works unchanged).

Idempotent: if a party hint already resolves to an existing party on the validator,
it is reused rather than re-allocated. Run with the devnet env sourced:

    source ~/.tradeguard/devnet.env
    TG_NET=devnet .venv/bin/python -m agent.devnet_setup
"""
from __future__ import annotations
import json, os, sys, urllib.request, urllib.error, urllib.parse

BASE = os.environ["TG_DEVNET_LEDGER"].rstrip("/")
TOKEN_URL = os.environ["TG_DEVNET_TOKEN_URL"]
CLIENT_ID = os.environ["TG_DEVNET_CLIENT_ID"]
CLIENT_SECRET = os.environ["TG_DEVNET_CLIENT_SECRET"]
AUDIENCE = os.environ["TG_DEVNET_AUDIENCE"]
SCOPE = os.environ.get("TG_DEVNET_SCOPE", "daml_ledger_api")

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(PROJECT, "tradeguard-v3", "devnet-parties.json")

# TradeGuard party roster: key -> partyIdHint. Prefixed 'tg' to avoid collisions on
# the shared validator. These keys match the LocalNet real-init-result.json exactly.
ROSTER = {
    "firma": "tgFirmA", "firmb": "tgFirmB", "firmc": "tgFirmC",
    "operator": "tgOperator", "netbank": "tgNetBank", "netreg": "tgNetReg",
    "netout": "tgNetOut",
}


def _token() -> str:
    data = urllib.parse.urlencode({
        "grant_type": "client_credentials", "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET, "audience": AUDIENCE, "scope": SCOPE,
    }).encode()
    req = urllib.request.Request(TOKEN_URL, data=data, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["access_token"]


def _get(path: str, tok: str) -> dict:
    req = urllib.request.Request(BASE + path, method="GET",
        headers={"Authorization": f"Bearer {tok}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def _post(path: str, body: dict, tok: str) -> tuple[int, dict]:
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(),
        method="POST", headers={"Authorization": f"Bearer {tok}",
                                "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, {"_body": e.read().decode()[:400]}


def main() -> int:
    tok = _token()
    # who am I (the ledger-api user)?
    me = _get("/v2/users/me" if False else "/v2/authenticated-user", tok) if False else None
    # the token's user id: decode sub from the JWT
    import base64
    sub = json.loads(base64.urlsafe_b64decode(
        tok.split(".")[1] + "===").decode()).get("sub", "")
    print(f"ledger-api user (sub): {sub}")

    # existing parties on the validator (to reuse by hint prefix)
    existing = {}
    try:
        pl = _get("/v2/parties", tok).get("partyDetails", [])
        for p in pl:
            pid = p.get("party", "")
            hint = pid.split("::")[0]
            existing[hint] = pid
    except Exception as e:
        print(f"(warning: could not list parties: {e})")

    parties: dict[str, str] = {}
    for key, hint in ROSTER.items():
        if hint in existing:
            parties[key] = existing[hint]
            print(f"  reuse  {key:9s} -> {existing[hint]}")
            continue
        status, resp = _post("/v2/parties", {"partyIdHint": hint, "identityProviderId": ""}, tok)
        if status != 200:
            print(f"  FAIL   {key}: {resp}")
            return 1
        pid = resp["partyDetails"]["party"]
        parties[key] = pid
        print(f"  alloc  {key:9s} -> {pid}")

    # grant the ledger-api user CanActAs on every party
    rights = [{"kind": {"CanActAs": {"value": {"party": pid}}}} for pid in parties.values()]
    status, resp = _post(f"/v2/users/{sub}/rights",
                         {"userId": sub, "rights": rights}, tok)
    print(f"grant CanActAs: HTTP {status}, newly granted "
          f"{len(resp.get('newlyGrantedRights', []))}")

    with open(OUT, "w") as f:
        json.dump(parties, f, indent=1)
    print(f"wrote {OUT} ({len(parties)} parties)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
