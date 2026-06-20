# TradeGuard

**Private multilateral netting + atomic settlement for B2B trade finance — on Canton.**

TradeGuard is a settlement-optimization application for the [Build on Canton](https://www.encodeclub.com/) hackathon. Its headline capability is the thing a transparent chain *cannot* safely do:

> **Net a book of obligations across many parties who can't see each other's positions, then settle only the residuals — atomically.**

A governed AI agent, acting as an authorized netting operator, is the only party that sees the whole book. It computes the multilateral net, proposes the minimal residual settlement, waits for human approval, and then discharges every obligation **and** moves only the residual cash in a single all-or-nothing transaction. In our live run, **5 obligations across 3 firms (360 gross) net to 2 transfers (70) — 80.6% of value never moves.**

It is:

- **Privacy-optimizing** — netting requires seeing many parties' positions. On a transparent chain that means exposing every position publicly. Here each obligation is visible only to its two counterparties and the operator; **no firm sees the whole book.** The optimization is only *safe* because privacy is the substrate. *(Proven live: FirmA/B/C each see only their own obligations; the operator sees all; an outsider sees nothing.)*
- **Atomic** — obligations discharge and residual cash moves in one transaction, or neither does. No Herstatt/settlement risk; the failure mode is "nothing happened," never "money is stuck." The underlying primitive is an atomic Delivery-versus-Payment (DvP) engine (tokenized asset leg ⇄ cash leg).
- **Governed by a real agent** — the off-chain agent monitors the ledger, decides with an auditable rationale, and **proposes** — it can never move assets on its own. A human approval (an on-ledger `ApprovedAction`) gates every settlement.
- **Adversarially safe** — the netting contract enforces, on-ledger, that a proposal *conserves value* (residual net per party equals the netted obligations), is *efficient* (residual gross ≤ obligation gross), and is *funded* (an underfunded leg rolls back the whole transaction). A fraudulent under-settlement is rejected by the ledger, not trusted.

> **Why this needs Canton.** Multilateral netting over confidential positions is the load-bearing idea, and it is *only possible* because Canton's sub-transaction privacy lets an authorized operator net positions that the counterparties themselves can't see. Pure deterministic settlement can't deliver safe private netting alone — that's the gap TradeGuard fills.

_Scope note: TradeGuard automates the **settlement and netting layer** of trade finance. It does not replace the legal/credit machinery of a Letter of Credit (discrepancies, amendments, confirmation) — it removes the settlement risk and liquidity drag that sit on top of it._

---

## What's in the box

| Path | What |
|------|------|
| `tradeguard-v3/main/daml/TradeGuard/Netting.daml` | **Private multilateral netting** — Obligation + NettingBatch w/ on-ledger adversarial guards. |
| `tradeguard/daml/` | Institution-grade Daml model (daml-finance v4 patterns): Holdings, Instruments, atomic batch settlement, attestation gating. |
| `tradeguard-v3/` | Canton 3.x (DPM/SDK 3.4.11) keyless port — the **real-network deploy target**. |
| `tradeguard/daml/TradeGuard/Test/` | 14 Daml Script tests — netting (3), happy path, privacy, atomicity, exception, attestation, reject. |
| `agent/` | The off-chain reasoning agent (Python): `ledger_client`, `reasoner`, `netting`, `cli`. |
| `ui/` | Live role-based UI (`live.html` + `ui_server.py`) reading the real ledger over the JSON API. |
| `scripts/` | `run_stack.sh` (bring up the full stack), `demo.sh` (run the whole story), `linear_post.py`. |
| `ARCHITECTURE.md` | Deep architecture + design rationale (authorization model, atomicity, privacy). |
| `wireframes/` | Hi-fi UI design set (the design system the live UI implements). |
| `ui/console.html` + `ui/console_server.py` | **Operator Console** — the interactive app you drive the netting workflow from. |
| `deck/index.html` | The pitch deck (7 slides, netting-first). |

---

## The Operator Console (start here)

The headline experience is an **app you operate**, not a script you run. With the real
network up (`canton builder start` + `scripts/seed_real.py`):

```bash
python3 ui/console_server.py     # -> http://localhost:8090
```

Then drive the whole workflow from the browser, against the live ledger:
**Seed book** → **Compute net** (the agent's plan: 360 → 70, 80.6% netted) →
**Approve & settle** (human-approval gate → atomic on-ledger settlement) →
**Test: reject fraud** (the ledger rejects a value-violating proposal). The privacy
panel shows, live and per-party, that each firm sees only its own obligations while only
the operator sees the whole book.

---

## Quickstart (sandbox path)

```bash
# one-time: JDK 17 + Daml SDK 2.10.4 on PATH (see ARCHITECTURE.md)
source ~/.tg-env.sh

# bring up ledger + JSON API + UI, seed a scenario:
scripts/run_stack.sh

# run the full governed-agent story + prove privacy live:
scripts/demo.sh

# or step through it:
python3 -m agent.cli status              # snapshot the ledger
python3 -m agent.cli watch --once        # agent reasons -> writes a recommendation
python3 -m agent.cli approve TG-LIVE-001 # HUMAN GATE: authorize
python3 -m agent.cli settle  TG-LIVE-001 # agent settles atomically
python3 -m agent.cli net                 # multilateral netting demo

# open the live UI:
open http://localhost:8080               # switch roles -> watch the privacy boundary
```

### On the real Canton network (Canton Builder LocalNet)

```bash
# prereq: canton builder start  +  DAR deployed  (see ARCHITECTURE.md)
scripts/demo_real.sh                     # full flow on a real 3-validator network

# live UI against the real network (JSON API v2):
TG_REAL=1 python3 ui/ui_server.py        # http://localhost:8080  (header shows "Canton LocalNet")
TG_REAL=1 python3 -m agent.cli status    # agent reads the real ledger
```

## Tests

```bash
cd tradeguard && daml test          # 11 Daml scripts (ledger logic)
cd .. && python3 -m agent.test_netting   # 5 netting tests (optimization)
```

---

## The flow

```
 Seller posts TradeProposal
        │  (regulator observes; buyer can Accept/Reject)
        ▼
 Buyer Accepts ──> AcceptedTrade (buyer+seller signed)
        │
        ▼
 Registry attests delivery ──> DeliveryAttestation (conditional gate)
        │
        ▼
 AGENT monitors ──> reasons (2 legs? funded? swap? attested?) ──> SETTLE
        │
        ▼
 AGENT writes SettlementRecommendation  ⟵ auditable rationale, NO authority
        │
        ▼
 HUMAN Approves ──> ApprovedAction (on-ledger authorization)
        │
        ▼
 AGENT orchestrates ──> lock both legs ──> SettlementBatch.Settle
        │                                    (atomic: all-or-nothing)
        ▼
 SettledTrade (durable audit record; regulator-observable)
        │
        ▼
 Buyer owns the asset · Seller owns the cash · Outsider sees nothing
```

---

## Status

Built and working **end-to-end, locally** — no dependency on hackathon org access.
Deploys to the Canton DevNet sandbox (Seaport) as a final config step once the
party is whitelisted. See `STATUS.md` for the full state and `ARCHITECTURE.md` for
the deep dive.

_Apache-2.0. Built for the Build on Canton hackathon, June 2026._
