# TradeGuard — Architecture

> Private, atomic, **governed** Delivery-versus-Payment settlement for B2B trade
> finance on Canton.

TradeGuard settles trade-finance deals the way institutions actually need: both
legs move together or neither moves (atomic DvP), each party sees only its own
slice (sub-transaction privacy), a regulator gets scoped oversight, and an
off-chain reasoning **agent** proposes settlements that a **human** must authorize
before the ledger executes them.

This is the thing a public, transparent chain *cannot* do: the agent reasons and
settles over data it is a stakeholder in, and the privacy boundary is enforced by
the protocol — not painted on by the UI.

---

## The three layers

```
┌──────────────────────────────────────────────────────────────────┐
│  UI  (ui/)                                                         │
│   live.html  +  ui_server.py  — role switch = party-JWT switch     │
│   each role's view is a real /v1/query; privacy is the ledger's    │
└───────────────▲──────────────────────────────────────────────────┘
                │ JSON Ledger API (HTTP 7575)
┌───────────────┴──────────────────────────────────────────────────┐
│  AGENT  (agent/)                                                   │
│   ledger_client → reasoner → cli                                  │
│   monitor → reason (auditable) → recommend → [HUMAN GATE] → settle │
└───────────────▲──────────────────────────────────────────────────┘
                │ gRPC Ledger API (6865)
┌───────────────┴──────────────────────────────────────────────────┐
│  LEDGER  (tradeguard/daml/)   — the institution-grade Daml model   │
│   Types · Holding · Instrument · Settlement · Trade · Agent        │
└──────────────────────────────────────────────────────────────────┘
```

---

## Ledger layer (Daml)

Modeled on the **daml-finance v4** vocabulary (verified loadable on SDK 2.10.4),
kept self-contained so the core is guaranteed to build and test independently.

| Module | Responsibility |
|--------|----------------|
| `Types` | `Id`, `AccountKey`, `InstrumentKey`, `HoldingStandard`, `Quantity` — the daml-finance-mirrored type vocabulary. |
| `Holding` | `Account` + `Holding` (custody). Lock / disclose / transfer; a holding is signed by **custodian + owner**. Disclosure gives selective privacy. |
| `Instrument` | Instrument registration (depository + issuer) and holding issuance. |
| `Settlement` | **The engine.** `SettlementBatch` (N legs), `Allocate` (lock each leg), `Settle` (atomic lock→swap), `SettlementAuthority` (custodian → coordinator delegation), `SettledTrade` (durable, regulator-observable audit record). |
| `Trade` | `TradeProposal` → `Accept` → `AcceptedTrade` → `AssembleBatch`; `DeliveryAttestation` for conditional settlement. |
| `Agent` | `SettlementRecommendation` (agent's auditable proposal) + `Approve`/`ApprovedAction` (the on-ledger human gate). |
| `Init` / `Orchestrate` | Idempotent live-ledger seeding; atomic settlement orchestration invoked post-approval. |

### Why atomicity is real
`Settle` is one transaction. It exercises `ExecuteSettleTransfer` on every leg via
the custodians' delegated `SettlementAuthority`. If any leg's precondition fails,
the **entire transaction rolls back** — Daml gives all-or-nothing for free. The
failure mode is "nothing happened," never "money is stuck."

### Why privacy is real
Every contract declares explicit `signatory` / `observer` sets. A party not in
those sets cannot fetch or even see the contract — enforced by Canton's
sub-transaction privacy. The `Holding` for the asset leg is visible to its
custodian + owner (+ disclosed counterparty); an outsider's `/v1/query` returns
`[]`. We prove this in tests **and** live over HTTP with different party tokens.

### The authorization model (the subtle, institutional part)
A naive design fails: the buyer can't create a coordinator-signed batch, and the
coordinator can't move a custodian-signed holding. TradeGuard solves this exactly
how real settlement networks do — **delegation**:
- `AcceptedTrade` is signed by buyer+seller; the coordinator turns it into a batch
  it signs (`AssembleBatch`).
- Custodians grant a one-time `SettlementAuthority` to the coordinator, so the
  coordinator can execute settlement transfers without the custodian co-signing
  every trade — while the receiver's authority flows from the batch `Settle`.

---

## Agent layer (Python)

A genuine off-chain reasoning service — **not** a chat wrapper.

- **`ledger_client.py`** — JSON Ledger API client; per-party JWT; package-name
  references (`#tradeguard:…`) so it survives DAR rebuilds.
- **`reasoner.py`** — pure decision logic. For each `AcceptedTrade` it runs
  explicit checks (two legs, positive amounts, is-a-swap, delivery-attested) and
  emits `SETTLE` / `WAIT` / `CANCEL` with an **auditable rationale trail**.
- **`cli.py`** — the loop: `status`, `watch` (reason → write recommendation),
  `approve` / `reject` (human gate), `settle` (orchestrate atomic settlement,
  but only after verifying an on-ledger `ApprovedAction` exists).

**Governance is structural, not advisory.** The agent literally cannot settle
without a human-created `ApprovedAction` on the ledger — the Daml authorization
model enforces it.

---

## UI layer

`ui_server.py` bridges the browser to the ledger, injecting the right party JWT per
requested role. Switching role in `live.html` switches the token, so the buyer,
seller, regulator, and outsider each see a genuinely different view of the *same*
settled trade — the privacy story, demonstrated live, backed by real `/v1/query`s.

---

## Running it

```bash
source ~/.tg-env.sh
cd tradeguard
daml build
daml sandbox --port 6865 --dar .daml/dist/tradeguard-1.0.0.dar &
daml json-api --ledger-host localhost --ledger-port 6865 --http-port 7575 --allow-insecure-tokens &
daml script --dar .daml/dist/tradeguard-1.0.0.dar \
  --script-name TradeGuard.Init:initWithAccepted \
  --ledger-host localhost --ledger-port 6865 --output-file accepted-result.json

cd ../agent
python3 -m agent.cli status
python3 -m agent.cli watch --once     # reason + recommend
python3 -m agent.cli approve TG-LIVE-001
python3 -m agent.cli settle  TG-LIVE-001

cd ../ui && python3 ui_server.py       # http://localhost:8080
```

## Tests
```bash
cd tradeguard && daml test    # 11 scripts green: happy path, privacy, atomicity,
                              # exception/cancel, attestation, reject + setup
```
