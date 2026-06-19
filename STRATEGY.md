# Canton Hackathon — Strategy & Findings

**Synthesized from 4 Grok (Expert mode) research passes. Source files:** `research/q1_tech_stack.md`, `q2_build_ideas.md`, `q3_winning_strategy.md`, `q4_landscape_resources.md`

---

## 1. The Hackathon (facts)

| | |
|---|---|
| **Event** | Build on Canton Hackathon (Encode Club) |
| **Format** | Online, 4 weeks, Intermediate |
| **Started** | 15 June 2026 — "started but you can still apply" |
| **Prize** | **$7,000** to top 3 teams across ALL tracks |
| **Chain** | Canton Network — privacy-enabled L1 for institutional finance (Digital Asset, Daml/DAML stack) |
| **Submit** | Public repo + presentation deck + 3-min video w/ demo + live product link |

**3 Tracks:** (1) Private DeFi & Capital Markets · (2) TradeFi/RWA & Tokenized Assets · (3) **Payments, Neobanking & Agentic Commerce** ← *our track*

**Judging:** Technical execution · Originality/creativity · UX/design · Real-world applicability

---

## 2. The Bet (decision)

> **Build a Privacy-Preserving Autonomous Treasury/Payments Agent** — an AI co-pilot that orchestrates private, atomic B2B settlement on Canton using Daml Finance primitives.

Both independent research passes converged here:
- **Q2 ranking** (feasibility + wow): **PrivyFactor (9)** and **TradeGuard (8.5)** on top.
- **Q4 winning bet**: "Canton AI Treasury Co-Pilot" archetype — directly hits the explicit *"agentic commerce with privacy"* problem statement.

**Why it wins for an AI-agent specialist:**
- Directly matches the track's stated brief (few will go deep on real on-ledger agent actions).
- Differentiates from the crowd who will UI-wrap Daml Finance as a black box.
- Plays our edge (autonomous agents) into Canton's moat (sub-transaction privacy + atomic multi-party settlement).

### Recommended primary: **PrivyFactor** (lead) with Treasury-Agent framing
Private agentic **dynamic invoice factoring / early-payment**: Supplier + Factor AI agents privately negotiate invoice advances; atomic DvP exchange of funds ↔ invoice claim; sensitive commercial terms hidden via Canton stakeholder privacy.
- Wow **5**, Feasibility **4** — highest combined score, painful real SME/SCF market, killer 3-min demo (upload invoice → agent posts private offer → factor accepts → atomic settle, each party sees only their view).

**Backups:** TradeGuard (trade-finance, wow 5 / feas 3.5) · PrivySweep (treasury liquidity sweeps, feas 4.5) · NetOpti (multilateral netting, feas 4).

---

## 3. Tech Stack (from Q1 + Q4)

**Mental model — Daml:** templates (contract types) · choices (actions) · parties · **signatories vs observers** (this IS the privacy model). Authorization/privacy modeling is the #1 time-sink — get signatory/observer/controller right early.

**Privacy:** Canton = need-to-know, sub-transaction privacy. Each participant node sees only the legs relevant to its party. This is native, not bolted-on ZK.

**Atomic settlement:** Global Synchronizer coordinates all-or-nothing multi-party settlement across independent participant nodes (true DvP, no central clearer).

**Day-1 setup (exact):**
```bash
git clone https://github.com/digital-asset/cn-quickstart.git
cd cn-quickstart && direnv allow && cd quickstart
make setup      # interactive: parties, Keycloak/auth, observability
make build
make start      # LocalNet (Splice) + participants + PQS + demo UIs
# separate terminals:
make canton-console
make shell       # Daml Shell
```
- **cn-quickstart** = official scaffolding. LocalNet only (no DevNet post-July 2025). Docker + 8GB+ RAM, JDK 21.
- **Daml Finance** (clone too): `github.com/digital-asset/daml-finance` + study `daml-finance-app`. Gives Instruments / Holdings / Accounts / **Settlement (atomic DvP)** out of the box — don't rebuild token/transfer/settlement primitives.
- **JSON Ledger API** = the practical interface for AI agents (Python/TS). **PQS** (Participant Query Store) projects contracts → PostgreSQL for SQL state reads by the agent.
- `dpm codegen-js / codegen-java` → typed client libs for agent code.

**⚠️ Flagged uncertainty:** exact current Daml Finance package names/versions + one-command integration into latest cn-quickstart is NOT well-documented publicly. Expect to experiment (clone both, study daml-finance-app, add deps to daml.yaml) or ask in workshop/forum.

**Learning curve:** 3–7 days to a productive multi-party "hello world" for an experienced dev. Paradigm shift is the hurdle; after that velocity is high.

---

## 4. How to WIN (from Q3)

**Where teams LOSE points:**
- Not actually running on Canton (mock / single-node / "used SDK but no real participant views").
- **Privacy is cosmetic** — no meaningful signatory/observer distinctions; everyone can query everything; sub-tx views never demonstrated.
- Idea doesn't *require* Canton (could run on Ethereum + access control).
- Scripted/broken/single-party demo.

**What separates top-3:** a working multi-party demo that SHOWS privacy (Party A sees X, Party B sees Y, outsider sees nothing), real atomic settlement, agent reasoning/decision trace, and a crisp institutional narrative — not AI hype.

**"Wow, this is what Canton is for"** = agent autonomously coordinates a private multi-party flow that atomically settles, where each party provably sees only their slice.

**Failure modes that kill agentic projects:** "just an LLM wrapper," no real on-ledger settlement, privacy bolted on, fully off-chain agent that never drives a Daml choice.

**Proof-of-seriousness checklist:** clean documented public repo · deck with clear problem/market · 3-min video showing multi-party private views + atomic settle + agent trace · live LocalNet demo · explicit "why Canton privacy is essential here" slide.

---

## 5. 4-Week Plan (scoped)

- **Week 1** — cn-quickstart LocalNet fully running + Daml Finance wired in (Instrument/Holding/Account/Settlement working across demo participants). Learn tx trees, Daml Shell, PQS. First templates (invoice claim + offer).
- **Week 2** — Core agentic flow with correct privacy model: agent queries private state (PQS) → posts private Offer → counterparty accepts → atomic DvP settlement. Signatory/observer design locked.
- **Week 3** — Agent autonomy + LLM orchestration layer (NL instruction → propose/validate/execute Daml choices), conditional logic, multi-party coordination, simple role-based UI for the video.
- **Week 4** — Polish scenarios + exception handling, record 3-min video, deck, docs, package submission.

---

## 6. White Space (avoid the crowd)

**Crowd will build:** basic tokenized-asset issuance, simple private wallets, generic settlement UIs, shallow "chatbot that doesn't drive on-ledger choices." Most treat Daml Finance as a black box / UI layer.

**Our white space:** real on-ledger agent actions + novel use of sub-transaction privacy in agent *decisions* + automation of a genuine treasury/SCF pain point, built cohesively on cn-quickstart + Daml Finance + a lightweight LLM agent layer.

---

## Next: pipeline
Convert this into Linear issues (epics = weeks/workstreams) mirrored on a Kanban board. See pipeline design doc.
