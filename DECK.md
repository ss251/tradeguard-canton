# TradeGuard — Pitch Deck Narrative

The slide-by-slide story for the 3-minute video + presentation deck. Netting is the
headline; atomic DvP is the substrate; the adversarial guard is the credibility beat.

Design language: the "ledger paper + ink" system from the live UI (Newsreader serif +
IBM Plex Mono, single oxblood accent). Each slide = one idea.

---

## Slide 1 — Title / one-liner
**TradeGuard**
*Private multilateral netting + atomic settlement for trade finance, on Canton.*

> "Firms that owe each other money can now net it down and settle the residual —
> without ever showing each other their books. Only possible because privacy is the
> protocol."

(Visual: the 3-firm obligation graph collapsing to 2 arrows.)

---

## Slide 2 — The problem (15s)
- Multi-party trade finance is a web of bilateral obligations.
- Today: settle **gross** (every obligation moves money) or coordinate netting through
  a **trusted central party** that sees everyone's positions.
- Gross settlement = huge liquidity drag. Central netting = a privacy/trust problem.
- And cross-leg settlement carries **Herstatt risk**: you pay, you don't receive.

---

## Slide 3 — The insight (the "only on Canton" claim) (20s)
> **You can only net positions you're allowed to see. Canton lets an authorized
> operator net positions the counterparties themselves can't see each other's.**

- Each obligation is a private contract: visible to its **two counterparties + the
  netting operator** — nobody else.
- No firm sees the whole book. The operator (the agent's principal) does.
- This is sub-transaction privacy doing real algorithmic work — not decoration.

(Visual: the live privacy table — FirmA sees 3, FirmB sees 3, FirmC sees 4, Operator
sees 5, Outsider sees 0.)

---

## Slide 4 — What the agent does (25s)
1. **Monitors** the confidential book it's disclosed to.
2. **Computes** the multilateral net → minimal residual transfers.
3. **Proposes** a NettingBatch with an auditable rationale.
4. **Stops** — a human approves (on-ledger `ApprovedAction`). The agent never moves
   assets on its own.
5. **Settles atomically** — discharges every obligation **and** moves only the
   residual cash in ONE transaction. All-or-nothing.

> Live demo number: **5 obligations / 360 gross → 2 transfers / 70 net. 80.6% never
> moves.**

---

## Slide 5 — The credibility beat: adversarial safety (20s)
A reasoning agent proposing settlements sounds risky. So the **ledger checks the
agent**, not the other way around. NettingBatch enforces on-chain:
- **Conservation** — residual net per party must equal the netted obligations.
- **Efficiency** — residual gross ≤ obligation gross.
- **Funding** — an underfunded leg rolls the whole transaction back.

> Demo: a fraudulent proposal that under-settles is **rejected by the ledger.** The
> agent's "rationale" is never trusted — the contract is.

(Visual: red "REJECTED" stamp on the bad proposal.)

---

## Slide 6 — It's real, not a sandbox (20s)
- Built on **daml-finance v4 patterns**; **14 Daml tests green**.
- Deployed + running on a **real 3-validator Canton network** (Canton Builder LocalNet),
  not a single-node sandbox.
- Full flow verified live over the JSON Ledger API v2: net → propose → human approve →
  atomic settle.
- **Live role-switching UI** — click a party, see exactly what that party can see.

---

## Slide 7 — Why this wins / the ask (15s)
- **Atomic DvP** kills settlement risk. (table stakes on Canton — our substrate.)
- **Private multilateral netting** kills liquidity drag **without** a trusted central
  party — the thing a transparent chain can't do.
- **Governed agent** makes it operable; **on-ledger guards** make it safe.
- Track: **TradeFi, RWA & Tokenized Assets** (maps directly to the "inter-company
  cross-currency netting" theme).

> "TradeGuard is the settlement-and-netting layer institutions actually need —
> private, atomic, agent-operated, and provably safe."

---

## 3-minute video shot list
1. (0:00–0:20) Problem: obligation web + gross settlement / Herstatt.
2. (0:20–0:40) Insight: privacy enables netting. Show the live privacy table.
3. (0:40–1:30) Live terminal: `seed book → agent nets → 360→70 → human approve →
   atomic settle`. Show obligations discharged.
4. (1:30–2:00) Adversarial: run the fraudulent proposal → ledger rejects it.
5. (2:00–2:30) Live UI: switch FirmA / FirmB / Operator / Outsider — privacy is real.
6. (2:30–3:00) "Real 3-validator network, 14 tests, deployed." Close on the one-liner.
