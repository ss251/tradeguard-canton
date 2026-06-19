# Institutional Finance — Builder's Glossary (for Canton / TradeGuard)

> Purpose: speak TradFi judges' language fluently. Every term is tied to the hackathon
> and to TradeGuard. Bolded terms in the "pitch script" at the bottom are the must-knows.

## Tier 0 — Settlement (everything orbits this)
- **Settlement** — the final, irreversible exchange of value (asset for cash). The moment the whole system exists to make safe.
- **Clearing** — everything between agreeing a trade and settling it (confirm, calc obligations, reserve assets). Prep vs the act.
- **Finality** — once settled it cannot be reversed. Hard in banking; probabilistic on most chains; *legal/instant* on Canton.
- **T+2 / T+1 / T+0** — settlement timing (trade day + N business days). Industry racing to T+0 / atomic. The trade→settle gap is where risk lives.

## Tier 1 — Market structure (who's in the room)
- **Counterparty** — the other side of a trade. "Counterparty risk" = they don't deliver.
- **Custodian** — institution that holds assets on your behalf (e.g., BNY Mellon).
- **Clearing house / CCP** (Central Counterparty) — sits in the middle of every trade, becomes buyer-to-every-seller; absorbs default. DTCC = this for US securities (builds on Canton).
- **OTC** (Over-the-Counter) — privately negotiated, bilateral, off-exchange trade. Inherently a privacy story. Most institutional volume.
- **Primary vs secondary market** — primary = asset issued/created; secondary = existing asset traded between holders.
- Canton thesis: intermediaries exist because there was no shared+private+trustworthy ledger. Canton collapses them into the protocol.

## Tier 2 — Instruments (what moves)
- **Instrument / security** — a tradable financial contract.
- **Equity** — ownership (shares).
- **Bond / fixed income / debt** — a tradable loan; pays principal + **coupon** (interest).
- **Derivative** — value derived from something else: **forwards/futures** (trade later at set price), **options** (right not obligation), **swaps** (exchange cash-flow streams: fixed-for-floating, FX).
- **Repo** (repurchase agreement) — sell now, buy back later higher = collateralized short-term loan. Trillions/day. Broadridge's Canton repo platform = the flagship Canton success. KNOW THIS.
- **RWA** (Real-World Asset) — off-chain asset represented on-chain (treasuries, real estate, invoices, deposits).
- **Tokenized deposit** — a regulated bank deposit as a token (a claim on a bank; not a stablecoin).
- **Stablecoin** — token pegged to a currency (USDC). Likely the "cash leg" in TradeGuard.

## Tier 3 — Workflows (the hackathon themes)
- **Netting** — settle the *net* of mutual obligations, not each gross. Bilateral (2 parties) vs multilateral (many). Cuts volume, fees, liquidity needs. "Gross vs net settlement."
- **Treasury operations** — how a company manages its own cash across entities/currencies.
- **Liquidity** — cash available when/where needed. "Trapped liquidity" = stuck in wrong account/entity/country.
- **Collateral** — assets pledged to secure an obligation. **Collateral mobility** = moving it fast to where needed (a $B inefficiency Canton targets).
- **Invoice factoring / receivables financing** — supplier sells a future invoice (receivable) to a **factor** for cash now at a discount. (= PrivyFactor.) Amounts/terms are secrets.
- **Supply chain finance** — financing the buyer/supplier/logistics payment chain, often milestone-triggered.
- **Letter of Credit (LC)** — the OLD way to make trade safe: a bank guarantees payment on proof of delivery. Slow, paper, costly. TradeGuard = "replace the LC with a private atomic smart contract."
- **Confidential / private lending / private credit** — lending where terms/parties/collateral aren't public. One of the hottest areas in finance.

## Tier 4 — Risk (the language finance thinks in)
- **Counterparty / credit risk** — they default / go bankrupt.
- **Settlement risk** — you delivered your leg, they didn't deliver theirs. **Herstatt risk** (1974 bank failure) = the textbook case. *Atomic DvP eliminates this* — TradeGuard's #1 talking point.
- **Liquidity risk** — can't get cash when needed even if solvent.
- **Operational risk** — the process breaks (manual error, system failure, fraud).
- **Systemic risk** — one failure cascades through the connected system (2008).

## Tier 5 — Why privacy is load-bearing
- **Information leakage** — others learn your positions/intentions and trade against you.
- **Front-running** — someone sees your order coming and jumps ahead. Crypto version = **MEV** (Maximal Extractable Value), bots front-running the public mempool. Cite MEV to show *why* public chains fail institutions.
- **Market impact** — revealing a large trade moves the price against you.
- **Selective disclosure** — reveal exactly what each party + regulator needs, nothing more. = Canton sub-transaction privacy in finance language.

## DvP — the keystone (tie Tier 0 + Tier 5 together)
- **DvP — Delivery vs Payment** — asset leg and cash leg move at the same instant, or neither moves. The gold standard. Eliminates settlement/Herstatt risk. **PvP** = Payment vs Payment (the FX version: two currencies swap atomically). TradeGuard = private atomic DvP.

## THE PITCH SCRIPT (weld these together)
"TradeGuard replaces the **letter of credit** in B2B **trade finance**. Today **settlement risk** — the **Herstatt** problem — forces buyers and sellers to trust slow, expensive intermediaries. We do **atomic DvP**: cash leg and asset leg settle together or not at all, eliminating **counterparty risk** at settlement. And because **prices and counterparties are competitive information**, we use Canton's **selective disclosure** so each party sees only its own legs while a **regulator** gets an **observer** view — impossible on a public chain (**MEV / information leakage**), impossible in **siloed** bank systems (can't settle **atomically** across institutions)."

## THE 5-BEAT LOGIC CHAIN (your whole thesis)
institutions must settle together (shared ledger) -> but cannot leak (privacy) ->
public chains leak (MEV/transparency) -> bank silos can't settle atomically across each other ->
Canton is the only thing that does both.
