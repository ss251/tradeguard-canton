# TradeGuard — Project Status

_Last updated: 2026-07-04 — LIVE on Canton DevNet + public Operator Console deployed._

## STATE: COMPLETE, DEPLOYED, PUBLICLY DEMOABLE

- **Repo:** github.com/ss251/tradeguard-canton (main)
- **Live Operator Console:** https://tradeguard-console-production.up.railway.app/?k=tg-9f93a696
  (runs against the **real Canton Foundation DevNet** — 5N Seaport validator, real OIDC auth)
- **Deck (GitHub Pages):** https://ss251.github.io/tradeguard-canton/
- **Runs on TWO real Canton networks:** local 3-validator LocalNet (fast, reset-proof
  demo spine) and the shared **DevNet** (the "it's really on the network" proof).

---

## The one-line thesis

**The only settlement rail where competing fintechs net their book and settle only the
residual — atomically, without ever exposing their flow to each other — live on the real
Canton network, speaking the official Canton Token Standard.**

A governed AI agent is the only party that sees the whole book. It computes the
multilateral net, proposes the minimal residual settlement, waits for human approval,
then discharges every obligation **and** moves only the residual cash in one all-or-nothing
transaction. Nothing the agent (or its LLM policy layer) says can move value past the
on-ledger guards.

---

## What's built (all working, all tested, all live)

### Core — private multilateral netting + atomic settlement
- Each obligation is visible only to its two counterparties + the operator. **No firm sees
  the whole book** (genuine Canton sub-transaction privacy — verified live: operator sees
  all 12, each firm sees only its own 8, an outsider sees 0).
- Netting brain (LP/MILP solver, PuLP/CBC) computes the minimal residual flow; residuals
  discharge + settle atomically or not at all. 360 gross → 70 residual (80.6% never moves).
- On-ledger adversarial guards: value conservation, efficiency, funding — a fraudulent
  under-settlement is **rejected by the ledger**, not trusted.

### Governed by a real agent + natural-language risk policy
- Off-chain agent monitors, decides with an auditable rationale, and **proposes** — it can
  never move assets alone. A human approval (`ApprovedAction`) gates every settlement.
- Risk officer steers in plain English → LLM (`claude` CLI + deterministic rules fallback)
  → validated structured constraints. Garbage degrades to `invalid`; the LLM can never
  fabricate a plan or talk past the solver / on-ledger guards.

### On-ledger risk constraints (single source of truth: the ledger)
- **Credit limits** — a fintech's bilateral exposure cap, signed on-ledger; the same limit
  the solver respects is carried into the settle tx, so the ledger rejects any breach.
- **Aggregate exposure limits** (Basel large-exposure) — the case bilateral caps
  *mathematically cannot catch*: a firm inside every pair-cap can still be over-exposed in
  total. `AggregateLimit` caps a firm's TOTAL residual outflow across ALL counterparties.
- **Trustless cross-currency netting** — the FX rate is a **co-signed** on-ledger contract
  (every relying party signs); a EUR debt nets against a USD debt only at a rate all
  parties agreed to. The operator cannot pick it.
- **Liquidity floors** — a plan that would drain a firm below its minimum operating
  balance is rejected on-ledger.
- **Obligation maturity** — an immature obligation cannot be discharged (on-ledger
  `getTime` guard); the agent nets only what's due. Tomorrow's cashflow can't be netted today.

### Resilience
- **Settlement-failure re-net** — when a participant can't fund, the ledger rejects the
  WHOLE batch (atomicity: nothing partial ever hits the book); the agent excludes the
  failer, re-nets the survivors' book, and settles it. The failer's obligations stay live.

### Canton Network Token Standard (CIP-56)
- `TGHolding` implements the **real** `Splice.Api.Token.HoldingV1:Holding` interface
  (built against official Splice 0.6.10 DARs; package-ids match what's deployed on DevNet —
  any compliant wallet can read TradeGuard holdings).
- **Cross-token atomic DvP** (the CIP-112 flagship pattern): a book with legs in TWO
  tokens (USDCx + WrappedAmulet) nets per-instrument and settles every leg across both
  tokens in ONE atomic transaction. Live on DevNet: USDCx 280→80 + WrappedAmulet 90→25.
- **Netting cycles** (`NettingCycle`: Open → Close → Settle → RollForward) — the operating
  rhythm of a real multilateral system (CLS sessions, ACH windows).

---

## Test totals (all green)
- **33 Daml Script tests** (`cd tradeguard-v3/test && dpm test`) — netting, privacy,
  atomicity, credit limits, aggregate caps, maturity, cross-currency FX at a co-signed
  rate, unsigned-rate reject, value-violation reject, liquidity floors, CIP-56 token
  settlement + cross-token atomic DvP.
- **17 solver tests** · **10 policy tests** · **5 netting tests**
- Live integration tests (on-ledger limits/FX/floors/agg-caps drive the solver as the
  single source of truth).

---

## Current package / deploy state
- **`tradeguard 1.7.1`** — deployed to LocalNet (:3975 + :2975) AND DevNet (HTTP 200).
- Canton smart-upgrade lineage maintained (Optional last-fields; modules persist across
  versions). Official token-standard DARs vendored in `vendor/token-standard/`.
- Operator Console deployed on Railway (Eric's team), DevNet-backed, password-gated.

---

## How to run

**Public (no setup):** open the live console URL above.

**Local (fast demo spine):**
```bash
cd ~/Developer/canton-hackathon
# requires the 3-validator LocalNet up on :3975/:2975; venv has PuLP
TG_NET=local .venv/bin/python ui/console_server.py      # http://localhost:8090
```

**One-command live end-to-end:**
```bash
scripts/e2e_phase2.sh                                    # LocalNet, full chain
source ~/.tradeguard/devnet.env && scripts/devnet_demo.sh # DevNet, 8 steps
```

---

## Linear (team THE)
- Epic **THE-45** (CIP-56 rebuild) + sub-issues THE-46…52 **DONE**.
- THE-53 aggregate limits · THE-54 settlement-failure re-net · THE-55 obligation maturity
  — all **DONE**.

---

## Remaining for submission (docs/story, NOT code)
- [ ] Demo video (script drafted: `DEMO_SCRIPT.md`)
- [ ] Submission writeup on the hackathon platform (confirm platform + deadline)
- [ ] Optional: clear the DevNet demo book / add a fast LocalNet-backed second instance
