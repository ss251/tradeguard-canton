"""Thin client for the Canton JSON Ledger API (v1).

Handles per-party JWT auth, queries, creates, and exercises. Designed for the
TradeGuard settlement agent but generic enough for any party.
"""
from __future__ import annotations
import base64
import json
import os
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Any

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DAML_DIR = os.path.join(PROJECT, "tradeguard")


def _b64(d: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()


def make_token(party: str, ledger_id: str = "sandbox",
               app_id: str = "tradeguard-agent") -> str:
    """Build an insecure (unsigned) Daml JWT for the sandbox JSON API."""
    header = {"alg": "none", "typ": "JWT"}
    payload = {"https://daml.com/ledger-api": {
        "ledgerId": ledger_id,
        "applicationId": app_id,
        "actAs": [party],
        "readAs": [party],
    }}
    return f"{_b64(header)}.{_b64(payload)}."


def load_parties() -> dict[str, str]:
    """Load the seeded party ids from init-result.json."""
    with open(os.path.join(DAML_DIR, "init-result.json")) as f:
        return json.load(f)


def load_pkgid() -> str:
    with open(os.path.join(DAML_DIR, "pkgid.txt")) as f:
        return f.read().strip()


@dataclass
class LedgerClient:
    """A JSON Ledger API client scoped to one party."""
    party: str
    host: str = "http://localhost:7575"
    pkgid: str = ""

    def __post_init__(self):
        if not self.pkgid:
            self.pkgid = load_pkgid()
        self.token = make_token(self.party)

    def tid(self, module_entity: str) -> str:
        """Fully-qualify a template id: '<pkgid>:Module:Entity'."""
        return f"{self.pkgid}:{module_entity}"

    def _post(self, path: str, body: dict) -> dict:
        req = urllib.request.Request(
            self.host + path,
            data=json.dumps(body).encode(),
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            return json.load(e)

    def query(self, module_entity: str, where: dict | None = None) -> list[dict]:
        """Query active contracts of a template visible to this party."""
        body: dict[str, Any] = {"templateIds": [self.tid(module_entity)]}
        if where:
            body["query"] = where
        resp = self._post("/v1/query", body)
        return resp.get("result", [])

    def create(self, module_entity: str, payload: dict) -> dict:
        resp = self._post("/v1/create", {
            "templateId": self.tid(module_entity),
            "payload": payload,
        })
        return resp

    def exercise(self, module_entity: str, contract_id: str,
                 choice: str, argument: dict | None = None) -> dict:
        resp = self._post("/v1/exercise", {
            "templateId": self.tid(module_entity),
            "contractId": contract_id,
            "choice": choice,
            "argument": argument or {},
        })
        return resp

    def ready(self) -> bool:
        try:
            with urllib.request.urlopen(self.host + "/readyz", timeout=5) as r:
                return r.status == 200
        except Exception:
            return False
