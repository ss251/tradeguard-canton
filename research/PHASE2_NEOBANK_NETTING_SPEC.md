# TradeGuard → NetWeave — Phase 2 Build Spec (Neobank Netting Rail)

_Status: ACTIVE PLAN. ~2 weeks, solo (+ agent). Written after two Grok first-principles
reviews killed the "intercompany" framing and validated the neobank/fintech framing
("high 2nd-tier / solid 3rd-tier real thesis, not a contrivance")._

---

## 0. The thesis (locked)

**A private multilateral settlement & netting rail for neobanks / fintechs / PSPs /
stablecoin issuers.** Competing payment fintechs owe each other across corridors and
currencies. Today they prefund nostro accounts (capital drag) or route through slow
correspondent banking. They are **competitors** — their flow volumes and counterparty
graph are competitively sensitive (they reveal customer base, corridors, growth).

A neutral Canton rail lets them net the whole book and settle only residuals, atomically,
where **each fintech sees only its own obligations — never a competitor's book, not even
the operator can expose it.** A constrained solver computes the plan under real credit
limits + liquidity buffers + FX; an LLM lets a risk officer steer policy in natural
language; **on-ledger guards reject any plan that breaches a limit.**

Why only Canton: netting needs someone to see across books; a public chain leaks the whole
competitive map; a classic clearer (CLS) needs blind trust. Canton's sub-transaction
privacy + atomic multi-party settlement makes private, enforced, atomic netting possible.

**Wedge (Grok's sharpest):** atomic private settlement + constrained netting of tokenized
bank deposits ⇄ USDC, for **treasury/liquidity rebalancing** (clean provenance — both
parties sign), not customer payments. Rides real Canton proof (HSBC TDS pilot, Visa/Brale
stablecoin settlement, Helios neobank on Canton). Position as "the netting layer CLS
doesn't serve," **not** "replace CLS."

**Honest ceiling (stated, not hidden):** multilateral netting has a bootstrapping /
network-effect problem (convex value; 3-5 parties = shallow nets). That's a go-to-market
risk, not a tech risk — out of scope for the build, acknowledged in the pitch.

**Naming:** working name **NetWeave** (or keep TradeGuard). Decide before public docs.

---

## 1. What we KEEP (≈90% of the existing base — do not rebuild)

- Daml `Obligation` (private to counterparties + operator), `NettingBatch`,
  `SettleNetting` with conservation/efficiency/funding guards.
- Holding / Account / Instrument / SettlementAuthority custody + atomic lock-then-swap.
- Real 3-validator Canton deploy (Builder LocalNet), JSON Ledger API v2 client
  (`agent/real_client.py` with `create_tree`/`exercise_tree`).
- Operator Console shell + per-party privacy panel + live fraud-reject.
- `agent/net_settle.py` (instant v2 settle + live on-ledger fraud rejection).
- 14 Daml tests; the commit/track discipline.

## 2. What CHANGES (the real product delta — nothing faked)

| Area | Change | Real? |
|------|--------|-------|
| Actors | 4 competing fintechs/PSPs + 1 stablecoin issuer (not friendly subs) | scenario |
| Currency | `Obligation` gains `currency` (USD/EUR/GBP); multi-currency book | real |
| FX | on-ledger `FXRate` contracts the operator publishes (fixed for demo, real contract) | real |
| Credit limits | on-ledger `CreditLimit` (per ordered pair, per currency) Daml contracts | real |
| Liquidity floors | on-ledger `LiquidityFloor` (per party, per currency) Daml contracts | real |
| Solver | real constrained optimizer (PuLP/CBC LP) — net subject to limits+floors+FX | real |
| Policy | real LLM: NL risk policy → structured constraint deltas (objectives/priorities) | real |
| Guards | `SettleNetting` extended: reject if any post-settle position breaches an on-ledger CreditLimit/LiquidityFloor | real |
| Console | policy textbox + preset policies; plan view w/ reasoning trace + per-party freed-capital; compliance flags | real |

## 3. Data model (Daml additions)

```
template FXRate
  operator, base:Text, quote:Text, rate:Decimal   -- signatory operator; observer parties
template CreditLimit
  operator, from:Party, to:Party, currency:Text, limit:Decimal  -- max `from` may owe `to`
  -- signatory operator + from (the obligor accepts its own limit); observer to
template LiquidityFloor
  operator, party:Party, currency:Text, floor:Decimal  -- min balance party must retain
  -- signatory operator + party; observer party
-- Obligation gains: currency:Text  (keep instrument for the settlement leg)
-- NettingBatch.SettleNetting gains: reads CreditLimit + LiquidityFloor cids,
--   asserts every party's post-settle net respects them (guard 4 + 5).
```

Cross-currency conservation: conservation guard checks **per currency** (net per party
per currency conserved). FX only matters for the residual settlement leg + liquidity
valuation, not for whether obligations net.

## 4. Solver (the engine — highest priority)

Off-chain, deterministic, real. Input: obligation book + FXRates + CreditLimits +
LiquidityFloors + LLM-derived objective weights. Output: residual transfers that
(a) net the book, (b) respect every credit limit, (c) keep every party above its
liquidity floor, (d) optimize the LLM-set objective (e.g. minimize EUR exposure,
minimize gross FX, prioritize strategic counterparties).

Formulation: LP/MILP via **PuLP** (CBC bundled). Variables = residual transfer amounts
per (payer,payee,currency). Constraints = net-position conservation per party/currency,
≤ credit limit, ≥ liquidity floor post-settle, ≥0. Objective = weighted from policy.
Fallback: if infeasible, return the binding constraint(s) — that's a *feature* (shows
the guard/limit teeth). Keep ≤4 parties / ≤20 obligations / 3 currencies so it solves
instantly and stays demo-legible.

## 5. LLM policy layer (the steering wheel, NOT the engine)

Grok: "LLM is UX polish, not core infra." So: LLM's ONLY job = translate a
natural-language risk policy into a **structured constraint/objective delta** (JSON:
objective weights + soft constraint adjustments), which feeds the deterministic solver.
The solver + on-ledger guards do the real work and cannot be talked past. Use the
available `claude` CLI / API with structured output + a strict schema; validate the JSON;
if the LLM returns garbage, surface it (don't fake). The wow = edit policy in English →
different valid plan, no code change.

## 6. Build plan — dependency-ordered, THIN-SLICE-FIRST

**Guiding rule (the lesson from this project): protect Week 1. Build a thin REAL
end-to-end slice before deepening. If Week 2 slips we still have a real working product.**

### Week 1 — the real vertical slice (everything works, bounded)
1. **D1-2 · Data model + multi-currency.** Add `currency` to Obligation; add `FXRate`,
   `CreditLimit`, `LiquidityFloor` templates; per-currency conservation guard. Build +
   deploy DAR to real net. Seed a 2-currency book. _Milestone: multi-currency netting
   settles atomically on the real network._
2. **D3-4 · Real solver.** `agent/solver.py` (PuLP): net subject to credit limits +
   liquidity floors + FX. Unit tests incl. an infeasible case that returns the binding
   constraint. Wire into `net_settle` so settle uses the solver's residuals.
   _Milestone: a credit-limit-constrained book produces a different (valid) plan than
   naive netting._
3. **D5 · On-ledger limit guards.** Extend `SettleNetting` to read CreditLimit/
   LiquidityFloor and reject breaching plans live (like the fraud guard). Test: a plan
   that breaches a credit limit is rejected on-ledger. _Milestone: the ledger enforces a
   real risk constraint, not just conservation._
4. **D6-7 · LLM policy → solver + basic Console wiring.** `agent/policy.py` (NL →
   structured deltas via `claude`). Console: policy textbox + 2-3 presets → solver →
   plan view. _Milestone: type a policy in English → see a different real plan settle._

→ **End of Week 1: a real, bounded, end-to-end product.** Even if Week 2 fully slips,
this is demoable and honest.

### Week 2 — deepen + harden + pitch
8. Per-party "freed capital" private views; compliance-flag panel; reasoning-trace display.
9. Add the 3rd currency + the stablecoin-issuer actor; tokenized-deposit ⇄ USDC framing
   on the settlement leg.
10. Demo hardening: scripted realistic seed (corridors, near-limit cases); the
    infeasible/guard-rejection beat as a deliberate demo moment.
11. Daily full-flow test on the real network. Tests for multi-currency conservation +
    constraint violations.
12. Reposition all docs/deck/video to the neobank thesis. Re-run Grok gut-check.

## 7. Explicitly OUT OF SCOPE (de-risk — say no on purpose)
- General MIP / arbitrary optimization modeling. Bounded LP only.
- Live FX oracles. Fixed on-ledger FXRate contracts (real contracts, fixed values).
- Autonomous multi-turn agent loops / self-correction. Human approve stays.
- >4 parties / >20 obligations / >3 currencies.
- Real tokenized-deposit/stablecoin integration (we model the settlement leg in our own
  Holding/Instrument; we *frame* it as tokenized-deposit ⇄ USDC, honestly labeled as a
  model). Do NOT claim a real HSBC/Circle integration.
- Solving bootstrapping / network effects (acknowledged as GTM risk in the pitch).

## 8. Top risks
- **Slither into UI polish before the solver works** (our chronic failure). Mitigation:
  Week-1 order above is solver-first; no Console polish until D6.
- **LLM flakiness.** Mitigation: LLM only emits a small validated JSON; solver is
  deterministic; guards are on-ledger. A bad LLM response degrades to "invalid policy,"
  never a broken settlement.
- **Solver infeasibility looking like a bug.** Mitigation: infeasible = a feature that
  surfaces the binding constraint; build that path first-class.
- **Not finishing.** Mitigation: thin slice end of Week 1 is the floor; everything after
  is additive.

## 9. Definition of done (per milestone)
Code pushed + this spec's checklist ticked + a real-network test passing + Linear updated.
No milestone is "done" on the strength of a mock.
