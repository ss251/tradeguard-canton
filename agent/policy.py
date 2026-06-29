"""LLM policy layer — the steering wheel, NOT the engine.

A risk officer types a policy in plain English ("minimize FirmA's exposure to
FirmC", "cap what FirmA owes FirmB at 50 USD"). This module translates that into a
SMALL, STRICTLY-VALIDATED structured policy — objective weights per (payer,receiver)
arc plus optional credit-limit overrides — which feeds the deterministic solver
(agent/solver.py). The solver and the on-ledger guards do the real work and cannot
be talked past: a bad/garbled LLM response degrades to "invalid policy", never a
broken or unsafe settlement.

Two backends, same output contract:
  * LLM backend  — the real `claude` CLI with --output-format json + a strict
    --json-schema. Used when available and not disabled.
  * rules backend — a deterministic regex parser for the common policy phrasings.
    Always available; used as fallback and for tests (no network, repeatable).

Design rules (from the build spec):
  * the LLM ONLY emits a validated JSON delta — it never does arithmetic;
  * every party named must exist in the book context, or the policy is rejected;
  * weights and limits must be non-negative;
  * if validation fails we return a Policy with source="invalid" and the reason —
    the caller surfaces it; we NEVER silently fabricate a plan.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field

from agent.solver import CreditLimit

# objective-weight applied to an arc the policy wants to discourage. The solver
# minimizes (1 + weight) * flow on that arc, so a large weight pushes flow away.
DEFAULT_PENALTY = 5.0
CLAUDE_TIMEOUT = int(os.environ.get("TG_POLICY_TIMEOUT", "90"))


@dataclass
class PolicyContext:
    """What the policy may reference: the parties and currencies in the book."""
    parties: list[str]                      # short names, e.g. ["FirmA","FirmB","FirmC"]
    currencies: list[str] = field(default_factory=lambda: ["USD"])

    def norm_party(self, name: str) -> str | None:
        """Resolve a free-text party reference to a known party (case/space-insensitive)."""
        if not name:
            return None
        target = re.sub(r"[^a-z0-9]", "", name.lower())
        for p in self.parties:
            if re.sub(r"[^a-z0-9]", "", p.lower()) == target:
                return p
        # allow "A" -> "FirmA" style suffix match
        for p in self.parties:
            if re.sub(r"[^a-z0-9]", "", p.lower()).endswith(target) and target:
                return p
        return None

    def norm_ccy(self, name: str | None) -> str:
        if not name:
            return self.currencies[0] if self.currencies else "USD"
        u = name.strip().upper()
        return u if u in self.currencies else (self.currencies[0] if self.currencies else "USD")


@dataclass
class Policy:
    """A validated, structured policy ready to feed the solver."""
    objective_weights: dict[tuple[str, str], float] = field(default_factory=dict)
    credit_limits: list[CreditLimit] = field(default_factory=list)
    interpretation: str = ""
    source: str = "rules"                   # "llm" | "rules" | "invalid"
    errors: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return self.source != "invalid"

    def to_solver_inputs(self) -> tuple[dict[tuple[str, str], float], list[CreditLimit]]:
        return self.objective_weights, self.credit_limits

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "valid": self.valid,
            "interpretation": self.interpretation,
            "objective_weights": [
                {"payer": p, "receiver": r, "weight": w}
                for (p, r), w in self.objective_weights.items()
            ],
            "credit_limits": [
                {"from": cl.frm, "to": cl.to, "currency": cl.currency, "limit": cl.limit}
                for cl in self.credit_limits
            ],
            "errors": self.errors,
        }


# --- the structured schema the LLM must emit -------------------------------------

POLICY_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["objective_weights", "credit_limits", "interpretation"],
    "properties": {
        "objective_weights": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["payer", "receiver", "weight"],
                "properties": {
                    "payer": {"type": "string"},
                    "receiver": {"type": "string"},
                    "weight": {"type": "number"},
                },
            },
        },
        "credit_limits": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["from", "to", "currency", "limit"],
                "properties": {
                    "from": {"type": "string"},
                    "to": {"type": "string"},
                    "currency": {"type": "string"},
                    "limit": {"type": "number"},
                },
            },
        },
        "interpretation": {"type": "string"},
    },
}


def _system_prompt(ctx: PolicyContext) -> str:
    return (
        "You translate a treasury risk officer's natural-language netting policy into a "
        "structured JSON delta for a deterministic settlement solver. You do NOT compute "
        "any settlement yourself.\n\n"
        f"Parties in the book (use these EXACT names): {ctx.parties}\n"
        f"Currencies: {ctx.currencies}\n\n"
        "Output rules:\n"
        "- objective_weights: arcs the policy wants to DISCOURAGE. Each is "
        "{payer, receiver, weight}; higher weight => the solver avoids routing that "
        "payer->receiver residual. Use weight 5 for 'minimize/avoid', 10 for 'strongly "
        "avoid'. To FAVOR an arc, leave it out (default weight 0) and optionally penalize "
        "the alternatives.\n"
        "- credit_limits: hard caps the ledger will enforce. Each is "
        "{from, to, currency, limit} meaning 'from' may owe 'to' at most 'limit' in that "
        "currency after netting.\n"
        "- Only use party names from the list above. If the policy names an unknown "
        "party, omit that clause.\n"
        "- interpretation: one sentence describing what you encoded.\n"
        "Return ONLY the JSON object."
    )


def _claude_available() -> bool:
    return (
        os.environ.get("TG_POLICY_BACKEND", "").lower() != "rules"
        and shutil.which("claude") is not None
    )


def _call_claude(nl_text: str, ctx: PolicyContext) -> dict | None:
    """Call the real claude CLI with a strict JSON schema. Returns the parsed policy
    object, or None on any failure (so the caller falls back to rules).

    NOTE: --json-schema takes the schema INLINE as a JSON string, not a file path.
    """
    try:
        cmd = [
            "claude", "-p",
            "--output-format", "json",
            "--json-schema", json.dumps(POLICY_JSON_SCHEMA),
            "--append-system-prompt", _system_prompt(ctx),
            nl_text,
        ]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=CLAUDE_TIMEOUT)
        if p.returncode != 0:
            return None
        envelope = json.loads(p.stdout)
        if envelope.get("is_error"):
            return None
        result = envelope.get("result", envelope)
        # result may be a JSON string or already an object
        if isinstance(result, str):
            result = _extract_json(result)
        return result if isinstance(result, dict) else None
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        return None


def _extract_json(text: str) -> dict | None:
    """Pull the first balanced JSON object out of a text blob."""
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    return None
    return None


def _validate(raw: dict, ctx: PolicyContext) -> Policy:
    """Validate + normalize an LLM/rules policy object against the book context.

    Unknown parties are dropped (with a recorded note); a totally empty result on a
    non-empty request is still valid (it just means 'no constraints recognized')."""
    pol = Policy(source="llm")
    notes: list[str] = []

    for ow in raw.get("objective_weights", []) or []:
        payer = ctx.norm_party(str(ow.get("payer", "")))
        receiver = ctx.norm_party(str(ow.get("receiver", "")))
        try:
            weight = float(ow.get("weight", 0))
        except (TypeError, ValueError):
            weight = 0.0
        if payer and receiver and payer != receiver and weight >= 0:
            pol.objective_weights[(payer, receiver)] = weight
        else:
            notes.append(f"dropped objective_weight {ow!r}")

    for cl in raw.get("credit_limits", []) or []:
        frm = ctx.norm_party(str(cl.get("from", "")))
        to = ctx.norm_party(str(cl.get("to", "")))
        ccy = ctx.norm_ccy(cl.get("currency"))
        try:
            limit = float(cl.get("limit"))
        except (TypeError, ValueError):
            limit = -1.0
        if frm and to and frm != to and limit >= 0:
            pol.credit_limits.append(CreditLimit(frm=frm, to=to, limit=limit, currency=ccy))
        else:
            notes.append(f"dropped credit_limit {cl!r}")

    pol.interpretation = str(raw.get("interpretation", "")).strip()
    pol.errors = notes
    return pol


# --- deterministic rule-based backend (fallback + tests) -------------------------

def _parse_rules(nl_text: str, ctx: PolicyContext) -> Policy:
    """A small deterministic parser for the common policy phrasings. Order matters:
    we scan clause-by-clause (split on ';' / ',' / ' and ')."""
    pol = Policy(source="rules")
    clauses = re.split(r";|\band\b|,|\.", nl_text, flags=re.IGNORECASE)
    encoded: list[str] = []

    for clause in clauses:
        c = clause.strip()
        if not c:
            continue

        # "cap/limit/restrict ... X owes/pays/to Y ... at/to/below N [CCY]" -> credit limit
        # handles: "cap what FirmA owes FirmB at 50 USD",
        #          "limit FirmA paying FirmB to 50", "restrict FirmA to FirmB below 50 EUR"
        m = re.search(
            r"(?:cap|limit|restrict)\b[^\w]*(?:what\s+|the\s+)?"
            r"(\b\w+\b)\s+(?:owes?|pay(?:s|ing)?|to|owing)\s+(?:to\s+)?(\b\w+\b)"
            r".*?(?:at|to|below|under|of)\s+\$?\s*([\d,.]+)\s*([A-Za-z]{3})?",
            c, re.IGNORECASE)
        if m:
            frm = ctx.norm_party(m.group(1))
            to = ctx.norm_party(m.group(2))
            amt = _num(m.group(3))
            ccy = ctx.norm_ccy(m.group(4))
            if frm and to and amt is not None:
                pol.credit_limits.append(CreditLimit(frm=frm, to=to, limit=amt, currency=ccy))
                encoded.append(f"cap {frm}->{to} at {amt:g} {ccy}")
                continue

        # "minimize/avoid/reduce X['s] exposure to Y"  ->  penalize arc X->Y
        m = re.search(
            r"(minimi[sz]e|avoid|reduce|discourage|strongly avoid)\s+(?:\w+\s+)*?"
            r"(\b\w+\b)(?:'s)?\s+(?:exposure to|paying|payments? to|owing|debt to|"
            r"settling with)\s+(\b\w+\b)",
            c, re.IGNORECASE)
        if m:
            verb = m.group(1).lower()
            payer = ctx.norm_party(m.group(2))
            receiver = ctx.norm_party(m.group(3))
            weight = 10.0 if "strong" in verb else DEFAULT_PENALTY
            if payer and receiver:
                pol.objective_weights[(payer, receiver)] = weight
                encoded.append(f"penalize {payer}->{receiver} (w={weight:g})")
                continue

        # "prioritize/prefer/favor X paying Y"  ->  penalize the OTHER receivers for X
        m = re.search(
            r"(priorit[iy][sz]e|prefer|favou?r)\s+(\b\w+\b)\s+(?:paying|to pay|settling with)\s+(\b\w+\b)",
            c, re.IGNORECASE)
        if m:
            payer = ctx.norm_party(m.group(2))
            favored = ctx.norm_party(m.group(3))
            if payer and favored:
                for other in ctx.parties:
                    if other not in (payer, favored):
                        pol.objective_weights[(payer, other)] = DEFAULT_PENALTY
                encoded.append(f"prefer {payer}->{favored} (penalize {payer}'s other arcs)")
                continue

    pol.interpretation = "; ".join(encoded) if encoded else "no recognizable policy clauses"
    if not encoded:
        pol.errors.append("rules backend recognized no clauses")
    return pol


def _num(s: str) -> float | None:
    try:
        return float(s.replace(",", ""))
    except (TypeError, ValueError, AttributeError):
        return None


# --- public entry point ----------------------------------------------------------

def parse_policy(nl_text: str, ctx: PolicyContext, *, prefer_llm: bool = True) -> Policy:
    """Translate a natural-language risk policy into a validated structured Policy.

    Tries the real LLM (claude CLI) first when available; falls back to the
    deterministic rules parser. If BOTH yield nothing usable for a non-empty
    request, returns source='invalid' with a reason — never a fabricated plan.
    """
    nl_text = (nl_text or "").strip()
    if not nl_text:
        return Policy(source="rules", interpretation="empty policy (no constraints)")

    pol: Policy | None = None
    if prefer_llm and _claude_available():
        raw = _call_claude(nl_text, ctx)
        if raw is not None:
            pol = _validate(raw, ctx)

    # fall back to rules if LLM unavailable or produced nothing
    if pol is None or (not pol.objective_weights and not pol.credit_limits):
        rules_pol = _parse_rules(nl_text, ctx)
        # keep the LLM interpretation if it parsed something; else use rules
        if pol is None or (not rules_pol.errors):
            pol = rules_pol

    if not pol.objective_weights and not pol.credit_limits:
        pol.source = "invalid"
        if "could not interpret" not in " ".join(pol.errors):
            pol.errors.append(
                "could not interpret the policy into any constraint; "
                "rephrase, e.g. 'minimize FirmA exposure to FirmC' or "
                "'cap FirmA owes FirmB at 50 USD'")
    return pol


if __name__ == "__main__":
    ctx = PolicyContext(parties=["FirmA", "FirmB", "FirmC"], currencies=["USD", "EUR"])
    for txt in [
        "minimize FirmA's exposure to FirmC",
        "cap what FirmA owes FirmB at 50 USD",
        "strongly avoid FirmB paying FirmC and cap FirmA owes FirmC at 20",
        "prioritize FirmA paying FirmB",
        "make me a sandwich",
    ]:
        p = parse_policy(txt, ctx, prefer_llm=False)
        print(f"\nPOLICY: {txt!r}")
        print(json.dumps(p.to_dict(), indent=2))
