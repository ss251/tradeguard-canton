# Pipeline Design — Linear + Kanban

## Roles (two-layer system)

| Layer | Tool | Purpose | Lifespan |
|-------|------|---------|----------|
| **Backlog / source of truth** | **Linear** (team `THE`, project "Canton Hackathon — PrivyFactor") | Durable plan: epics, issues, priorities, due dates, the research record | Whole hackathon |
| **Live execution board** | **Hermes Kanban** (board `canton`) | Day-to-day working surface; claim/swarm/complete tasks; what's actively in flight | Per-sprint, ephemeral |

**Flow:** Research → Linear issues (plan) → mirror active sprint onto Kanban → work/claim/complete → status syncs back to Linear.

## Linear structure

**Project:** `Canton Hackathon — PrivyFactor` (privacy-preserving autonomous invoice-factoring agent)

**Workflow states (existing):** Backlog → Todo → In Progress → In Review → Done

**Labels:** research, infra, daml, agent, privacy, demo (create the missing ones)

**Epics (parent issues) + children:**

### E0 — Research & Strategy ✅ (done)
- Canton hackathon brief captured
- Grok deep research ×4 (tech stack, build ideas, winning strategy, landscape)
- STRATEGY.md synthesis → bet on PrivyFactor

### E1 — Week 1: Infra & Foundations
- Run cn-quickstart LocalNet end-to-end (`make setup/build/start`)
- Clone + study daml-finance + daml-finance-app
- Resolve Daml Finance dep versions into daml.yaml (FLAGGED: under-documented)
- First templates: Invoice/Claim + private Offer
- Wire JSON Ledger API + PQS read path for the agent
- Learn tx trees / Daml Shell / Canton console

### E2 — Week 2: Core Private Settlement Flow
- Model signatories/observers for agent→counterparty→atomic settle (privacy design)
- SupplierAgent posts private Offer (visible only to authorized Factor)
- FactorAgent reviews + accepts/counters via Daml choice
- Atomic DvP: cash ↔ invoice claim in one settlement batch
- Verify privacy: Party A sees X, Party B sees Y, outsider sees nothing (tx-tree check)

### E3 — Week 3: Agent Autonomy + LLM Orchestration
- Agent decision loop: query private state (PQS) → decide → submit command
- LLM orchestration: NL instruction → propose/validate/execute Daml choices
- Conditional logic + multi-party coordination
- Role-based UI for the demo video (per-party private views)

### E4 — Week 4: Submission Package
- Polish scenarios + exception handling
- 3-min video: multi-party private views + atomic settle + agent reasoning trace
- Presentation deck (problem/market/why-Canton-privacy-essential)
- Clean documented public repo + live LocalNet demo link
- Final submission on Encode Club

## Kanban board `canton`
Mirror E1 (current sprint) tasks as claimable Kanban cards. Use `hermes kanban create --board canton`. Swarm-able for parallel sub-agent execution later.

## Priority map (Linear: 1=Urgent…4=Low)
- E1 infra = Urgent (1) — blocks everything
- E2 core flow = High (2)
- E3 agent layer = High (2)
- E4 submission = Medium (3) until week 4
