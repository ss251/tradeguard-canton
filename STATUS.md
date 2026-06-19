# TradeGuard — Project Status & Strategy

_Last updated: 2026-06-19_

## The pivot decision (validated by Grok, independent of sunk cost)

**Bare propose-accept DvP is too simple** — it's the workshop's worked example; ~10 teams will ship it and get filtered early. BUT multilateral netting (the "impressive" option) is the WORST bet for a solo builder on a new toolchain — over-scoping into it and failing to ship is a top failure mode.

**Chosen direction: C + B**
- **C — daml-finance institutional depth (foundation):** real Holdings / Instruments / Settlement batches / conditional settlement / attestations, instead of hand-rolled templates.
- **B — a real reasoning agent (differentiator):** monitors ledger state, proposes settlements, handles exceptions/scheduling, constructs *real* Daml choices — behind a human approval gate. NOT a chat wrapper.
- **Centerpiece (the "only-on-Canton" claim):** sub-transaction privacy + observer roles inside ONE atomic multi-party transaction. Regulator sees compliance detail; counterparties see only their legs; outsiders see nothing — protocol-enforced. Demo via the role-switch UI we already built.
- **Multilateral netting (N=3):** STRETCH polish only, if everything else is solid.

## The big unblock: LOCAL DEV WORKS

Per Grok: **do not gate the demo on org whitelisting.** Build + test locally with simulated parties.

- Installed: openjdk@17 (brew, no sudo) + Daml SDK 2.10.4 (`~/.daml`)
- PATH: `export PATH=$HOME/.daml/bin:/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin:$PATH`
- Local project: `~/Developer/canton-hackathon/daml-local/tradeguard-local`
- `daml test` → **PASSES**: "ok, 3 active contracts, 5 transactions" — atomic DvP + privacy proof (outsider = None) with NO org access.
- Org deploy is now a "config once whitelisted" bonus, not a blocker.

### Version split (important)
- **Local SDK = Daml 2.10.4** → uses `submitMulti [p1,p2] []`
- **Seaport = Daml 3.4.11** → uses `submit (actAs p1 <> actAs p2)`
- Keep both syntaxes straight when porting.

### Canton privacy gotcha found locally (the kind that eats days if found late)
Buyer couldn't `fetch` the seller's `AssetHolding` inside `Accept` — buyer isn't an observer on it → "contract not visible to reading parties." Fix: added an `AssetHolding_Disclose` choice so the seller discloses the asset to the buyer before Accept. (With daml-finance, disclosure is handled by its settlement model — another reason to adopt it.)

## What's already built
- 6 hi-fi UI screens + index walkthrough (`wireframes/`) — ledger/ink design, vision-verified
- Lo-fi flow wireframes (`wireframes/tradeguard-lofi.html`)
- Daml skeleton builds on Seaport (3.4.11) AND runs locally (2.10.4)
- Research docs: CANTON_BUILD_BIBLE, FINANCE_GLOSSARY, DEFI_TO_TRADFI_JOURNEY, OPERATIONS
- Linear board (team THE, THE-36..44); Encode project (JOIN CODE eae56e81)

## Next moves (in order)
1. ✅ Verify local dev — DONE
2. Pull daml-finance, get its DvP/settlement example building locally
3. Re-base TradeGuard contracts on daml-finance Holdings/Instruments/Settlement
4. Design + build the reasoning agent (the real differentiator)
5. Wire the role-switch UI to read the local ledger (JSON Ledger API) for a live privacy demo
6. (Stretch) N=3 netting
7. Once Jatin whitelists: deploy to org DevNet (small config step)

## Failure modes to avoid (Grok)
- Shipping tutorial DvP + thin agent wrapper → filtered early
- Over-scoping netting → no working demo by deadline
- Talking privacy but not SHOWING it in the demo
- Shallow TradFi modeling (generic tokens vs real daml-finance)
- Agent as gimmick (doesn't drive real ledger actions)
- Death by toolchain (Daml paradigm + Seaport quirks eating days)
