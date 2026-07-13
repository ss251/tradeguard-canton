# TradeGuard — Demo Video Script (2:45)

**Goal:** in under 3 minutes, make a judge understand the wedge, believe it's real, and
remember one sentence. Everything is shown live on the deployed console against Canton DevNet.

**Setup before recording**
- Open the live console: `https://tradeguard-console-production.up.railway.app/?k=tg-9f93a696`
- Start with an EMPTY book (clear it first) so the seed beat lands visually.
- Have a second tab on the deck title slide for the open/close.
- Screen res 1440p, browser zoom 110%, hide bookmarks bar. Record system audio + mic.
- Because DevNet settle takes 30–90s: pre-narrate over the wait, or do ONE clean take with
  a jump-cut on the settle spinner (label it "≈40s on the shared network — real consensus").

---

## [0:00–0:20] — The hook (talking head or deck title slide)

> "Competing fintechs owe each other money across payment corridors every single day.
> Today they either prefund every corridor — locking up capital — or they net through a
> trusted middleman who gets to see everyone's flow. On a public blockchain it's worse:
> netting means exposing every position to the world.
>
> TradeGuard is the settlement rail where **rivals net their book and settle only the
> residual — atomically — without ever exposing their flow to each other.** Live, on
> Canton. Let me show you the real thing."

*(Cut to the console. It's already loaded — banner reads "Canton DevNet · 5N Seaport
validator.")*

---

## [0:20–0:45] — It's real + the privacy wedge

> "This is running against the Canton Foundation's shared DevNet — real validator, real
> auth, not a local sandbox."

**ACTION:** Click **Seed book.** (Narrate over the ~30s DevNet write.)

> "I'm seeding a confidential book — twelve obligations criss-crossing three fintechs,
> FirmA, B, and C. Watch the privacy panel."

**ACTION:** Point at the per-party privacy panel.

> "This is the whole ballgame. The **operator sees all twelve** obligations. But FirmA
> sees only the eight it's party to. So does B, so does C. An outsider sees **zero.**
> Nobody except the operator can reconstruct the book. That's Canton's sub-transaction
> privacy — and it's the only reason safe multilateral netting is possible here."

---

## [0:45–1:15] — The netting brain + human gate

**ACTION:** Click **Compute net.**

> "Now the agent — the only party that can see the whole book — computes the multilateral
> net. Twelve obligations, 565 units of gross exposure, collapse to **two residual
> transfers. Eighty percent of the value never has to move.** That's the liquidity the
> old model locks up in prefunding."

**ACTION:** Point at the proposed plan / rationale.

> "But the agent only **proposes.** It has an auditable rationale, and zero authority to
> move a cent. Settlement needs a human."

**ACTION:** Click **Approve & settle.** (Jump-cut the ~40s spinner; overlay "≈40s — real
DevNet consensus.")

> "A human approves — that's an on-ledger authorization — and now the ledger discharges
> all twelve obligations **and** moves the two residuals in a single, all-or-nothing
> transaction. Either the whole thing settles, or nothing does. No Herstatt risk. The
> failure mode is 'nothing happened,' never 'money is stuck.'"

**ACTION:** Show the book now empty / residual holdings at the firms.

> "Book's discharged. Done, on the real network."

---

## [1:15–1:45] — The ledger polices the agent (adversarial + limits)

> "Here's what makes it trustworthy: the agent can't cheat, because the **ledger checks
> the agent — not the other way around.**"

**ACTION:** Click **Test: adversarial / fraudulent proposal.**

> "I'll submit a deliberately fraudulent settlement — one that under-pays a party. The
> ledger's on-chain conservation guard **rejects it.** Not the agent's code — the ledger."

**ACTION:** Click **Seed aggregate cap (FirmA ≤ 50)** then settle.

> "And real risk controls live on the ledger. This is an **aggregate exposure limit** —
> the Basel large-exposure case that bilateral limits mathematically can't catch: a firm
> can be inside every one-to-one cap and still be dangerously over-exposed in total. Cap
> FirmA's total outflow, and the plan **defers the excess** rather than breach it."

---

## [1:45–2:20] — The Canton Token Standard payoff

> "And this isn't a toy asset. TradeGuard settles the **official Canton Network Token
> Standard** — CIP-56. Our holdings implement the real Splice Holding interface; any
> compliant wallet can read them."

**ACTION:** Switch to the token panel. Click **Seed multi-token book → Settle
cross-token.**

> "Here's the flagship move: a book with legs in **two different tokens** — USDCx and
> WrappedAmulet. TradeGuard nets each token, then settles **every leg across both tokens
> in one atomic transaction.** Cross-token delivery-versus-payment. This is the exact
> pattern the Token Standard was designed for — and we're doing it live."

**ACTION:** Show per-instrument result + balances read back via the standard interface.

> "Verified by reading the balances back through the standard interface. Real tokens, real
> atomic DvP, real network."

---

## [2:20–2:45] — Close (deck close slide or talking head)

> "So: a private netting rail for fintechs that compete. The agent proposes, a human
> disposes, the ledger settles atomically — or refuses with the binding reason. Built on
> the one thing a transparent chain can't do: **net confidential positions without a
> trusted middleman.** Live on Canton DevNet, speaking the official token standard, today.
>
> That's TradeGuard."

*(End card: the live console URL + github.com/ss251/tradeguard-canton + QR code.)*

---

## Beat checklist (for the editor)
1. Hook — the wedge in one breath ✅
2. Privacy panel — operator 12 / firms 8 / outsider 0 ✅
3. Compute net — 565 → 100, 82% never moves ✅
4. Human approve → atomic settle on DevNet ✅
5. Adversarial reject (ledger, not agent) ✅
6. Aggregate cap defers ✅
7. Cross-token CIP-56 atomic DvP ✅
8. One-sentence close + end card ✅

## Fallback if DevNet is too slow to record cleanly
Record the interactive beats against **LocalNet** (`TG_NET=local`, sub-second) for a
smooth take, and include ONE genuine DevNet settle (with the honest "≈40s, real shared
consensus" label) as proof it's on the real network. Best of both: smooth demo + real
receipts.
