# Q1: Canton/Daml Tech Stack for Agentic Commerce

Daml (Digital Asset Modeling Language) is the smart contract language for Canton Network. It is a functional, Haskell-inspired, statically typed language purpose-built for multi-party financial workflows with declarative authorization and privacy.

1. Core Mental Model (Templates, Choices, Parties, Signatories)

Daml models rights and obligations between parties rather than global mutable state. Here is the precise mental model:

Templates are declarative blueprints (like classes). You define a template with data fields (parameters), signatory parties, optional observer parties, an optional ensure precondition, and embedded choice definitions. Templates live in .daml modules and compile into a DAR package.
Contracts are live instances of a template on the ledger. Each has a unique ContractId, the template ID, and concrete argument values. A contract represents an active state (e.g., an order, IOU, proposal, or settlement obligation).
Parties (Party type) are first-class principals representing real-world actors (users, organizations, agents, accounts, or sub-accounts). All authorization, visibility, and notifications are expressed in terms of Party values.
Signatories (declared with signatory keyword or derived from arguments) must authorize contract creation. They are the primary "owners" and typically control archiving. Controllers on choices are the parties authorized to exercise (perform) that specific action.
Stakeholders & Observers drive visibility: Stakeholders = signatories + observers of a contract. Only stakeholders can fetch/see the contract. Choices can declare additional observers for the sub-transaction outcome. This declarative model is what Canton enforces at the protocol level.

Example skeleton (typical pattern):

daml
Copy
template OrderProposal with
    proposer : Party
    counterparty : Party
    details : OrderDetails  -- your record type
  where
    signatory proposer
    observer counterparty

    choice Accept
      : ContractId Order
      with paymentRef : Text
      controller counterparty
      do
        -- atomic updates: archive self, create new contract(s), etc.
        create Order with ...

Daml transactions are built from atomic create / exercise / fetch actions inside choice bodies (in do blocks). The ledger validates authorization and preconditions before committing.

2. Canton's Privacy Model at Protocol Level (Sub-Transaction Privacy)

Canton does not replicate full transaction data everywhere (unlike public chains or many permissioned ledgers).

Daml defines visibility per contract and per choice via stakeholders (signatories + observers + choice observers/controllers as applicable).
Canton protocol decomposes every transaction into subtransactions — the minimal units affecting specific stakeholders/contracts.
Only the Participant Nodes hosting the relevant parties receive the encrypted payload for their sub-parts. Other participants and the network infrastructure receive only minimal metadata (ordering info, status, high-level routing hints — no business payload).
All inter-participant and participant-to-synchronizer traffic is end-to-end encrypted.
Sync domains (sequencer + mediator) see only encrypted blobs + metadata required for total ordering and consistency validation. They cannot decrypt or inspect content.
Result: Each participant maintains a private ledger view containing only the contracts and transaction history it is entitled to see. Global consistency is preserved without global data sharing. This enables "need-to-know" privacy, data minimization, and features like GDPR right-to-be-forgotten.

Example (DvP-style commerce): In an atomic delivery-vs-payment flow, the securities leg details are visible only to the relevant custodian/buyer/seller parties; the cash leg is visible only to the banks involved; high-level confirmation may be visible to a platform agent. No single party or infrastructure node sees the full picture unless explicitly modeled as a stakeholder.

This is Canton's core differentiator for institutional/privacy-sensitive agentic commerce.

3. Atomic Multi-Party Settlement

Daml guarantees atomicity at the language level: a single choice exercise (or top-level command) can atomically archive contracts, create new ones, and perform multiple updates in an all-or-nothing do block. If any precondition or authorization fails, the entire update is rejected.

Canton extends this across distributed participants:

The synchronizer (domain) coordinates via sequencer (ordering) and mediator (validation/commit coordination).
Even when subtransactions are privacy-partitioned and sent only to relevant participants, Canton ensures atomic commit semantics: either all involved participants successfully apply their view of the transaction to their private ledgers (consistent global state), or the transaction is rejected/rolled back everywhere.
This enables true atomic settlement (e.g., simultaneous asset transfer + payment + fee distribution) without requiring a central intermediary to see or custody everything.
Cross-domain atomicity is supported via bridging protocols where needed.

For your track: Model agent-initiated proposals, acceptances, payments, and fulfillments so that critical settlement steps happen inside atomic choice boundaries. Canton + Daml gives you the privacy + atomicity combination that is very hard on other platforms.

4. Fastest Local Dev Setup (as of mid-2026)

Primary tool: DPM (Digital Asset Package Manager) — the current CLI (replaces legacy daml assistant). It handles SDK management, project scaffolding, build, test, sandbox, codegen, etc.

Install DPM (Mac/Linux):

Bash
Copy
curl https://get.digitalasset.com/install/install.sh | sh

(Windows: use the installer from get.digitalasset.com. Requires JDK 17+.)

Fastest path for a new project:

Bash
Copy
dpm new my-agentic-commerce          # scaffolds package + daml.yaml
cd my-agentic-commerce
dpm build                            # compiles to .daml/dist/*.dar

Fastest local ledger: dpm sandbox (single-participant, simplest topology — perfect for initial Daml logic + agent integration testing):

Bash
Copy
dpm sandbox                          # Ledger API (gRPC) on :6865
dpm sandbox --json-api-port 7575     # + HTTP JSON Ledger API (recommended for agents)
dpm sandbox --dar path/to/my.dar     # upload DAR at startup

Key options: --config for auth/TLS/declarative state, --dev for dev protocol features.

For realistic multi-party testing (recommended for hackathon): Use cn-quickstart (full LocalNet with Docker Compose, multiple participants/validators, synchronizer, example app, observability, PQS):

Bash
Copy
git clone https://github.com/digital-asset/cn-quickstart.git
cd quickstart
make setup          # interactive config (parties, auth/Keycloak toggle, observability)
make build
make start          # brings up LocalNet + services
make shell          # Daml Shell for inspection
make canton-console # Canton console

Other essential commands:

dpm test — run Daml Script tests
dpm studio — launches Daml Studio (VS Code integration)
dpm codegen-js / dpm codegen-java — generate typed client libraries from your DAR (very useful for agent code)
dpm script ... — run Daml Scripts against a ledger

JSON Ledger API (HTTP/JSON over the Ledger API) is the most practical interface for AI agents (easy from Python/TS, curl, etc.). It supports command submission (create/exercise) and queries (active contracts, transaction trees, etc.). For production-grade querying, use PQS (Participant Query Store) — projects your party's contracts into PostgreSQL for standard SQL.

Testnet / Faucet: Start with local sandbox or LocalNet. For shared infrastructure, check the hackathon Discord/Slack or Canton channels for DevNet endpoints, party allocation, or test assets (quickstart includes examples like Canton Coin). No public "faucet" like EVM chains — parties and assets are provisioned via admin APIs or scripts in the participant environment.

Daml project basics: daml.yaml specifies sdk-version, name, source: daml, dependencies (include daml-prim, daml-stdlib, daml-script for testing), and optional init-script.

5. Realistic Learning Curve & Time-Sinks (4-Week Sprint)

Curve: 3–7 days to productive "hello world" multi-party flow if you are an experienced developer (especially with functional programming or strong typing background). The paradigm shift is the main hurdle. After that, velocity is high because the model matches financial workflows well and the type system + ledger enforcement catches many errors early.

Biggest time-sinks for newcomers (in rough order of impact on a privacy-focused agentic commerce build):

Authorization & privacy model design (biggest sink) — Getting signatory / observer / controller / choice observers correct for your specific flows. This directly determines what agents and counterparties can see/act on. Wrong model = either privacy leaks or agents/parties blocked from valid actions. Spend time upfront modeling the exact information flow for "agent proposes → counterparty reviews privately → atomic settlement."
Workflow decomposition into atomic choices — Breaking real commerce processes (negotiation, payment, fulfillment, agent coordination, disputes?) into composable templates where critical steps are atomic and invariants hold across sub-transactions. Debugging visibility or partial-update issues in transaction trees takes time.
Tooling & multi-environment workflow — Learning DPM commands, DAR lifecycle (build → upload via sandbox flag, declarative config, or API), switching between simple sandbox and realistic LocalNet, setting up JSON API or codegen clients in your agent code, and using Daml Shell / PQS for debugging. Auth (JWT) and TLS config add friction if you move beyond open sandbox.
Agent-ledger integration patterns — Your agents will typically act off-chain (monitoring via queries/PQS, deciding per strategy) and submit commands on behalf of on-ledger parties (via JSON API or generated clients). There is no native "autonomous agent" primitive — you build the autonomy layer. Mapping agent identity to Canton parties and handling command signing/authorization cleanly takes iteration.
Testing & observability of distributed private txs — Unit tests (Daml Script) are straightforward; integration testing across parties and verifying privacy (who sees what in tx trees) requires deliberate setup. PQS and Daml Shell help a lot here.

4-week feasibility: High for a strong MVP, especially leveraging cn-quickstart scaffolding, existing Daml Finance patterns (if tokenization/payments involved), and your existing agent harness experience.

Suggested pacing:

Week 1: DPM + sandbox/LocalNet setup, first templates (proposal + simple asset/settlement), basic JSON API integration from a script/agent, learn tx trees and Daml Shell.
Week 2: Core agentic commerce flows with proper privacy model (agent-initiated private proposals, atomic settlement choices).
Week 3: Agent autonomy layer (monitoring + autonomous choice exercise), PQS integration or advanced queries, polish + edge cases.
Week 4: Demo video (ElevenLabs-style narration works great), documentation, submission packaging, any hackathon-specific testnet integration.

Resources to prioritize:

Official unified docs at https://docs.canton.network/ (and linked Digital Asset build sections).
cn-quickstart GitHub + its make targets.
Daml learning modules/quests (mentioned in Canton pathways).
Daml Shell and PQS heavily during development.

You are in a strong position because your core strength (autonomous AI agents) maps directly onto Canton's strengths (private, atomic, multi-party workflows that agents can initiate and coordinate). The privacy model is a natural fit for "agentic commerce with privacy."

If you share more specifics about the exact commerce flow you're modeling (e.g., what the agent proposes, what gets settled atomically, which parties/observers are involved), I can help refine template sketches or integration patterns. Good luck with the hackathon — this track plays to Canton's and your strengths.
