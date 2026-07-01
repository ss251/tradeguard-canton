"""Real-network ledger client — Canton JSON Ledger API v2.

Two target networks, selected by env:
  * TG_NET=local (default): Canton Builder LocalNet on :3975. HS256 self-signed token
    (secret "unsafe"), one admin user with CanActAs for all TG parties.
  * TG_NET=devnet: the 5N Seaport sandbox DevNet validator. Real OIDC M2M
    client-credentials auth (RS256 JWT, 8h expiry, auto-refreshed). Parties are
    allocated on the validator and the ledger-api user is granted CanActAs.

Both speak JSON API v2 (/v2/state/active-contracts, /v2/commands, ...). The only
differences are host, auth, and the parties file — everything else is shared.

Package refs use the package-NAME form (#tradeguard), which both networks accept.

NOTE (v2 JSON quirk): integer contract fields must be encoded as JSON STRINGS
("1", not 1) — the v2 codec rejects bare ints ("Expected ujson.Str"). _stringify_ints
handles this transparently for create/exercise payloads.
"""
from __future__ import annotations
import base64, hashlib, hmac, json, os, time, urllib.request, urllib.error
from dataclasses import dataclass, field

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = "#tradeguard"

# ── network selection ────────────────────────────────────────────────────────
NET = os.environ.get("TG_NET", "local").lower()
_IS_DEVNET = NET in ("devnet", "dev")

if _IS_DEVNET:
    HOST = os.environ.get("TG_DEVNET_LEDGER", "https://ledger-api.validator.devnet.sandbox.fivenorth.io").rstrip("/")
    REAL_PARTIES = os.path.join(PROJECT, "tradeguard-v3", "devnet-parties.json")
else:
    HOST = os.environ.get("TG_REAL_HOST", "http://localhost:3975").rstrip("/")
    REAL_PARTIES = os.path.join(PROJECT, "tradeguard-v3", "real-init-result.json")

SECRET = "unsafe"  # LocalNet only


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _local_token() -> str:
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64(json.dumps({
        "sub": "ledger-api-user",
        "aud": "https://canton.network.global",
        "scope": "daml_ledger_api",
    }).encode())
    sig = _b64(hmac.new(SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
    return f"{header}.{payload}.{sig}"


# ── DevNet OIDC M2M token manager (fetch + cache + auto-refresh) ──────────────
class _DevnetAuth:
    """Client-credentials token cache. Refreshes ~2 min before the 8h expiry."""
    def __init__(self):
        self._token: str | None = None
        self._exp: float = 0.0
        self.token_url = os.environ.get("TG_DEVNET_TOKEN_URL", "")
        self.client_id = os.environ.get("TG_DEVNET_CLIENT_ID", "")
        self.client_secret = os.environ.get("TG_DEVNET_CLIENT_SECRET", "")
        self.audience = os.environ.get("TG_DEVNET_AUDIENCE", "")
        self.scope = os.environ.get("TG_DEVNET_SCOPE", "daml_ledger_api")
        if not (self.token_url and self.client_id and self.client_secret):
            raise RuntimeError(
                "TG_NET=devnet but OIDC creds missing. Run: source ~/.tradeguard/devnet.env")

    def token(self) -> str:
        if self._token and time.time() < self._exp - 120:
            return self._token
        data = urllib.parse.urlencode({
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "audience": self.audience,
            "scope": self.scope,
        }).encode()
        req = urllib.request.Request(self.token_url, data=data, method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = json.load(r)
        self._token = resp["access_token"]
        self._exp = time.time() + int(resp.get("expires_in", 28800))
        assert self._token is not None
        return self._token


import urllib.parse  # noqa: E402 (used by _DevnetAuth)

_DEVNET_AUTH = _DevnetAuth() if _IS_DEVNET else None


def _auth_token() -> str:
    if _IS_DEVNET:
        assert _DEVNET_AUTH is not None
        return _DEVNET_AUTH.token()
    return _local_token()


def load_real_parties() -> dict[str, str]:
    with open(REAL_PARTIES) as f:
        return json.load(f)


def _stringify_ints(obj):
    """v2 JSON codec wants Numeric/Int contract fields as strings. Recursively
    convert bare ints (not bools) to strings inside a create/exercise payload."""
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, int):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _stringify_ints(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_stringify_ints(v) for v in obj]
    return obj


@dataclass
class RealLedgerClient:
    """JSON API v2 client for the real Canton network (LocalNet or DevNet). Acts as
    `party`; the ledger-api user has CanActAs for the TG parties."""
    party: str

    def __post_init__(self):
        self.token = _auth_token()

    def _hdr(self) -> dict:
        # refresh the token each call on devnet (cheap; cached until near expiry)
        return {"Authorization": f"Bearer {_auth_token()}"}

    def tid(self, module_entity: str) -> str:
        return f"{PKG}:{module_entity}"

    def _post(self, path: str, body: dict) -> dict:
        req = urllib.request.Request(HOST + path, data=json.dumps(body).encode(),
            method="POST", headers={**self._hdr(), "Content-Type": "application/json"})
        # DevNet's shared consensus is far slower than LocalNet; give commands room.
        timeout = 120 if _IS_DEVNET else 40
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            return {"_http_error": e.code, "_body": e.read().decode()[:600]}

    def _ledger_end(self) -> int:
        req = urllib.request.Request(HOST + "/v2/state/ledger-end", method="GET",
            headers=self._hdr())
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r).get("offset", 0)
        except Exception:
            return 0

    def query(self, module_entity: str) -> list[dict]:
        """Active contracts of a template visible to `party` (WildcardFilter ACS,
        filtered by template id client-side)."""
        end = self._ledger_end()
        body = {
            "filter": {"filtersByParty": {self.party: {
                "cumulative": [{"identifierFilter": {
                    "WildcardFilter": {"value": {"includeCreatedEventBlob": False}}}}]
            }}},
            "verbose": False,
            "activeAtOffset": end,
        }
        resp = self._post("/v2/state/active-contracts", body)
        if isinstance(resp, dict) and "_http_error" in resp:
            return []
        items = resp if isinstance(resp, list) else resp.get("result", [])
        want = self.tid(module_entity)
        want_suffix = module_entity
        out = []
        for it in items:
            ce = (it.get("contractEntry", {}).get("JsActiveContract", {})
                    .get("createdEvent")) if isinstance(it, dict) else None
            if not ce:
                continue
            tmpl = ce.get("templateId", "")
            if tmpl.endswith(want_suffix) or tmpl == want:
                out.append({"contractId": ce.get("contractId"),
                            "payload": ce.get("createArgument", {})})
        return out

    def create(self, module_entity: str, payload: dict, act_as: list[str] | None = None) -> dict:
        actors = act_as or [self.party]
        body = {"commands": [{"CreateCommand": {
            "templateId": self.tid(module_entity), "createArguments": _stringify_ints(payload)}}],
            "commandId": f"tg-{os.urandom(4).hex()}",
            "actAs": actors, "readAs": actors}
        return self._post("/v2/commands/submit-and-wait", body)

    def create_tree(self, module_entity: str, payload: dict, act_as: list[str] | None = None) -> dict:
        actors = act_as or [self.party]
        body = {"commands": [{"CreateCommand": {
            "templateId": self.tid(module_entity), "createArguments": _stringify_ints(payload)}}],
            "commandId": f"tg-{os.urandom(4).hex()}",
            "actAs": actors, "readAs": actors}
        return self._post("/v2/commands/submit-and-wait-for-transaction-tree", body)

    def exercise_tree(self, module_entity: str, contract_id: str, choice: str,
                      argument: dict | None = None, act_as: list[str] | None = None) -> dict:
        actors = act_as or [self.party]
        body = {"commands": [{"ExerciseCommand": {
            "templateId": self.tid(module_entity), "contractId": contract_id,
            "choice": choice, "choiceArgument": _stringify_ints(argument or {})}}],
            "commandId": f"tg-{os.urandom(4).hex()}",
            "actAs": actors, "readAs": actors}
        return self._post("/v2/commands/submit-and-wait-for-transaction-tree", body)

    def exercise(self, module_entity: str, contract_id: str, choice: str,
                 argument: dict | None = None, act_as: list[str] | None = None) -> dict:
        actors = act_as or [self.party]
        body = {"commands": [{"ExerciseCommand": {
            "templateId": self.tid(module_entity), "contractId": contract_id,
            "choice": choice, "choiceArgument": _stringify_ints(argument or {})}}],
            "commandId": f"tg-{os.urandom(4).hex()}",
            "actAs": actors, "readAs": actors}
        return self._post("/v2/commands/submit-and-wait", body)

    def ready(self) -> bool:
        try:
            with urllib.request.urlopen(HOST + "/readyz", timeout=5) as r:
                return r.status == 200
        except Exception:
            # devnet has no /readyz; probe ledger-end instead
            return self._ledger_end() > 0


# backward-compat alias (older code imports admin_token)
def admin_token() -> str:
    return _auth_token()
