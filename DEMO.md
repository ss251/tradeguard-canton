# TradeGuard — Demo Script (3 minutes)

A tight, judge-facing walkthrough. Everything below is **live**, not slides.

## Setup (before you present)
```bash
source ~/.tg-env.sh
scripts/run_stack.sh        # ledger + JSON API + UI + seeded scenario (~90s)
```
Have two things open: a terminal, and `http://localhost:8080` in a browser.

---

## Act 1 — The problem (15s)
> "B2B trade finance still settles on paper Letters of Credit — days of delay, and
> real settlement risk: you can pay and not receive. We fix that with atomic
> Delivery-versus-Payment on Canton: both legs move together, or neither does.
> But the hard part isn't the swap — it's doing it **privately** and letting an
> **AI agent** help **without handing it the keys**."

## Act 2 — The agent reasons, but doesn't act (45s)
```bash
python3 -m agent.cli status         # a real trade sitting on the ledger, ready
python3 -m agent.cli watch --once   # the agent THINKS out loud
```
> "The agent connects to the live ledger as the settlement coordinator. It checks:
> two legs? funded? a real swap? delivery attested? All pass — so it recommends
> SETTLE. But watch — it does **not** settle. It writes an on-ledger
> recommendation and stops. It has no authority to move a cent."

## Act 3 — The human gate (30s)
```bash
python3 -m agent.cli approve TG-LIVE-001
python3 -m agent.cli settle  TG-LIVE-001
```
> "A human approves — that's an on-ledger ApprovedAction, fully auditable. *Only
> now* can the agent orchestrate settlement: it locks both legs and swaps them in
> one atomic transaction. If anything were wrong, the whole thing rolls back.
> Asset to the buyer, cash to the seller, simultaneously."

## Act 4 — The money shot: privacy, live (45s)
Open `http://localhost:8080`. Click through the role tabs.
> "Same settled trade. Four readers. Each tab hits the **same ledger** with a
> different party's token.
> - **Buyer** sees the bill of lading they now own.
> - **Seller** sees the cash.
> - **Regulator** sees the settlement record — scoped oversight, no position detail.
> - **Outsider** —" *(click Public/Outsider)* "— sees **nothing**. 'No record
>   disclosed. The ledger returned nothing.' That's not the UI hiding it. That's
>   Canton's sub-transaction privacy. The outsider's query literally returns an
>   empty set."

## Act 5 — The depth: netting (30s)
```bash
python3 -m agent.cli net
```
> "And because privacy makes it safe, the agent can do something a public chain
> can't: multilateral netting. Twelve obligations across three firms, \$565k gross —
> nets down to two residual transfers, \$70k. 80% of the value never has to move.
> Those residuals settle atomically as one batch. You can only net positions you're
> allowed to see — privacy is what makes the optimization legal."

## Close (15s)
> "Private. Atomic. Agent-proposed, human-approved, ledger-enforced. And it's all
> running locally right now — 11 Daml tests green, the agent loop live, the privacy
> boundary provable with curl. That's TradeGuard."

---

## One-liner backup (if live fails)
```bash
scripts/demo.sh    # runs Acts 2,3,5 + prints the privacy table from Act 4
```
