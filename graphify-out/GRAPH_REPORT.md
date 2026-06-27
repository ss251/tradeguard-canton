# Graph Report - .  (2026-06-27)

## Corpus Check
- 84 files · ~202,515 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 423 nodes · 713 edges · 36 communities (27 shown, 9 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 59 edges (avg confidence: 0.82)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_V2 Netting Settlement Engine|V2 Netting Settlement Engine]]
- [[_COMMUNITY_Multilateral Netting Algorithm|Multilateral Netting Algorithm]]
- [[_COMMUNITY_Trade Finance & DvP Concepts|Trade Finance & DvP Concepts]]
- [[_COMMUNITY_CantonDaml Platform Primitives|Canton/Daml Platform Primitives]]
- [[_COMMUNITY_Settlement Agent CLI|Settlement Agent CLI]]
- [[_COMMUNITY_Multi-Party Settlement Record Views|Multi-Party Settlement Record Views]]
- [[_COMMUNITY_Dashboard & Live Privacy Screens|Dashboard & Live Privacy Screens]]
- [[_COMMUNITY_JSON Ledger API Client (v1)|JSON Ledger API Client (v1)]]
- [[_COMMUNITY_Accept-Authorize-Settle Wireframes|Accept-Authorize-Settle Wireframes]]
- [[_COMMUNITY_Outsider Privacy & Draft Screens|Outsider Privacy & Draft Screens]]
- [[_COMMUNITY_Role-View UI Server|Role-View UI Server]]
- [[_COMMUNITY_On-Ledger Netting & Guards|On-Ledger Netting & Guards]]
- [[_COMMUNITY_Agent Reasoning & Approval Layer|Agent Reasoning & Approval Layer]]
- [[_COMMUNITY_Daml Ledger Modules|Daml Ledger Modules]]
- [[_COMMUNITY_Atomic Settlement Orchestration|Atomic Settlement Orchestration]]
- [[_COMMUNITY_UI Layer & Demo Stack|UI Layer & Demo Stack]]
- [[_COMMUNITY_Demo Video Script|Demo Video Script]]
- [[_COMMUNITY_Project Planning & Strategy|Project Planning & Strategy]]
- [[_COMMUNITY_Real-Ledger Party Seeding|Real-Ledger Party Seeding]]
- [[_COMMUNITY_Daml Package Workspaces|Daml Package Workspaces]]
- [[_COMMUNITY_Linear Issue Posting|Linear Issue Posting]]
- [[_COMMUNITY_Canton 3.x LocalNet Client|Canton 3.x LocalNet Client]]
- [[_COMMUNITY_Real-Ledger Demo Script|Real-Ledger Demo Script]]
- [[_COMMUNITY_Video Preflight Script|Video Preflight Script]]
- [[_COMMUNITY_Linear Issue Creation Script|Linear Issue Creation Script]]
- [[_COMMUNITY_Tradeguard-Local Daml Package|Tradeguard-Local Daml Package]]
- [[_COMMUNITY_Demo Shell Script|Demo Shell Script]]
- [[_COMMUNITY_Linear Build Script|Linear Build Script]]
- [[_COMMUNITY_Agent Package Init|Agent Package Init]]
- [[_COMMUNITY_Stack Runner Script|Stack Runner Script]]
- [[_COMMUNITY_Tokenized Asset Concepts|Tokenized Asset Concepts]]
- [[_COMMUNITY_Canton Amulet Configuration|Canton Amulet Configuration]]
- [[_COMMUNITY_TradeGuard Daml Package|TradeGuard Daml Package]]
- [[_COMMUNITY_Seller Role|Seller Role]]

## God Nodes (most connected - your core abstractions)
1. `RealLedgerClient` - 30 edges
2. `attempt_fraud()` - 18 edges
3. `Obligation` - 18 edges
4. `settle_real()` - 17 edges
5. `minimal_settlement()` - 13 edges
6. `LedgerClient` - 11 edges
7. `netting_report()` - 11 edges
8. `load_real_parties()` - 11 edges
9. `net_positions()` - 10 edges
10. `TradeGuard` - 10 edges

## Surprising Connections (you probably didn't know these)
- `PrivyFactor` --semantically_similar_to--> `TradeGuard`  [INFERRED] [semantically similar]
  PIPELINE.md → ARCHITECTURE.md
- `PQS (Participant Query Store)` --semantically_similar_to--> `JSON Ledger API`  [INFERRED] [semantically similar]
  STRATEGY.md → ARCHITECTURE.md
- `Live Settlement Record UI` --semantically_similar_to--> `Settlement Record 4-Role Screen`  [INFERRED] [semantically similar]
  ui/live.html → wireframes/tradeguard-settlement.html
- `TradeGuard Settlement Agent` --semantically_similar_to--> `Agent Layer (Python)`  [INFERRED] [semantically similar]
  agent/README.md → ARCHITECTURE.md
- `real_client.py` --semantically_similar_to--> `ledger_client.py`  [INFERRED] [semantically similar]
  STATUS.md → ARCHITECTURE.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Governed Settlement Flow (monitor-reason-recommend-approve-settle)** — architecture_reasoner, architecture_settlement_recommendation, architecture_human_gate, architecture_approved_action, architecture_settlement_batch [EXTRACTED 0.90]
- **Three-Layer Architecture (UI/Agent/Ledger)** — architecture_ui_layer, architecture_agent_layer, architecture_ledger_layer [EXTRACTED 0.90]
- **On-ledger Adversarial Safety Guards (conservation/efficiency/funding)** — deck_netting_batch, deck_adversarial_guards, deck_multilateral_netting [EXTRACTED 0.85]
- **Atomic DvP Settlement on Canton** — research_canton_build_bible_atomic_dvp, research_canton_build_bible_global_synchronizer, research_canton_build_bible_selective_disclosure, research_canton_build_bible_herstatt_risk [INFERRED 0.85]
- **Daml Template Authorization & Privacy Model** — research_canton_build_bible_template, research_canton_build_bible_signatory_observer_controller, research_canton_build_bible_choice, research_canton_build_bible_propose_accept [EXTRACTED 0.75]
- **Canton Hackathon Project Candidates** — research_synthesis_netopti, research_canton_build_bible_tradeguard, research_q2_build_ideas_privyfactor, research_q2_build_ideas_privysweep [EXTRACTED 0.75]
- **Draft to Settle Trade Workflow Screens** — wireframes_propose_draft_proposal, wireframes_accept_review_accept, wireframes_agent_agent_approval, wireframes_settlement_settlement_record [EXTRACTED 1.00]
- **Four-Role Privacy Settlement Views** — wireframes_settlement_settlement_record, ui_live_settlement_record, concept_subtransaction_privacy [INFERRED 0.75]
- **tradeguard-v3 Multi-Package Build** — tradeguard_v3_multi_package_workspace, tradeguard_v3_main_daml_tradeguard_main, tradeguard_v3_test_daml_tradeguard_test [EXTRACTED 1.00]
- **Accept to Authorize to Settle Workflow** — shots_accept_view, shots_agent_view, shots_accept_settled_view, shots_buyer_view [INFERRED 0.85]
- **Live Settlement Record - Multi-party Privacy View** — shots_live_buyer_view, shots_live_regulator_view, shots_live_outsider_view [EXTRACTED 1.00]
- **TradeGuard Settlement Workflow (dashboard to exception)** — shots_index_view, shots_dashboard_view, shots_exception_view, shots_live_buyer_view [INFERRED 0.85]
- **Outsider Sub-Transaction Privacy Sequence** — shots_outsider_view, shots_outsider2_view, shots_outsider3_view, shots_outsider_final_view [INFERRED 0.85]
- **Trade Proposal Drafting Flow** — shots_propose_view, shots_propose2_view, shots_propose_trade_proposal_contract [INFERRED 0.75]
- **Settlement Record Across Four Party Views (Buyer, Seller, Regulator, Outsider)** — shots_real_buyer_view, shots_seller_view, shots_regulator_view, shots_real_outsider_view [INFERRED 0.85]
- **Regulator Oversight View Variants** — shots_regulator_view, shots_regulator3_view, shots_seller2_view [INFERRED 0.65]
- **Seller Projection View Variants** — shots_seller_view, shots_seller2_view, shots_real_buyer_view [INFERRED 0.55]

## Communities (36 total, 9 thin omitted)

### Community 0 - "V2 Netting Settlement Engine"
Cohesion: 0.10
Nodes (38): attempt_fraud(), _authority_cid(), _book_facts(), _created_cid(), _ensure_account(), _err(), _id(), _instr() (+30 more)

### Community 1 - "Multilateral Netting Algorithm"
Cohesion: 0.11
Nodes (30): minimal_settlement(), net_positions(), netting_report(), Obligation, Multilateral netting — the settlement-optimization brain.  Given a set of bilate, Net position per party: positive = net receiver, negative = net payer., Compute the minimal set of residual transfers that settles all obligations., A full, auditable netting report the agent attaches to its recommendation. (+22 more)

### Community 2 - "Trade Finance & DvP Concepts"
Cohesion: 0.08
Nodes (35): Atomic DvP, daml-finance Library, DvP (Delivery vs Payment), Global Synchronizer, Settlement Risk (Herstatt), JSON Ledger API, Letter of Credit, Off-Chain Governed Agent (+27 more)

### Community 3 - "Canton/Daml Platform Primitives"
Cohesion: 0.07
Nodes (34): Bond, Broadridge DLR Repo Platform, Canton, Canton Loop Wallet, Daml Choice, Daml, Daml Script, DAR (Daml Archive) (+26 more)

### Community 4 - "Settlement Agent CLI"
Cohesion: 0.12
Nodes (29): _approver(), _client(), cmd_approve(), cmd_net(), cmd_reject(), cmd_settle(), cmd_status(), cmd_watch() (+21 more)

### Community 5 - "Multi-Party Settlement Record Views"
Cohesion: 0.12
Nodes (30): Agent + Human Authorization, Agent Proposes, Human Disposes Governance, Atomic DvP Settlement, Buyer Role (Importer Co.), Canton JSON Ledger API / PQS Query, Outsider Role (Public, Non-Stakeholder), Regulator Role (FCA Observer), Seller Role (Exporter Ltd.) (+22 more)

### Community 6 - "Dashboard & Live Privacy Screens"
Cohesion: 0.18
Nodes (18): Active Contract Set (party-scoped feed), Agent + Human Authorization Gate, Atomic DvP Settlement, Delivery Attestation Window, Exception Resolution (Extend / Cancel / Escalate), Canton JSON Ledger API / PQS query, Buyer Role (Importer Co.), Outsider Role (Public) (+10 more)

### Community 7 - "JSON Ledger API Client (v1)"
Cohesion: 0.18
Nodes (9): _b64(), LedgerClient, load_pkgid(), make_token(), Thin client for the Canton JSON Ledger API (v1).  Handles per-party JWT auth, qu, Build an insecure (unsigned) Daml JWT for the sandbox JSON API., A JSON Ledger API client scoped to one party., Fully-qualify a template id. We use the package-NAME reference         ('#tradeg (+1 more)

### Community 8 - "Accept-Authorize-Settle Wireframes"
Cohesion: 0.20
Nodes (17): Review & Accept Screen - Settled State (Buyer), Review & Accept Screen (Buyer), Accept Workflow Step, Agent Approval Screen (Authorizer), Atomic DvP Settlement, Authorize Workflow Step, Bill of Lading 7741 Asset Title, Settlement Record - Sidebar Reader Views (Buyer) (+9 more)

### Community 9 - "Outsider Privacy & Draft Screens"
Cohesion: 0.23
Nodes (16): Outsider View with Buyer Disclosure Panel Visible, Protocol-Redacted Instrument Fields, Outsider View with Redacted Instrument Fields, Atomic DvP Settlement Method, Outsider Final View (Status Not Disclosed), No Record Disclosed (Ledger Returns None), Public / Outsider Role (Non-Stakeholder), Settlement Record Screen (Multi-Reader Projection) (+8 more)

### Community 10 - "Role-View UI Server"
Cohesion: 0.26
Nodes (8): BaseHTTPRequestHandler, _b64(), build_view(), Handler, ledger_query(), load_parties(), Build a role's live view of the settled trade from real ledger data., token_for()

### Community 11 - "On-Ledger Netting & Guards"
Cohesion: 0.22
Nodes (11): On-ledger Adversarial Guards, Private Multilateral Netting, NettingBatch, Netting Operator, Obligation, demo.sh, Netting.daml, netting (agent module) (+3 more)

### Community 12 - "Agent Reasoning & Approval Layer"
Cohesion: 0.28
Nodes (9): Coordinator Party, TradeGuard Settlement Agent, Agent Layer (Python), ApprovedAction, cli.py, Human Approval Gate, Agent Module, reasoner.py (+1 more)

### Community 13 - "Daml Ledger Modules"
Cohesion: 0.22
Nodes (9): Canton Network, daml-finance v4, Ledger Layer (Daml), Holding Module, Instrument Module, Trade Module, Types Module, Sub-transaction Privacy (+1 more)

### Community 14 - "Atomic Settlement Orchestration"
Cohesion: 0.25
Nodes (8): Orchestrator (lock/allocate/settle), Atomic Delivery-versus-Payment (DvP), Settlement Module, SettledTrade Audit Record, SettlementAuthority Delegation, SettlementBatch, Herstatt Risk, Global Synchronizer

### Community 15 - "UI Layer & Demo Stack"
Cohesion: 0.29
Nodes (8): TradeGuard, UI Layer, ui_server.py, Demo Script, Role-based Privacy UI, Build on Canton Hackathon, run_stack.sh, Project Status

### Community 16 - "Demo Video Script"
Cohesion: 0.39
Nodes (6): demo_video.sh script, banner(), beat(), make_jwt(), PATH, say()

### Community 17 - "Project Planning & Strategy"
Cohesion: 0.25
Nodes (8): Hermes Kanban Board, Linear Backlog, Pipeline Design (Linear + Kanban), PrivyFactor, cn-quickstart, Grok Deep Research Passes, PQS (Participant Query Store), Strategy & Findings

### Community 18 - "Real-Ledger Party Seeding"
Cohesion: 0.43
Nodes (7): admin_token(), allocate_parties(), api(), _b64(), grant_rights(), main(), Grant the user CanActAs for every TG party so the admin token can act as them.

### Community 19 - "Daml Package Workspaces"
Cohesion: 0.33
Nodes (7): df-probe Daml Package, daml-finance v4 vendor DARs, tradeguard Daml Package (tradeguard/), TradeGuard.Init:initialize init-script, tradeguard v1.1.0 (v3 main), tradeguard-v3 multi-package workspace, tradeguard-test (v3 test)

### Community 20 - "Linear Issue Posting"
Cohesion: 0.62
Nodes (5): gql(), issue_id(), post_comment(), set_status(), upload_image()

### Community 21 - "Canton 3.x LocalNet Client"
Cohesion: 0.40
Nodes (6): JSON Ledger API, ledger_client.py, tradeguard-v3 (Canton 3.x port), Canton Builder LocalNet (3-validator), real_client.py, seed_real.py

### Community 22 - "Real-Ledger Demo Script"
Cohesion: 0.67
Nodes (3): demo_real.sh script, make_jwt(), PATH

### Community 23 - "Video Preflight Script"
Cohesion: 0.67
Nodes (3): preflight_video.sh script, chk(), PATH

### Community 25 - "Tradeguard-Local Daml Package"
Cohesion: 0.67
Nodes (3): tradeguard-local Daml Package, tradeguard-local dlint config, Main:setup init-script

## Knowledge Gaps
- **69 isolated node(s):** `PATH`, `PATH`, `PATH`, `run_stack.sh script`, `daml-finance v4` (+64 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `RealLedgerClient` connect `V2 Netting Settlement Engine` to `Multilateral Netting Algorithm`, `Role-View UI Server`, `Settlement Agent CLI`?**
  _High betweenness centrality (0.049) - this node is a cross-community bridge._
- **Why does `Obligation` connect `Multilateral Netting Algorithm` to `V2 Netting Settlement Engine`, `Settlement Agent CLI`?**
  _High betweenness centrality (0.023) - this node is a cross-community bridge._
- **Why does `LedgerClient` connect `JSON Ledger API Client (v1)` to `Settlement Agent CLI`?**
  _High betweenness centrality (0.016) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `RealLedgerClient` (e.g. with `Handler` and `Handler`) actually correct?**
  _`RealLedgerClient` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `TradeGuard off-chain settlement agent.`, `TradeGuard settlement agent — CLI + monitoring loop.  Commands:   status   snaps`, `True if a create/exercise succeeded, across v1 (status==200) and v2     (returns` to the rest of the system?**
  _117 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `V2 Netting Settlement Engine` be split into smaller, more focused modules?**
  _Cohesion score 0.0963265306122449 - nodes in this community are weakly interconnected._
- **Should `Multilateral Netting Algorithm` be split into smaller, more focused modules?**
  _Cohesion score 0.10953058321479374 - nodes in this community are weakly interconnected._