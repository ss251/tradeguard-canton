# TradeGuard — Project Status

_Last updated: 2026-06-19 18:08 IST_

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
