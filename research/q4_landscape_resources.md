# Q4: Competitive Landscape & Resources

Here is the concrete, current competitive landscape and resource map for the Build on Canton Hackathon (Encode Club, started 15 June 2026, 4 weeks, $7k top-3 prizes across tracks including explicit "Payments, Neobanking & Agentic Commerce" with privacy focus). All info is pulled from official repos, docs, and hackathon pages as of mid-June 2026.

1. Day 1 Concrete Canton/Daml Resources (What to Use Immediately)

Primary hub (start here):
https://docs.canton.network/ (consolidated developer docs launched ~May 2026; covers overview, quickstart, appdev, Canton concepts, and links to tools).

#1 Day 1 action — Canton Network Quickstart (cn-quickstart):
Repo: https://github.com/digital-asset/cn-quickstart
This is the official scaffolding for Canton apps on the Global Synchronizer. It gives you a full LocalNet (via Splice), Canton nodes/participants, Daml environment, PQS (Participant Query Store for SQL queries on holdings/contracts), Canton Console, Daml Shell, observability (optional), Keycloak, and demo UIs (wallet, ANS/name registration, Scan for tx monitoring).

Setup (follow README exactly):

Bash
Copy
git clone https://github.com/digital-asset/cn-quickstart.git
cd cn-quickstart
direnv allow
cd quickstart
make setup
make build
make start

Then in separate terminals: make canton-console and make shell (Daml Shell). It includes a Licensing Model Workflow demo you can extend or replace.

Notes/Flags (current as of June 2026):

Post-July 2025 architectural change: No longer connects to DevNet (LocalNet only; run make clean-all + make build after changes).
Assumes Daml Enterprise license for full runtime features (open-source use is fine for learning/hackathon prototyping).
Docker + ~8GB+ RAM recommended. Uses JDK 21 in containers.
Excellent for hackathons/day 1 — resolves infra, onboarding, and multi-participant setup so you focus on Daml logic + agent layer.

Daml Finance library (core primitives — clone this too):
Repo: https://github.com/digital-asset/daml-finance
Demo integration example: https://github.com/digital-asset/daml-finance-app (study this for how to wire it into a full Daml app).

Integration path (high-level, see below for details): Add relevant packages to your daml.yaml dependencies (or use pre-built DARs from the repo). Common ones historically include daml-finance-interface-instrument-token, daml-finance-instrument-token, daml-finance-interface-holding (Fungible/Transferable), daml-finance-holding, daml-finance-interface-settlement, daml-finance-settlement, daml-finance-interface-account, plus interfaces for claims/lifecycle/types. Build with daml build and upload DARs via Canton tools or quickstart flows.

Other immediate resources:

Daml SDK / dpm (Daml Package Manager) — set up automatically via quickstart make commands.
Canton Console + Daml Shell (from quickstart) for interacting with contracts, parties, and queries.
PQS (built into quickstart) — query holdings/accounts/contracts via SQL (very useful for your agent to read state).
Forum: forum.canton.network (active for integration questions).
Hackathon-specific: Encode Club page + workshops (Canton Tech Deep Dive, ecosystem overview). Leverage mentors/speakers from Canton Foundation/Digital Asset.

Uncertainties to flag (say so explicitly):
Exact current (June 2026) Daml Finance package names/versions and one-command integration steps into the latest cn-quickstart (public examples are older; the old daml new quickstart-finance template is superseded). No recent public "cn-quickstart + Daml Finance" end-to-end tutorial found. You will likely need to experiment (clone both, study daml-finance-app, add deps to daml.yaml, test in LocalNet) or ask in the hackathon workshop/forum. DevNet/mainnet access for non-partners is unclear/limited (quickstart is LocalNet-focused).

Day 1 plan: Clone + fully run cn-quickstart (get LocalNet + demo running). Clone daml-finance + daml-finance-app. Read the high-level Canton overview on docs.canton.network. Then start wiring Daml Finance primitives into a copy/extension of the quickstart's Daml code.

2. Daml Finance Library — What You Get Out of the Box

It is a collection of purpose-built, modular, composable Daml libraries for enterprise-grade tokenization and finance primitives. Goal: avoid reinventing asset models, custody, transfers, and settlement so you can focus on business logic, workflows, and (in your case) agent orchestration.

Core building blocks it gives you:

Instruments: Define rights, obligations, and economic terms of an asset. Built-in implementations for Token (fungible), Bond, Equity, and Generic (via Contingent Claims library for complex/arbitrary payoffs like options, swaps, or custom instruments). The Instrument contract encodes lifecycling logic (e.g., coupon payments, dividends, corporate actions, versioned updates). You issue instruments and they carry their own rules.
Holdings: Represents a specific quantity of an Instrument held in an Account (your "position"). Interfaces: Fungible (split/merge quantities cleanly) and Transferable (transfer logic). Factories create holdings. This is your balance/ownership primitive — no need to code ERC-20-style logic or custom registries.
Accounts: Custodial account model with Credit/Debit operations. Tied to a HoldingFactory. Manages where holdings live and supports real-world custody chains/hierarchies.
Settlement: Atomic settlement engine for complex, multi-step, multi-party transactions (e.g., DvP — Delivery vs Payment). Uses Settlement Batches/Instructions that atomically move multiple holdings. Canton protocol enforces atomicity (all-or-nothing) + sub-transaction privacy (each party sees only the legs relevant to them; e.g., cash leg hidden from securities parties and vice versa). Supports custodial hierarchies and real institutional flows.

Additional supporting modules: Claims (contingent), Lifecycle (event processing), common types.

How it accelerates an agentic payments build (massive leverage for 4-week hackathon):
You do not spend time designing or implementing basic token standards, holding factories, balance/transfer logic, or atomic settlement primitives. These are standardized, tested, and composable.

Your agent layer focuses on the high-value parts: natural language or event-driven instructions ("pay supplier X privately when invoice confirmed"), state querying (via PQS on holdings/accounts), decision logic (rules + LLM), proposing/validating/executing Daml choices on Settlement or Holding contracts, and coordinating multi-party flows with Canton's privacy model.

Example accelerated flow: Agent reads current Holdings → proposes a Settlement batch (cash vs goods or netting) → other parties (or their agents) review/accept via choices → atomic execution with sub-tx privacy. Add lifecycling if your payment instrument has terms. This turns weeks of primitive work into days, letting you ship a sophisticated agent-orchestrated commerce demo. It also aligns perfectly with Canton's strengths (privacy granularity + atomic multi-party settlement) instead of fighting them.

3. What Most Teams Will Probably Build (Saturated Ideas — Avoid the Crowd)

Given the tracks (Private DeFi & Capital Markets; TradeFi/RWA & Tokenized Assets; Payments/Neobanking & Agentic Commerce) and institutional-grade focus:

Basic tokenized asset / RWA issuance platforms: Issue Bond/Token/Eq instruments via Daml Finance, simple holding/transfer UI or dashboard, basic settlement.
Simple private payments or neobanking wallets: Accounts + Holdings for transfers, privacy controls, basic multi-party flows.
Generic settlement engines or OTC/confidential lending matching with Canton privacy toggles.
Tokenized deposits or invoice financing with straightforward workflows and frontend polish.
"Private DeFi" primitives (simple swaps or lending) wrapped in a nice UI, often just demonstrating Daml Finance + Canton privacy without deep automation or novel agent use.

Crowd characteristics: Heavy on frontend/demo polish around the primitives, basic multi-party Daml workflows, or "institutional DeFi" dashboards. Many will treat Daml Finance as a black box or UI layer. Shallow or off-chain-only "agentic" attempts (chat interfaces that don't actually drive on-ledger choices/settlements). Low emphasis on deep composability, agent orchestration of complex/privacy-sensitive flows, or leveraging sub-transaction privacy in intelligent ways.

To avoid the crowd: Go deep on the agentic commerce track with real on-ledger agent actions, novel use of Canton's privacy model in agent decisions, automation of treasury/commerce ops pain points, or agent-to-agent/agent-to-institution private flows. Combine your AI agent expertise with Daml Finance + Canton primitives instead of just wrapping them.

4. Genuine White Space in Agentic Commerce with Privacy (Achievable in 4 Weeks)

Strong white space: Autonomous/privacy-preserving AI Treasury or Payments Agent (or "Agentic Settlement Co-Pilot") that acts as an intelligent orchestrator for B2B payments, netting, conditional settlements, or neobanking treasury ops.

Why white space (few will attempt this depth):
Most teams will stop at basic issuance/transfer/settlement UIs or simple private matching. True agentic commerce (agents as active participants or coordinators that propose/execute Daml choices, handle state via PQS, make LLM-assisted decisions, and leverage sub-tx privacy for confidential multi-party flows) is explicitly called out in the hackathon problem statements but will be under-served. Combining strong AI agent implementation (your strength) with Canton's unique privacy granularity + Daml Finance atomic settlement/lifecycling in one cohesive, demoable product is rare. Shallow chatbots or fully off-chain agents won't differentiate.

Achievable in 4 weeks (realistic scope):

Week 1: Full cn-quickstart LocalNet running + Daml Finance integration (add deps, basic Instrument/Holding/Account/Settlement flows working in demo participants).
Week 2: Agent backend that can query state (PQS/SQL) and drive Daml choices (via scripts, Canton tools, or simple API layer). Basic holding/settlement creation and execution.
Week 3: LLM orchestration layer (natural language instructions → agent proposes/validates/executes settlements; conditional logic, e.g., "settle if holdings sufficient and invoice private signal received"; multi-party coordination in demo). Simple frontend for user ↔ agent interaction.
Week 4: Polish scenarios (e.g., merchant payment agent settling with supplier privately via netting or atomic DvP; exception handling), video/demo, deck. Use LocalNet with multiple simulated parties/roles.

Privacy angle that few will nail: Agent-orchestrated flows where Canton sub-tx privacy ensures minimal disclosure (e.g., payer/payee see only their legs; agent coordinates without revealing full positions). Verifiable on-ledger actions + agent decision auditability.

This is deep enough to stand out but scoped to ship with your existing agent harness experience + the primitives provided.

5. One Project Archetype to Bet On for Top-3 (as AI-Agent Specialist)

Bet on: Privacy-Preserving Autonomous Treasury/Payments Agent for Agentic Commerce (or "Canton AI Treasury Co-Pilot").

Elevator pitch:
"The Canton AI Treasury Agent: an intelligent, privacy-first co-pilot that lets institutions, merchants, and neobanks autonomously orchestrate complex B2B payments, settlements, netting, and treasury operations on Canton. Tell it in natural language or via events ('Net and settle outstanding invoices with SupplierX privately if liquidity allows') and it queries Daml Finance holdings/accounts (via PQS), proposes atomic multi-leg Settlement batches, leverages Canton's sub-transaction privacy so counterparties see only their authorized parts, coordinates execution across parties, and handles lifecycling or exceptions. Built on cn-quickstart + Daml Finance primitives + lightweight LLM agent layer in 4 weeks. Delivers immediate operational value by cutting manual work, errors, and information leakage in commerce and capital markets while showcasing Canton's killer features in private multi-party workflows. Fully demoable with LocalNet multi-participant scenarios, real on-ledger agent actions, and strong privacy guarantees."

Why this wins top-3 for an AI-agent specialist:
It directly hits the hackathon's explicit "Agentic Commerce with privacy" problem statement and institutional-grade mandate. It differentiates you as the AI specialist who deeply understands and leverages Canton's privacy model + Daml Finance (instead of just UI-wrapping primitives like most teams). High originality (agent orchestration of complex/privacy-sensitive flows is rare), strong technical execution (real Daml choices + atomic settlement + PQS + LLM), excellent real-world applicability (treasury ops and B2B payments are painful; privacy is Canton's moat), and perfectly scoped for 4 weeks with your stack. Judging criteria (technical execution, originality/creativity, real-world applicability, UX/demo quality, privacy demonstration) align strongly. It positions you as the builder who "gets" both AI agents and Canton's enterprise value prop.

This is actionable, concrete, and current. Start with cn-quickstart today — it will give you the biggest head start. If you hit integration snags on Daml Finance deps, the hackathon workshops/mentors and forum are your next stop. Good luck; this archetype has real winning potential.
