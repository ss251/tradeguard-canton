# TradeGuard

**The private settlement rail where competing fintechs net their book and settle only the residual — atomically, without exposing their flow to each other. Live on Canton DevNet.**

*For payment fintechs, neobanks, and PSPs that owe each other across corridors: stop prefunding every corridor and stop leaking your flow to a trusted clearer.*

**Submitting to: Track A — Private DeFi & Capital Markets.** Why: multilateral netting over confidential positions + atomic settlement is capital-markets clearing infrastructure; privacy is the differentiator a transparent chain can't provide.

> ### ▶ [Open the live Operator Console](https://tradeguard-console-production.up.railway.app/?k=tg-9f93a696)
> Running **live on the Canton Foundation's shared DevNet** (5N Seaport validator). Click **Load a live book → Compute net → Approve & settle** and watch multilateral netting settle atomically on the real network — every settlement returns an **on-ledger receipt** (batch contract id, update id, ledger offset) surfaced right in the console. Each firm sees only its own obligations; only the operator sees the whole book. *(DevNet shared consensus is ~10–15× slower than local; a settle takes 30–90s — that's the real network being real.)*

TradeGuard is a settlement-optimization application for the [Build on Canton](https://www.encodeclub.com/) hackathon. Its headline capability is the thing a transparent chain *cannot* safely do:

> **Net a book of obligations across many parties who can't see each other's positions, then settle only the residuals — atomically.**

A governed AI agent, acting as an authorized netting operator, is the only party that sees the whole book. It computes the multilateral net, proposes the minimal residual settlement, waits for human approval, and then discharges every obligation **and** moves only the residual cash in a single all-or-nothing transaction. In our live run, **12 obligations across 3 firms (565 gross) net to 2 transfers (100) — 82.3% of value never moves.**

It is:

- **Privacy-optimizing** — netting requires seeing many parties' positions. On a transparent chain that means exposing every position publicly. Here each obligation is visible only to its two counterparties and the operator; **no firm sees the whole book.** The optimization is only *safe* because privacy is the substrate. *(Proven live: FirmA/B/C each see only their own obligations; the operator sees all; an outsider sees nothing.)*
- **Atomic** — obligations discharge and residual cash moves in one transaction, or neither does. No Herstatt/settlement risk; the failure mode is "nothing happened," never "money is stuck." The underlying primitive is an atomic Delivery-versus-Payment (DvP) engine (tokenized asset leg ⇄ cash leg).
- **Governed by a real agent** — the off-chain agent monitors the ledger, decides with an auditable rationale, and **proposes** — it can never move assets on its own. A human approval (an on-ledger `ApprovedAction`) gates every settlement.
- **Adversarially safe** — the netting contract enforces, on-ledger, that a proposal *conserves value* (residual net per party equals the netted obligations), is *efficient* (residual gross ≤ obligation gross), and is *funded* (an underfunded leg rolls back the whole transaction). A fraudulent under-settlement is rejected by the ledger, not trusted.

> **Why this needs Canton.** Multilateral netting over confidential positions is the load-bearing idea, and it is *only possible* because Canton's sub-transaction privacy lets an authorized operator net positions that the counterparties themselves can't see. Pure deterministic settlement can't deliver safe private netting alone — that's the gap TradeGuard fills.

_Scope note: TradeGuard automates the **settlement and netting layer** of trade finance. It does not replace the legal/credit machinery of a Letter of Credit (discrepancies, amendments, confirmation) — it removes the settlement risk and liquidity drag that sit on top of it._

---

## Phase 2 — the full product (policy → constrained plan → ledger-enforced settle)

The headline above is the core. Phase 2 makes it a product a risk officer can actually operate, with the risk constraints living **on the ledger** rather than in the agent's head:

- **Steer in plain English** — a risk officer types a policy ("cap what FirmA owes FirmC at 20 USD"); an LLM translates it to *validated structured constraints* (real `claude` CLI with a JSON schema, deterministic rules fallback). Garbage degrades to `invalid` — the LLM can never fabricate a plan, and it can't talk past the solver or the on-ledger guards.
- **A real optimizer, not a greedy heuristic** — the agent's plan comes from an LP solver (PuLP/CBC) that minimizes residual flow under the constraints. A binding limit forces a genuine *reroute*; an over-tight one returns the *binding constraint* and the agent **refuses to settle** rather than forcing a bad plan.
- **Credit limits, on the ledger** — a fintech's exposure cap (`CreditLimit`) is a signed on-ledger contract. The **same** limit the solver respects is carried into the settle transaction, so the ledger rejects any plan that breaches it — the operator cannot settle around a firm's own risk constraint.
- **Trustless cross-currency netting** — the FX rate is a **co-signed on-ledger contract** (`FXRate`, signed by *every* relying party). A EUR debt nets against a USD debt only at a rate all parties agreed to — the operator cannot pick it. Settlement then conserves **value** at that rate. *(Live: 4 mixed-currency obligations net by value at 1 EUR = 1.2 USD → 2 USD residuals, all discharged atomically; an FX rate not signed by all parties is rejected by the ledger.)*
- **Liquidity floors, on the ledger** — a neobank's minimum operating balance (`LiquidityFloor`) is enforced on-ledger: a netting plan that would drain a firm below its floor is rejected.

> **The one-line thesis:** *the agent proposes, a human disposes, the ledger settles atomically — or refuses with the binding reason.* Nothing the agent (or the LLM) says can move value past the on-ledger guards.

---

## Phase 3 — live on the real Canton Network + the official Token Standard

Everything above also runs **on the Canton Foundation's shared DevNet** (5N Seaport validator, real OIDC M2M auth, real party allocation, the real Global Synchronizer) — and the settlement layer speaks the **official Canton Network Token Standard (CIP-56)**:

- **CIP-56 token settlement** — TradeGuard's `TGHolding` implements the *real* `Splice.Api.Token.HoldingV1:Holding` interface (built against the official Splice DARs; package-ids match what's deployed on DevNet). Any compliant wallet can read TradeGuard holdings. The netting brain's residuals settle as standard token transfers.
- **Cross-token atomic DvP (the CIP-112 flagship pattern)** — a book with legs in **two different tokens** (USDCx + WrappedAmulet) nets per-instrument and settles **every leg across both tokens in ONE atomic transaction**. One unfundable leg rolls back the whole cross-token batch. *(Live on DevNet: USDCx 280→80 + WrappedAmulet 90→25, 4 legs / 2 tokens, one tx.)*
- **Aggregate exposure limits (Basel large-exposure)** — the case bilateral caps *mathematically cannot catch*: a firm inside every pair-cap can still be over-exposed in total. An on-ledger `AggregateLimit` (firm + operator co-signed) caps a firm's TOTAL residual outflow across ALL counterparties; the solver defers the excess, and the ledger re-checks the same cap at settle. *(Daml test: bilateral caps 80/80 pass, aggregate cap 100 rejects total 120 — atomic rollback.)*
- **Settlement-failure re-net** — when a participant can't fund, the ledger rejects the *whole* batch (atomicity: nothing partial ever hits the book); the agent then excludes the failer's obligations, **re-nets the survivors' book, and settles it** — the failer's obligations stay live for the next cycle. On-ledger funding guard: each allocated holding must exactly fund its leg, right owner, right amount. *(Live on both networks.)*
- **Obligation maturity** — obligations carry an optional maturity; an immature obligation **cannot be discharged** (on-ledger guard in `Discharge`) and the agent's book filter nets only what's due. Tomorrow's cashflow cannot be netted today. *(Live: 3 due obligations settle, the forward obligation stays.)*
- **Netting cycles** — the rail runs in on-ledger sessions (`NettingCycle`: Open → Close → Settle → RollForward), the operating rhythm of a real multilateral system (CLS sessions, ACH windows).

Run it: `source ~/.tradeguard/devnet.env && scripts/devnet_demo.sh` — 8 steps live on DevNet.

---

## What's in the box

| Path | What |
|------|------|
| `tradeguard-v3/main/daml/TradeGuard/Netting.daml` | **Private multilateral netting** — Obligation + NettingBatch w/ on-ledger adversarial guards, `CreditLimit`, co-signed `FXRate` (value conservation), `LiquidityFloor`. |
| `tradeguard/daml/` | Institution-grade Daml model (daml-finance v4 patterns): Holdings, Instruments, atomic batch settlement, attestation gating. |
| `tradeguard-v3/` | Canton 3.x (DPM/SDK 3.4.11) keyless port — the **real-network deploy target** (`tradeguard 1.3.0`). |
| `tradeguard-v3/test/daml/TradeGuard/Test/` | **33 Daml Script tests** — netting, privacy, atomicity, credit-limit reject, aggregate-cap reject, obligation maturity, cross-currency FX settle, unsigned-rate reject, value-violation reject, liquidity-floor reject, CIP-56 token settlement + cross-token DvP. |
| `agent/solver.py` | The optimizer — LP (PuLP/CBC) residual-flow netting under credit limits, FX rates (`solve_fx`), and liquidity floors. **17 tests.** |
| `agent/policy.py` | **NL risk policy → validated constraints** (real `claude` CLI + rules fallback). **10 tests.** |
| `agent/limits.py` | On-ledger lifecycle for `CreditLimit`, co-signed `FXRate`, `LiquidityFloor` — the single-source-of-truth bridge to the solver. |
| `agent/` | The off-chain reasoning agent (Python): `real_client`, `net_settle`, `reasoner`, `netting`, `cli`. |
| `ui/console.html` + `ui/console_server.py` | **Operator Console** — the interactive app you drive the netting workflow from (policy, limits, FX, floors, settle). |
| `scripts/e2e_phase2.sh` | **One-command live end-to-end** — the full product chain on the real network. |
| `scripts/` | `run_stack.sh`, `demo.sh`, `demo_real.sh`, `linear_post.py`. |
| `ARCHITECTURE.md` | Deep architecture + design rationale (authorization model, atomicity, privacy). |
| `deck/index.html` | The pitch deck (netting-first). |

---

## The Operator Console (start here)

The headline experience is an **app you operate**, not a script you run. With the real
network up (`canton builder start` + `scripts/seed_real.py`):

```bash
python3 ui/console_server.py     # -> http://localhost:8090
```

Then drive the whole workflow from the browser, against the live ledger:
**Load a live book** → **Compute net** (the agent's plan: 565 → 100, 82.3% netted) →
**Approve & settle** (human-approval gate → atomic on-ledger settlement; an **on-ledger
receipt** — batch contract id, update id, ledger offset — surfaces right in the console).
Then exercise the Phase 2 surface: type a **Risk Policy** in English and watch the plan go
infeasible with the binding constraint; seed an **on-ledger Credit Limit** and hit **Reject
a credit-limit breach (live)** (the ledger refuses); run **Seed USD+EUR book → Settle cross-currency**
(trustless FX netting at a co-signed rate); seed a **Liquidity Floor**. The privacy
panel shows, live and per-party, that each firm sees only its own obligations while only
the operator sees the whole book.

### One-command end-to-end (the canonical demo)

```bash
scripts/e2e_phase2.sh    # runs the ENTIRE product chain live, in one go:
#  seed → constrained net → NL-policy refusal → credit-limit reject →
#  cross-currency FX settle → liquidity-floor reject. All 6 steps on the real network.
```

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

**Prerequisite for the Daml suite:** `dpm` (the Daml Package Manager) installs to
`~/.dpm/bin/dpm`. Put it on your PATH (`export PATH="$HOME/.dpm/bin:$PATH"`) or invoke it by
full path (`~/.dpm/bin/dpm test`). The DAR must be built first — see `ARCHITECTURE.md` for
the one-time toolchain setup (JDK + Daml SDK). A fresh clone without `dpm` on PATH will get
`command not found`; that's the PATH gap, not a broken test.

```bash
# Daml ledger logic (33 scripts: netting, privacy, atomicity, credit limits, AGGREGATE
# exposure caps, obligation maturity, cross-currency FX at a co-signed rate,
# unsigned-rate reject, liquidity floors, CIP-56 token settlement + cross-token DvP):
cd tradeguard-v3/test && ~/.dpm/bin/dpm test      # or: export PATH="$HOME/.dpm/bin:$PATH" && dpm test

# Python (agent brain), from the repo root, using the project venv:
.venv/bin/python -m agent.test_solver            # 17 solver tests (netting, limits, agg caps, FX, floors)
.venv/bin/python -m agent.test_policy            # 10 policy tests (NL → validated constraints)
.venv/bin/python -m agent.test_netting           # 5 netting tests

# Live integration (on-ledger limits/FX/floors drive the solver as single source of truth):
TG_INTEG=1 TG_REAL=1 .venv/bin/python -m agent.test_limits_integration
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

Built and working **end-to-end on TWO real Canton networks**: the local 3-validator
LocalNet (reset-proof demo spine) and the **Canton Foundation's shared DevNet** (5N
Seaport validator — real OIDC auth, real party allocation, the real Global Synchronizer,
with party-level privacy verified against other live tenants). The full product chain —
NL risk policy → constrained MILP solver → on-ledger credit limits / aggregate exposure
caps / co-signed FX rates / liquidity floors / obligation maturity → human-approved
atomic settle (or ledger refusal with the binding reason) → settlement-failure re-net —
is verified live on both. The settlement layer speaks the official **Canton Network
Token Standard (CIP-56)**, including cross-token atomic DvP. Run
`scripts/e2e_phase2.sh` (LocalNet) or `scripts/devnet_demo.sh` (DevNet, 8 steps).
See `STATUS.md` for the full state and `ARCHITECTURE.md` for the deep dive.

_Apache-2.0. Built for the Build on Canton hackathon, June 2026._
