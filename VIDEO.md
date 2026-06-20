# TradeGuard — 3-Minute Video (recording guide)

Turnkey one-take recording. **Two windows:** (1) this terminal running
`scripts/demo_video.sh`, (2) the deck `deck/index.html` + the live UI
`http://localhost:8080`. Narrate over the script's pauses.

## Before you hit record
```bash
scripts/preflight_video.sh        # must print READY
# if not READY: canton builder start → deploy 1.1.0 → python3 scripts/seed_real.py
```
Set the pace: `PACE=5 scripts/demo_video.sh` (5s pauses give you room to talk).

## The 5 beats (≈3:00) — script auto-runs each; you narrate

| Time | On screen | Say (paraphrase) |
|------|-----------|------------------|
| **0:00–0:20** | Deck slide 1 → 2 | "Multi-party trade finance is a web of obligations. Today you either settle gross — huge liquidity drag — or net through a trusted central party that sees everyone's books. And you carry Herstatt risk: you pay, you don't receive." |
| **0:20–0:50** | `demo_video.sh` ACT 1 + ACT 2 | "TradeGuard makes each obligation private to its two counterparties and one netting operator. Watch the same ledger queried as each party — FirmA, FirmB, FirmC each see only their own slice; the operator sees the whole book; an outsider sees nothing. **You can only net what you can see — and only Canton lets an operator net positions the counterparties can't see each other's.**" |
| **0:50–1:40** | ACT 3 | "The agent computes the multilateral net and proposes the minimal residual settlement. A human approves on-ledger — the agent never moves assets alone. Then one atomic transaction discharges all five obligations and moves only the residual cash. **360 gross becomes 70 — over 80% never moves.**" |
| **1:40–2:20** | ACT 4 | "Why trust an AI agent? You don't. The netting contract enforces conservation, efficiency and funding on-ledger. Here's a fraudulent proposal that under-settles — **the ledger rejects it.** The agent's rationale is never trusted; the contract is." |
| **2:20–3:00** | Live UI (switch role tabs) → deck slide 7 | "This runs on a real three-validator Canton network — 14 tests, the JSON Ledger API v2, a live role-switching UI. Click any party, see exactly what they can see. TradeGuard is the settlement-and-netting layer institutions actually need: private, atomic, agent-operated, provably safe." |

## Tips
- Record terminal at a large font (the script prints big oxblood banners per act).
- For the UI beat: in the browser, click the Buyer/Operator/Outsider tabs so the
  privacy boundary is visible on camera (the outsider "No record disclosed" void is the
  money shot).
- If a beat runs long, the script pauses are driven by `PACE` — lower it for a tighter cut.
- Total runtime of the script ≈ (4 acts × a few pauses × PACE) + the real ledger calls
  (~10–15s each). At PACE=5 it lands close to 3 min with narration.
