# Q3: Winning Strategy & Judging Analysis

1. Weighting in practice at institutional/finance hackathons like this one (and similar Canton/Digital Asset or bank-led events).

Technical execution is the heaviest (roughly 35-40%). Canton + Daml has a real learning curve and specific primitives (participant nodes, sub-transaction privacy, Daml visibility rules, JSON Ledger API). If your code actually deploys, runs multi-party workflows on real participant setups (or the official cn-quickstart), and enforces privacy properly, you get a massive edge—most teams don't clear this bar.

Real-world applicability is next (25-35%). Judges include Canton Foundation / Digital Asset devrel + finance people. They ask: "Does this solve a genuine capital markets friction (collateral mobility, private OTC, netting, invoice financing, RWA lifecycle, etc.) that siloed systems or public chains can't handle cleanly?" Vague "DeFi but private" or consumer toy use cases die here.

Originality/creativity is 15-20%. Fresh angle or new primitive is good, but it must be grounded in Canton's actual strengths (sub-transaction privacy + atomic cross-participant sync without full data sharing). Wild unrelated ideas or "we added an LLM to a generic contract" score low.

UX/design is 10-15%. Polish helps a lot for the 3-min video and live demo perception, but a clean, functional interface (even if internal-tool style) beats a broken or confusing one. Judges forgive rough UI more than they forgive non-working privacy or irrelevant problem.

Where most teams lose points:

Not actually running on Canton (mock, single-node, or "we used the SDK but didn't show real participant views").
Privacy is fake or cosmetic (Daml contracts have no meaningful signatory/observer/controller distinctions; everyone can query everything; sub-transaction views aren't demonstrated).
Idea doesn't require Canton's model (could run on Ethereum with basic access control or off-chain).
Demo is scripted, broken, or single-party only.
Narrative is generic hype instead of specific institutional pain + Canton's unique unlock.
Agentic stuff is just an LLM wrapper with no real Daml workflow or settlement.

2. What separates top-3 from mid-pack in a privacy-finance hackathon.

Demo (biggest separator):
Top-3: Live on actual Canton participant setup (extend cn-quickstart with 2-3 participants). Agent triggers or participates in a real Daml workflow. Show side-by-side or toggled views: what Party A (e.g., Bank/Treasury) sees vs Party B (Custodian/Counterparty) vs what is correctly hidden. Real contract create/exercise that succeeds with atomicity and privacy preserved. If agentic, the agent reads its party's private Active Contract Set (ACS) and drives a choice or proposal that mutates ledger state. Judges can verify "this transaction only revealed the right sub-view."

Mid-pack: Single participant or mock. Privacy claimed but not shown (or demo shows full data to all viewers). Agent just chats or calls a public endpoint. Heavily scripted or video-only.

Narrative:
Top-3: Starts with a quantified institutional problem (e.g., "Collateral fragmentation and slow mobility costs X in opportunity cost/risk; current solutions either leak positions or can't settle atomically across silos"). Clearly states why public chains fail here (MEV, full leakage, no native compliance/audit model) and why siloed databases fail (no atomic cross-party workflows). Positions the solution as unlocking a specific Canton-enabled thing (private agent-coordinated netting/optimization, blind matching with selective disclosure, etc.). Ends with applicability and why this couldn't exist without Canton's privacy + sync model.

Mid-pack: Generic "finance needs privacy + AI" or "we made private DeFi." No specific pain point or Canton's unique role.

Technical depth:
Top-3: Non-trivial Daml (multiple interacting templates, proper visibility rules used meaningfully, observers for agents/auditors/regulators, contract keys, choices that enforce workflow). Canton participant/domain config. Agent uses JSON Ledger API (or equivalent) correctly and party-scoped. Clean code, docs, tests or simulation scripts proving multi-party execution + privacy. Real settlement/finalty demonstrated.

Mid-pack: Shallow Daml or none. Agent has god-mode visibility or bypasses rules. No actual ledger mutation or atomicity.

3. What makes judges go "wow, this is exactly what Canton is for" in an agentic-AI + Canton project.

Canton exists for institutional-grade shared infrastructure with need-to-know privacy (sub-transaction level) + atomic composability across participants/domains—without forcing full data replication or leakage. The wow is when your agentic system requires and demonstrates this model to do something valuable that alternatives can't.

Specific things that land:

Agent operates inside privacy boundaries (reads/writes only its party's view or as a proper observer) and drives real Daml workflows (proposes or executes choices) for multi-party outcomes like private collateral optimization/mobility, atomic private settlement, or blind netting—where revealing full positions/terms to all parties (or the agent itself) would be unacceptable.
Clear demonstration that without Canton's sub-transaction privacy + participant nodes, the agent either couldn't act safely across institutions or would leak sensitive data (positions, terms, counterparties). Show the "before" leakage vs "after" controlled visibility.
Ties to real production patterns (think Broadridge DLR repo scaling because of this privacy, or Euroclear-style collateral mobility) but adds agentic intelligence (monitoring private inventory, proposing moves, executing via Daml with audit trail).
Agent is a tool within guardrails, not rogue autonomous actor. Daml enforces authorization and visibility; agent proposes or assists within those rules. Finance judges hate "agent moves money with no controls."
Bonus: Shows composability (e.g., with tokenized assets/RWA or existing Canton apps) or new primitive like private agentic commerce / RFQ / data rooms with execution.

Judges (devrel + finance) light up when they see: "This workflow is only practical because Canton gives us privacy-preserving atomic sync that public chains and siloed systems both lack." Not "we put an LLM on a ledger."

4. Common failure modes that kill agentic/AI projects in finance hackathons.

Just an LLM wrapper: Pretty chat or "agent" that generates text, plans, or calls generic APIs but produces no real Daml contract exercise, ledger state change, or private multi-party outcome. Or the agent has full visibility into everything (bypassing the entire point of Canton).
Privacy is cosmetic or broken: Demo shows full transaction details to all parties or viewers. Daml contracts don't actually use signatories/controllers/observers meaningfully. Sub-transaction views aren't demonstrated or don't work.
No real settlement or finality: Everything is off-ledger simulation, "pending," or mocked. No atomic DvP/PvP-style outcome or Canton sync demonstrated.
Ignores regulated/finance realities: Agent acts with god-mode autonomy on institutional money/positions with no clear authorization model, human oversight points, or auditability. Canton/Daml is strong on audit trails and controlled visibility—projects that throw that away look unserious.
Overhyped autonomy without trust/controls: "Fully autonomous agent does finance" without showing how it fits compliance, permissions, dispute resolution, or Canton's party/visibility model. Judges want controllable, observable systems.
Generic or irrelevant idea: "Private AI trading agent" or "AI does DeFi privately" without specifying what privacy enables that wasn't possible before, or without deep use of a real finance primitive (collateral, netting, OTC execution, supply chain finance, etc.).
Demo/UX mismatch: Consumer-grade chatbot for what should feel like a professional treasury/risk/compliance tool. Or demo requires heavy local setup that judges can't easily verify.

5. Concrete 'proof of seriousness' checklist for top-3 quality submission.

Repo (public, clean, main branch ready):

README with: specific institutional problem + numbers/context, "Why Canton" section explaining sub-transaction privacy + how your project uses it (include simple diagram), full architecture (Daml roles/templates, agent components, privacy boundaries), exact setup instructions that work (base on/extend official cn-quickstart with multiple participants), privacy enforcement explanation, demo instructions, screenshots/video link.
Daml code: Non-trivial templates with real visibility rules (signatories, controllers, observers used for agent/audit roles), interacting workflows, contract keys, choices. Tests or scripts showing multi-party execution and different party views.
Agent/backend: Uses JSON Ledger API correctly and party-scoped. Clear separation so agent doesn't bypass privacy. Good structure, error handling, docs.
Frontend: Functional (even minimal). Shows role-based or private views.
Bonus signals: Docker/scripts for full multi-participant env; example flows proving privacy; references to official quickstart/docs; clean professional structure.

Deck (PDF or slides, 8-12 max):
Professional finance aesthetic (clean, minimal, blues/grays). Slides: Problem (quantified institutional pain), Why Canton (specific model + diagram), Solution + architecture (privacy callouts), Key primitives used, Agent role & guardrails, Demo flow/screenshots, Impact/applicability, Why this wins (originality + real-world fit). No walls of text; diagrams over bullet points. Tailored tone for both devrel and finance judges.

3-min video:
High-signal screen recording + clear voiceover (ElevenLabs finance-style or natural). Structure: 0-30s hook + problem, 30-90s why Canton + privacy visual (different party views), 90-150s live demo (agent acts → real Daml tx → private state changes), 150-180s impact/closing. Show actual participant views or logs. Every second demonstrates criteria. Polished editing; no fluff or talking-head padding.

Live link / verifiable demo:
Working frontend connected to a running Canton setup (or dead-simple instructions + scripts from repo to spin one up). Or clear public testnet/DevNet deployment. For agentic: triggerable live agent actions with observable private outcomes. Submission includes everything above plus a short note on unique Canton usage.

Extra top-3 signals: Extends official quickstart meaningfully. Uses real Daml patterns (or daml-finance libs where relevant). Shows measurable benefit (even simulated: faster private settlement, reduced data exposure, capital efficiency). Code looks production-grade (types, logging, error handling). Narrative works for both technical and finance audiences. Agent is a controlled tool inside Daml rules, not a bypass. No AI slop.

Ship something scoped but deep on one real Canton strength (private multi-party workflow + agent layer on top) rather than broad and shallow. That combination—working privacy demo + credible institutional narrative + clean execution—wins these. Good luck; this is winnable if you execute the privacy model properly.
