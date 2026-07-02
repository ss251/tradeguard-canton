# TradeGuard × CIP-56 Token Standard — Settlement-Layer Rebuild Spec

**Status:** active build · **Author:** agent · **Date:** 2026-07-01
**Networks:** LocalNet (`TG_NET=local`, reset-proof demo spine) + DevNet (`TG_NET=devnet`, 5N Seaport validator, real shared Global Synchronizer)

---

## 0. Why this rebuild

TradeGuard's netting **brain** (constrained solver → maximal-feasible netting → on-ledger
credit limits / co-signed FX / netting cycles) is real IP and stays **untouched**. What
made it puncturable was the **settlement layer**: a home-grown `TradeGuard.Holding` /
`SettleTransfer`. A Canton Foundation judge's fatal question is *"the Token Standard
(CIP-56) already defines allocation-based multilateral DvP — why did you reinvent it?"*

Verified on the DevNet validator (`5nsandbox-devnet-2`):
- Splice + **CIP-56 token standard fully deployed** (`Holding`, `TransferInstruction`,
  `Allocation`, `TransferFactory`, `AllocationFactory` interfaces all resolve).
- Real standardized assets held by a party we control: **USDCx (91 holdings),
  WrappedAmulet (42), Amulet/CC (2)**; ~21.5M CC on the validator party.
- **7 live `Allocation` + 34 live `AllocationRequest`** contracts — the DvP lifecycle is
  actively running here. `AllocationRequest` = `Splice.Testing.Apps.TradingApp:OTCTrade`
  with `transferLegs = {sender, receiver, amount, instrumentId}` — **structurally
  identical to TradeGuard's `NetTransfer`.**
- **Our validator party is the `admin` (registry) for USDCx & WrappedAmulet.**

Key architectural consequence: **TradeGuard is built as a CIP-56-compliant registry +
settlement app.** Because our party is the registry admin of its own instrument, the
Allocation/TransferInstruction flow executes **fully on-ledger** — no dependency on the
off-ledger registry HTTP API (which is 404 on our granted host). Any CIP-56 wallet could
read TradeGuard-registered holdings; settlement runs standard allocation-based DvP.

CIP-112 (Token Standard V2, approved 2026-06) uses **exactly multilateral netting** as its
flagship worked example (Alice/Bob/Carol cross-instrument legs → allocations →
`SettlementFactory_SettleBatch`). TradeGuard independently arrived at the same shape. This
rebuild makes that alignment literal.

---

## 1. Target architecture

```
        ┌─────────────────────────  UNCHANGED BRAIN  ─────────────────────────┐
 book → │ solver (maximal-feasible netting) → on-ledger CreditLimit / FXRate / │
        │ LiquidityFloor guards → NettingCycle lifecycle                       │
        └──────────────────────────────┬──────────────────────────────────────┘
                                        │ emits residual legs {sender,receiver,amount,instrumentId}
                          ┌─────────────▼──────────────┐
                          │   NEW SETTLEMENT LAYER      │
                          │  TradeGuard.TokenSettlement │
                          │  (CIP-56 registry + app)    │
                          └─────────────┬──────────────┘
                    ┌───────────────────┴────────────────────┐
              MINIMAL (M1)                              MAXIMAL (M2)
        single-instrument (USDCx)                cross-token atomic DvP batch
        real CIP-56 transfer of the              net legs across USDCx + WrappedAmulet,
        netted residual                          settle all in ONE atomic batch
                                                 (the CIP-112 flagship pattern)
```

**Design invariant:** the brain outputs a currency/instrument-tagged residual set. The
settlement layer only changes *how those residuals move value*. Solver, limits, FX,
cycles, console, and all their tests remain green throughout.

---

## 2. MINIMAL milestone (M1) — single-instrument, real token-standard transfer

**Goal:** net a book denominated in a single CIP-56 instrument (USDCx) and settle the
residual by a **real Token-Standard transfer** (not the home-grown Holding).

### Daml (`TradeGuard.TokenSettlement`)
- `RegisteredInstrument` — TradeGuard as CIP-56 registry admin for a `TGToken` instrument
  (id, admin=operator/registry). Implements the **`Holding` interface** (view =
  `{owner, instrumentId, amount, lock, meta}`).
- `TGHolding` template implementing `Splice.Api.Token.HoldingV1:Holding` — so any
  compliant wallet can read TradeGuard holdings via the standard interface.
- `TransferLeg` data = `{sender, receiver, amount, instrumentId}` (the standard shape),
  replacing the ad-hoc `NetTransfer` at the settlement boundary.
- `NettingSettlement` template that takes the netted residual legs and executes them
  atomically as standard transfers, requiring stakeholder authorization per leg.
- Preserve the adversarial guards (value conservation, efficiency) at this layer.

### Python / agent
- `agent/token_settle.py` — the CIP-56 settlement backend: build `TGHolding`s, run the
  brain, emit residual `TransferLeg`s, execute the settlement, verify on-chain.
- `net_settle.settle_real(..., backend="token")` switch (keep `backend="holding"` working
  so LocalNet demo + all existing tests stay green).

### Verification (both networks)
- `TGHolding`s are visible via the **standard Holding interface** (InterfaceFilter query
  returns TradeGuard holdings with the correct `{owner, instrumentId, amount}` view).
- Net 5 single-instrument obligations → residual settled as real token-standard
  transfers; post-settle ACS shows conservation.
- Daml script tests + a live DevNet integration test.

### Acceptance
- [ ] `TGHolding` implements CIP-56 `Holding`; interface query returns correct view.
- [ ] Single-instrument netting settles via standard transfer, atomic, conserving.
- [ ] Green on LocalNet **and** DevNet; existing 24 Daml + solver/policy/netting tests
      still pass (brain untouched).

---

## 3. MAXIMAL milestone (M2) — cross-token atomic multilateral DvP

**Goal:** the CIP-112 flagship. Net a book with legs across **two instruments**
(USDCx + WrappedAmulet), and settle the entire residual set as **one atomic
allocation-based batch** — value conserved per instrument, all-or-nothing across both.

### Daml
- `Allocation`-style reservation: each party locks the holdings it owes into an
  allocation bound to a `settlementRef` (mirrors `Splice.Api.Token.AllocationV1`).
- `SettlementBatch` executor choice that consumes all matched allocations and executes
  every leg in a single transaction (the `SettlementFactory_SettleBatch` analogue).
  Atomicity across instruments enforced on-ledger: either all legs settle or none.
- Cross-instrument conservation guard: per `instrumentId`, Σ residual net = 0.

### Solver / brain
- Extend the residual emitter to tag legs by `instrumentId` and produce a multi-instrument
  allocation plan. The maximal-feasible + credit-limit + FX logic is reused as-is; FX only
  informs cross-instrument *valuation* for limits, **not** cross-instrument netting-at-rate
  (per the co-signed-rate integrity rule already established).

### Verification
- Book with USDCx legs AND WrappedAmulet legs → single atomic batch settles both;
  per-instrument conservation holds; partial failure rolls the whole batch back.
- Live on DevNet with the real USDCx + WrappedAmulet holdings.

### Acceptance
- [ ] Two-instrument book settles in ONE atomic allocation batch.
- [ ] Per-instrument conservation enforced on-ledger; all-or-nothing across instruments.
- [ ] Live green on DevNet with real standardized assets.
- [ ] Console shows the cross-token settlement.

---

## 4. Constraints & non-negotiables
- **Brain untouched.** Solver / limits / FX / cycles and their tests stay green.
- **Both backends coexist.** `holding` (LocalNet demo spine) + `token` (CIP-56).
- **No fabricated results.** Every "settled" claim backed by a real ACS read-back.
- **Secrets** stay in `~/.tradeguard/devnet.env` (chmod 600, never committed).
- **DevNet is shared + slow** (~30s/settle); LocalNet remains the live-demo surface.
- Commit + push + Linear at every sub-milestone.

## 5. Risk register
| Risk | Mitigation |
|---|---|
| CIP-56 `Holding` is an *interface*; implementing it needs the exact `splice-api-token-holding-v1` package as a dependency | Add it as a data-dependency from the DevNet packages / Splice release DARs; if unavailable locally, mirror the interface's view type and implement against the on-DevNet package id |
| Registry HTTP API 404 on our host | TradeGuard **is** its own registry admin → allocation/transfer executes on-ledger via our own choices; no external API needed |
| Amulet 10-min prepare/submit window | We settle TradeGuard-registered instruments (USDCx/WrappedAmulet/TGToken) we admin, not native Amulet directly — no external window dependency |
| DevNet reset wipes deployment | `devnet_setup.py` idempotent; re-run before final evidence; LocalNet is the reset-proof spine |
