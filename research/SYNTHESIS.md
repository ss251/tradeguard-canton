# Canton Hackathon — Research Synthesis & Strategic Decision

**Event:** Build on Canton Hackathon (Encode Club) · Online · 4 weeks · started 15 June 2026
**Prize:** $7,000 pool, top-3 across tracks — **⚠️ FAQ contradicts itself** ("five challenge prizes worth $X,000 each" vs "$7,000 split"). MUST verify in Encode Discord before locking strategy.
**Submit:** public repo · deck · 3-min video w/ demo · live product link (all via Encode platform)

---

## THE DECISION (changed after reading FAQ)

### Pivot: lead with the institutional workflow, NOT the AI agent.

The judging panel is **TradFi engineers, capital-markets / settlement / treasury / collateral builders, institutional DeFi teams.** They explicitly want *"genuine institutional problems, not generic Web3 demos"* and warn against *"demos with an AI wrapper."*

My original framing ("autonomous AI agents as the hero") is a **strategic mistake with this panel.** TradFi judges are viscerally skeptical of agents touching money. Validated by Grok (Q5).

**Reposition:** Canton privacy + institutional workflow = the hero. The AI/agent layer = a **governed, off-chain automation layer** (data ingestion, opportunity detection, proposal generation, monitoring, exception flagging) that *proposes* — never unilaterally executes — Canton transactions under explicit permissions / human gates. Canton stays the source of truth for state, privacy, atomicity, finality. This is explicitly allowed ("supporting infra can be off-chain").

### Project: **NetOpti** — Private Multilateral Payment Netting & Optimization

Primary pick. Runner-up: **TradeGuard** (B2B trade settlement / private atomic DvP).

**Why NetOpti wins with THIS panel:**
- Textbook institutional pain settlement/treasury teams actually solve (liquidity optimization, reduced gross settlement volume, Herstatt risk reduction).
- It's an explicitly named hackathon theme ("inter-company cross-currency netting").
- True multilateral netting *requires* Canton's native privacy: parties submit detailed obligations, but bilateral exposures stay visible only to relevant counterparties / the netting operator; nets compute and settle atomically without broadcasting full flows. This is **functional privacy enabling a real regulated workflow** — not cosmetic "private tx."
- Canton is obviously central (private multi-party state sync + atomic net settlement). AI slots in cleanly as off-chain intelligence surfacing netting opportunities + preparing governed submissions.

**Why not the others:**
- **PrivyFactor** (invoice factoring): strong, but leans RWA/credit, less "core settlement/treasury optimization."
- **PrivySweep** (treasury sweeps): highest feasibility but lower wow ("known" problem).
- **TradeGuard**: excellent runner-up; slightly less differentiated on the multilateral-coordination axis netting provides. Keep as fallback if Daml netting modeling proves too hard.

---

## EXECUTION IS THE REAL BATTLE (idea < execution)

Most technically-decent projects STILL fail top-3 because of **shallow domain fluency exposed in Q&A** and **cosmetic/unproven privacy**. The make-or-break:

### The demo MUST show (non-negotiable):
1. **Realistic multi-party workflow w/ plausible data + ≥1 exception/dispute path.** Simulate 3–4 distinct institutional roles (banks / corporate treasuries) submitting real-ish obligations → privacy-preserving computation → atomic settlement on Canton → confirmation + reporting. No toy numbers.
2. **Explicit VISUAL proof of restricted transaction visibility.** Role-based UI views: each participant sees only what they're permissioned for (own details + computed nets; others' bilateral details masked/absent). Show an outsider view returning redacted/denied. Include a selective-disclosure path (regulator/auditor gets approved view). Narrate that this is **native to Canton's participant network + sub-transaction privacy**, not an app-layer filter.
3. **Institutional controls + AI visibly subordinate.** Permissions/roles (initiate, approve, override), on-ledger auditability, critical actions behind explicit gates (human or deterministic rules) even when the agent proposes. AI = off-chain support only, no unilateral money movement. Quantify before/after value (liquidity freed, messages reduced, reconciliation simplified, faster finality).

### Where most teams lose points (avoid):
- Not actually running on Canton (mock / single-node / no participant views).
- Privacy fake/cosmetic — no meaningful signatory/observer/controller distinctions; everyone queries everything.
- Idea doesn't *require* Canton (could be Ethereum + access control).
- Demo scripted/broken/single-party.
- Agentic = LLM wrapper with no real Daml workflow/settlement.

### Contrarian risk I'm underweighting:
**Live Q&A domain-authenticity scrutiny.** Fast-shipping + clean demo can still lose if answers on legacy reconciliation, failed-settlement handling, risk-committee buy-in, multi-jurisdiction data rules, or participant-node ops sound like a whitepaper. This panel rewards practitioner empathy + process hygiene as much as architecture. **Action: practice answering operational questions in their language.**

---

## TECH STACK (from Q1 + Q4)

- **Language:** Daml (templates, choices, parties, signatories/observers/controllers). Functional, strongly typed. ~3–7 days to productive multi-party "hello world" for an experienced dev.
- **Privacy:** sub-transaction privacy — each party's participant node only stores/sees the sub-views relevant to them. This is the moat.
- **Settlement:** atomic multi-party via Settlement Batches/Instructions (all-or-nothing), coordinated by the Global Synchronizer.

### Day-1 resources (verify currency):
- **docs.canton.network** — consolidated dev docs (~May 2026).
- **cn-quickstart** (`github.com/digital-asset/cn-quickstart`) — official scaffolding: full LocalNet (Splice), participants, PQS (SQL query store), Canton Console, Daml Shell, Keycloak, demo wallet/UI. `git clone … && cd quickstart && make setup && make build && make start`. Docker + ~8GB RAM, JDK 21. **Post-July-2025: LocalNet only (no DevNet).**
- **daml-finance** (`github.com/digital-asset/daml-finance`) + **daml-finance-app** (integration example). Gives Instruments (Token/Bond/Equity/Generic), Holdings (Fungible/Transferable), Accounts (custody), **Settlement engine (atomic DvP, multi-leg, sub-tx privacy)**. Avoids rebuilding token/settlement primitives — huge 4-week leverage.
- **Agent integration:** JSON Ledger API (HTTP/JSON) — easiest from Python/TS. PQS for reading party-scoped state via SQL. `dpm codegen-js/java` for typed clients.
- **Help:** Canton Discord (tech), Encode Discord (logistics). Forum: forum.canton.network.

### Known unknowns (flagged by Grok):
- Exact current daml-finance package names/versions + one-command cn-quickstart integration are uncertain; no recent end-to-end "cn-quickstart + daml-finance" tutorial found. Expect to experiment / ask in workshop. **De-risk in Week 1.**
- DevNet/mainnet access for non-partners unclear; assume LocalNet for demo.

---

## SUGGESTED 4-WEEK PACING
- **W1:** cn-quickstart LocalNet running + daml-finance deps integrated; first Instrument/Holding/Account/Settlement flow across demo participants; learn tx trees + Daml Shell. **Resolve the daml-finance integration unknown ASAP.**
- **W2:** Core netting Daml: obligation contracts, multilateral net computation, atomic residual settlement w/ proper signatory/observer privacy. Role-based ACS reads via PQS/JSON API.
- **W3:** Off-chain AI layer (surface netting opportunities, prepare governed submissions, monitor, flag exceptions) behind approval gates. Role-based UI showing per-party private views + selective disclosure.
- **W4:** Exception/dispute path, polish, quantified before/after, 3-min video (problem → why-Canton privacy visual → live multi-party demo → impact), deck, repo README w/ "Why Canton" + architecture diagram, live link.

---

## OPEN QUESTIONS TO RESOLVE
1. **Prize structure** — $7k pool vs 5×$X challenge prizes? (changes whether to target one challenge vs global top-3). → Encode Discord.
2. Solo or team (up to 5 allowed)? Affects scope.
3. Is there a shared DevNet / party allocation for the hackathon, or LocalNet-only demos?
4. Confirm daml-finance + cn-quickstart integration path early (biggest technical unknown).

---

*Research files: `research/q1_tech_stack.md`, `q2_build_ideas.md`, `q3_winning_strategy.md`, `q4_landscape_resources.md`, `q5_pivot_validation.md`*
