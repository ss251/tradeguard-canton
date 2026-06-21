"""Real-network ledger client — Canton JSON Ledger API v2 (Canton Builder LocalNet).

Differs from the sandbox client (ledger_client.py, JSON API v1):
  * JSON API v2 endpoints + request shapes (/v2/state/active-contracts, /v2/commands)
  * HS256-signed tokens (secret "unsafe"), one admin user that can act-as all parties
  * package-name references (#tradeguard)

Used when TG_REAL=1. Talks to the App Provider participant on :3975.
"""
from __future__ import annotations
import base64, hashlib, hmac, json, os, urllib.request, urllib.error
from dataclasses import dataclass

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL_PARTIES = os.path.join(PROJECT, "tradeguard-v3", "real-init-result.json")
HOST = os.environ.get("TG_REAL_HOST", "http://localhost:3975")
SECRET = "unsafe"
PKG = "#tradeguard"


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


def load_real_parties() -> dict[str, str]:
    with open(REAL_PARTIES) as f:
        return json.load(f)


@dataclass
class RealLedgerClient:
    """JSON API v2 client for the real Canton network. Acts as `party` (the admin
    user has CanActAs for all TG parties, so any party works)."""
    party: str

    def __post_init__(self):
        self.token = admin_token()

    def tid(self, module_entity: str) -> str:
        return f"{PKG}:{module_entity}"

    def _post(self, path: str, body: dict) -> dict:
        req = urllib.request.Request(HOST + path, data=json.dumps(body).encode(),
            method="POST", headers={"Authorization": f"Bearer {self.token}",
                                    "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            return {"_http_error": e.code, "_body": e.read().decode()[:600]}

    def _ledger_end(self) -> int:
        req = urllib.request.Request(HOST + "/v2/state/ledger-end", method="GET",
            headers={"Authorization": f"Bearer {self.token}"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r).get("offset", 0)
        except Exception:
            return 0

    def query(self, module_entity: str) -> list[dict]:
        """Active contracts of a template visible to `party`. Uses a WildcardFilter
        (the party's whole ACS) then filters by template id client-side — robust to
        the v2 identifierFilter sealed-trait encoding."""
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
        want = self.tid(module_entity)  # "#tradeguard:Module:Entity"
        want_suffix = module_entity     # "Module:Entity"
        out = []
        for it in items:
            ce = (it.get("contractEntry", {}).get("JsActiveContract", {})
                    .get("createdEvent")) if isinstance(it, dict) else None
            if not ce:
                continue
            tmpl = ce.get("templateId", "")
            # templateId comes back as "<pkgid>:Module:Entity"; match the Module:Entity tail
            if tmpl.endswith(want_suffix) or tmpl == want:
                out.append({"contractId": ce.get("contractId"),
                            "payload": ce.get("createArgument", {})})
        return out

    def create(self, module_entity: str, payload: dict, act_as: list[str] | None = None) -> dict:
        actors = act_as or [self.party]
        body = {"commands": [{"CreateCommand": {
            "templateId": self.tid(module_entity), "createArguments": payload}}],
            "commandId": f"tg-{os.urandom(4).hex()}",
            "actAs": actors, "readAs": actors}
        return self._post("/v2/commands/submit-and-wait", body)

    def create_tree(self, module_entity: str, payload: dict, act_as: list[str] | None = None) -> dict:
        """Create and return the transaction tree (so the new contractId is available)."""
        actors = act_as or [self.party]
        body = {"commands": [{"CreateCommand": {
            "templateId": self.tid(module_entity), "createArguments": payload}}],
            "commandId": f"tg-{os.urandom(4).hex()}",
            "actAs": actors, "readAs": actors}
        return self._post("/v2/commands/submit-and-wait-for-transaction-tree", body)

    def exercise_tree(self, module_entity: str, contract_id: str, choice: str,
                      argument: dict | None = None, act_as: list[str] | None = None) -> dict:
        """Exercise and return the transaction tree (created/result contracts visible)."""
        actors = act_as or [self.party]
        body = {"commands": [{"ExerciseCommand": {
            "templateId": self.tid(module_entity), "contractId": contract_id,
            "choice": choice, "choiceArgument": argument or {}}}],
            "commandId": f"tg-{os.urandom(4).hex()}",
            "actAs": actors, "readAs": actors}
        return self._post("/v2/commands/submit-and-wait-for-transaction-tree", body)

    def exercise(self, module_entity: str, contract_id: str, choice: str,
                 argument: dict | None = None, act_as: list[str] | None = None) -> dict:
        actors = act_as or [self.party]
        body = {"commands": [{"ExerciseCommand": {
            "templateId": self.tid(module_entity), "contractId": contract_id,
            "choice": choice, "choiceArgument": argument or {}}}],
            "commandId": f"tg-{os.urandom(4).hex()}",
            "actAs": actors, "readAs": actors}
        return self._post("/v2/commands/submit-and-wait", body)

    def ready(self) -> bool:
        try:
            with urllib.request.urlopen(HOST + "/readyz", timeout=5) as r:
                return r.status == 200
        except Exception:
            return False
