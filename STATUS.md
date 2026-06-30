# TradeGuard — Project Status

_Last updated: 2026-06-30 — Phase 2 COMPLETE (policy + console + trustless FX + floors)_

## STATE: COMPLETE & WORKING END-TO-END (local), PUSHED TO GITHUB

Repo: **github.com/ss251/tradeguard-canton** (main). Runs entirely locally with no
hackathon org dependency; Seaport DevNet deploy is a final config step once the
party is whitelisted by Jatin.

## What's built (all working, all tested)

### Ledger (Daml) — `tradeguard/daml/TradeGuard/`
- 8 modules, ~1,150 lines, modeled on daml-finance v4 (verified loadable on SDK 2.10.4)
- Types, Holding (custody + lock/disclose), Instrument, Settlement (atomic N-leg
  batch + SettlementAuthority delegation + SettledTrade audit record), Trade
  (propose/accept/attest), Agent (recommendation + on-ledger human gate), Init,
  Orchestrate
- **11 Daml tests green**: happy path, privacy (outsider=None), atomicity rollback,
  exception/cancel, attestation, reject

### Agent (Python) — `agent/`
- ledger_client (JSON API + per-party JWT, #tradeguard package-name refs)
- reasoner (auditable SETTLE/WAIT/CANCEL decisions)
- netting (multilateral netting; 5 unit tests pass; 80.6% netted in demo)
- cli: status / watch / approve / reject / settle / net
- Full loop verified live: monitor -> reason -> recommend -> HUMAN APPROVE -> atomic settle

### UI — `ui/`
- live.html + ui_server.py: role switch = party-JWT switch; each view is a real
  /v1/query. Buyer/seller/regulator/outsider verified live. Outsider sees nothing.

### Tooling & docs
- scripts/run_stack.sh (full stack up), scripts/demo.sh (full story), make_token.py,
  linear_post.py (comments + screenshot upload — works)
- README.md, ARCHITECTURE.md, DEMO.md (3-min pitch script)

## How to run
```bash
source ~/.tg-env.sh
scripts/run_stack.sh      # ledger 6865 + JSON API 7575 + UI 8080 + seed
scripts/demo.sh           # full governed-agent story + live privacy proof
open http://localhost:8080
```

## Environment
- JDK 17 (brew openjdk@17) + Daml SDK 2.10.4 (~/.daml); PATH in ~/.tg-env.sh
- daml-finance v4 bundle vendored in vendor/
- Local SDK = 2.x (submitMulti); Seaport = 3.4.11 (submit actAs) — port syntax when deploying

## Linear (team THE)
- THE-36 Checkpoint 1 (Encode) DONE · THE-37 wallet DONE · THE-38 live stack DONE
- THE-40 skeleton DONE · THE-41 atomic DvP DONE · THE-42 UI (live, screenshots) ·
  THE-43 agent + netting DONE · THE-44 submission (pushed)
- All milestones tracked with screenshots uploaded via scripts/linear_post.py

## Remaining (optional / external)
- Deploy DAR to Seaport DevNet org (needs Jatin to whitelist the Party ID) — config step
- Optional: record a screen-capture of the demo for the submission
- Optional: wire netting end-to-end on-ledger (algorithm + engine both exist; demo
  currently shows the optimization, residuals reuse the proven SettlementBatch)

## UPDATE 2026-06-19 ~19:30 — DEPLOYED TO REAL CANTON NETWORK ✅
- tradeguard-v3/ = keyless Daml 3.x port (DPM/SDK 3.4.11, LF 2.1). ALL 11 tests pass.
- Deployed to a REAL 3-validator Canton network (Canton Builder Tool LocalNet):
  - DAR uploaded to App Provider (3975) + App User (2975) — HTTP 200, package loaded=True
  - Network queryable with HS256 token (secret "unsafe"); 6 system parties present
- Refactor: dropped contract keys from 5 templates (Canton 3.4 LocalNet only allows LF 2.1/2.2
  which forbid keys); SettlementAuthority passed by ContractId (authorityCid on AllocatedLeg);
  PartyDetails.displayName removed in 3.x -> match parties by id-prefix via DA.Text.splitOn.
- REMAINING to run full agent loop on the REAL network: seed scenario via auth-enabled Daml
  Script (needs JWT to the gRPC ledger 3901) + point agent/ui at ports 3975/2975. The 2.x
  sandbox stack (scripts/run_stack.sh) remains the fully-working demo path.

## UPDATE 2026-06-19 ~19:25 — AGENT LOOP RUNS ON REAL NETWORK ✅
- agent/real_client.py: JSON API v2 client (HS256 admin token, WildcardFilter ACS,
  /v2/commands/submit-and-wait). Enable with TG_REAL=1.
- scripts/seed_real.py: allocate 7 parties + grant CanActAs via admin API.
- Seeded real net via auth'd Daml Script (dpm script --ledger-port 3901 --access-token-file).
- VERIFIED on live 3-validator LocalNet (:3975):
  * status reads coordinator view; watch reasons + writes SettlementRecommendation on-ledger;
    approve creates ApprovedAction on-ledger.
  * PRIVACY: buyer/seller see legs; regulator sees accepted trades but 0 holdings;
    OUTSIDER sees nothing (0/0/0).
- RUN real net: TG_REAL=1 python3 -m agent.cli status|watch --once|approve TG-LIVE-001
- Remaining: settle orchestration on real net (auth'd Daml Script, same pattern as seed).

## UPDATE 2026-06-29 ~16:30 — PHASE 2 LIVE: MULTI-CURRENCY + ON-LEDGER CREDIT LIMITS ✅
Pivot thesis (competing fintechs/neobanks) now backed by REAL code on the REAL network.
- **Daml (tradeguard 1.2.0, deployed to :3975 + :2975, HTTP 200):**
  - `NetTransfer` gained `currency` (Optional, for Canton SCU upgrade-compat); conservation
    + efficiency guards now checked INDEPENDENTLY PER CURRENCY (USD residual never offsets EUR).
  - New `CreditLimit` template (signatory from+operator, observer to) = a fintech's own
    on-ledger exposure cap. `NettingBatch.creditLimits` (Optional, LAST field for SCU);
    `SettleNetting` rejects any plan that breaches a cap — the operator can't settle around it.
  - 16 Daml tests green (added testMultiCurrencyNetting, testNettingRejectsCreditLimitBreach).
  - SCU gotchas hit + fixed: new fields must be Optional AND appended at the record end.
- **Solver (agent/solver.py, PuLP/CBC, 6 tests):** real LP per currency; unconstrained
  reproduces 360->70 (80.6%); a binding limit forces a genuine REROUTE; INFEASIBLE returns
  the binding constraint ("C owed 40 but capped at 20"); objective_weights = LLM policy hook.
- **VERIFIED LIVE on the 3-validator network:**
  - settle: 5 obligations (360) -> 2 residuals (70), atomic;
  - LIVE credit-limit reject: FirmA->FirmC capped 20 USD rejects the 40-owed plan
    ("credit limit breached: FirmA -> FirmC in USD");
  - LIVE per-currency conservation reject ("conserve value ... in USD").
- Commits: c5be431 (ledger) · 5c06ced (solver) · 703921c (live deploy). Deck reframed live
  to the neobank thesis (9694e80). NOT YET DONE: LLM policy layer (agent/policy.py), console
  wiring for the credit-limit beat, FX rates (all roadmap, clearly labeled).

## UPDATE 2026-06-30 — PHASE 2 COMPLETE: POLICY + CONSOLE + TRUSTLESS FX + FLOORS ✅

Everything labeled "roadmap" on 2026-06-29 is now SHIPPED, tested at every layer, and
verified live on the real 3-validator network. The product thesis is fully realized:
**a risk officer steers netting in plain English; an off-chain agent plans under the
exact constraints the ledger enforces; a human approves; the ledger settles atomically
or refuses with the binding reason.** Nothing the agent says can talk past the on-ledger
guards.

### M1 — LLM policy layer (`agent/policy.py`)
- Natural-language risk policy -> validated structured constraints. Two backends, one
  contract: real `claude` CLI (`--json-schema`, verified live) + deterministic rules
  fallback. Garbage degrades to `invalid` — never a fabricated plan.
- `objective_weights` + policy-declared limits feed straight into the solver.
- **10 policy tests green** (9 offline + 1 live LLM).

### M2 — credit-limit lifecycle (`agent/limits.py`)
- seed/load/clear on-ledger `CreditLimit`s + the bridge that feeds the SAME on-ledger
  limits into the solver AND `NettingBatch.creditLimits` — single source of truth, no
  parallel definition that can drift.
- Live integration test: seed a 20-USD cap -> solver plans under it -> binding constraint.

### M3 — console wired end-to-end (`ui/console_server.py`, `ui/console.html`)
- `/compute` + `/settle` use the constrained solver under live on-ledger limits + optional
  policy. New endpoints: `/policy`, `/limits`, `/limits/clear`, `/credit-breach`.
- `settle_real()` REFUSES to settle when infeasible — returns the binding constraint,
  book untouched (verified). Risk Policy input + Credit Limits panel in the UI.

### M4 — trustless cross-currency FX + liquidity floors (`tradeguard 1.3.0`)
Built the HARD, correct version, not valuation-only. **The FX rate is a co-signed
on-ledger contract** (signatory = operator + EVERY relying party), so a EUR debt nets
against a USD debt only at a rate all parties agreed to — the operator cannot pick it.
This is what makes cross-currency netting sound instead of a trusted-operator backdoor.
- **Daml (1.3.0, deployed :3975 + :2975, HTTP 200):**
  - `FXRate` (co-signed); when present, `SettleNetting` switches to VALUE-based
    conservation across currencies at the agreed rates, and REFUSES any rate not signed
    by all parties, or any currency with no agreed path to the valuation currency.
  - `LiquidityFloor` + `BalanceFact`: post-settle balance (pre + net residual) must stay
    >= floor, enforced on-ledger.
  - 4 new `NettingBatch` fields (Optional, appended for SCU compat): `fxRates`,
    `liquidityFloors`, `balanceFacts`, `valuationCurrency`. `fxFactor` handles direct+inverse.
  - **20 Daml tests green** (added cross-currency settle, value-violation reject,
    unsigned-rate reject, liquidity-floor reject).
- **Solver (`agent/solver.py`):** `solve_fx()` values each party's multi-currency net
  into a settlement currency at the agreed rates, solves the residual LP under credit
  limits AND liquidity floors; `solve_constrained()` dispatches FX vs per-currency.
  **11 solver tests green** (added 5 FX/floor tests).
- **Console:** "Cross-currency (FX)" + "On-ledger Liquidity Floors" cards; endpoints
  `/seed-fx`, `/settle-fx`, `/floors`, `/clear-all`. Vision-verified in-browser.
- **VERIFIED LIVE:** 4 mixed-currency obligations (A->B 100 USD, B->A 50 EUR, A->C 60 EUR,
  C->B 40 USD; 250 mixed gross) netted by value at 1 EUR=1.2 USD -> 2 USD residuals
  (112 USD total), all 4 discharged atomically; value conserved per party (A -112, B +80,
  C +32, Σ=0). Unsigned-rate + floor-breach both rejected by the ledger.

### Test totals (all green)
- 20 Daml tests (`dpm test`) · 11 solver tests · 10 policy tests · 5 netting tests
  · 3 live integration tests (limits + FX + floors drive the solver as single source of truth).

### End-to-end demo
- `scripts/e2e_phase2.sh` — one script that exercises the full chain on the live network:
  seed -> policy -> credit-limit reject -> cross-currency FX settle -> liquidity-floor reject.

### Commits (this phase)
- M1 `4266ab8` · M2 `4378a63` · M3 `3015b86` · M4 Daml/solver `09c2dc8` · M4 live FX
  `0db3a00` · M4 integration tests `9a2bb08` · M4 console `30a590c`.

### How to run the live console
```bash
cd ~/Developer/canton-hackathon
.venv/bin/python ui/console_server.py    # http://localhost:8090
# (requires the real 3-validator LocalNet up on :3975/:2975; venv has PuLP)
```

### Toolchain note
- Phase 2 agent code uses the project venv `.venv/bin/python` (Python 3.13 + PuLP);
  bare `python3` drifts. Daml 1.3.0 built with DPM 3.4.11.
