# TradeGuard

**Private, atomic, governed settlement for B2B trade finance — on Canton.**

TradeGuard is a settlement application for the [Build on Canton](https://www.encodeclub.com/) hackathon.
It replaces the slow, paper-heavy Letter-of-Credit process with on-ledger
**Delivery-versus-Payment (DvP)** that is:

- **Atomic** — both legs of a trade move in one transaction, or neither does. No
  Herstatt/settlement risk; the failure mode is "nothing happened," never "money
  is stuck."
- **Private** — each party sees only its own legs. A regulator gets scoped
  oversight. An outsider sees *nothing*. Enforced by Canton's sub-transaction
  privacy — not by the UI.
- **Governed by a real agent** — an off-chain reasoning agent monitors the ledger,
  decides when a trade is ready to settle (with an auditable rationale), and
  **proposes** settlement. A human must approve before the ledger executes. The
  agent can never move assets on its own.
- **Optimizing** — for multi-party books, the agent computes a multilateral **net**
  and settles only the residuals atomically (80%+ value netted out in our demo).

> **Why this needs Canton.** The agent reasons and settles over data it is a
> stakeholder in. Netting requires seeing many parties' positions — only safe when
> privacy is built into the protocol. The same logic on a transparent chain would
> leak every position it touches. TradeGuard is *only possible* because privacy is
> the substrate.

---

## What's in the box

| Path | What |
|------|------|
| `tradeguard/daml/` | Institution-grade Daml model (8 modules, ~1,150 lines), modeled on **daml-finance v4**. |
| `tradeguard/daml/TradeGuard/Test/` | 11 Daml Script tests — happy path, privacy, atomicity, exception, attestation, reject. |
| `agent/` | The off-chain reasoning agent (Python): `ledger_client`, `reasoner`, `netting`, `cli`. |
| `ui/` | Live role-based UI (`live.html` + `ui_server.py`) reading the real ledger over the JSON API. |
| `scripts/` | `run_stack.sh` (bring up the full stack), `demo.sh` (run the whole story), `linear_post.py`. |
| `ARCHITECTURE.md` | Deep architecture + design rationale (authorization model, atomicity, privacy). |
| `wireframes/` | Hi-fi UI design set (the design system the live UI implements). |

---

## Quickstart

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
