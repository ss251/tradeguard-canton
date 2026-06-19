#!/usr/bin/env python3
"""Build the Canton Hackathon Linear backlog: 5 epics + child issues, labeled & prioritized."""
import os, json, subprocess

API = "https://api.linear.app/graphql"
KEY = os.environ["LINEAR_API_KEY"]
TEAM = "4358a3b0-2202-4701-bb6b-feebdef13ff6"
PROJECT = "0ba4a311-9948-4ce8-ae47-4b7202b871f4"

STATE_TODO = "a8476c30-2ffc-42b3-b314-ec43ebbbe8e8"
STATE_DONE = "b9fd2a3a-aa1d-470e-b105-213b5ec8f0bf"

def gql(query, variables=None):
    body = {"query": query}
    if variables:
        body["variables"] = variables
    p = subprocess.run(
        ["curl", "-s", "-X", "POST", API,
         "-H", f"Authorization: {KEY}",
         "-H", "Content-Type: application/json",
         "-d", json.dumps(body)],
        capture_output=True, text=True)
    r = json.loads(p.stdout)
    if r.get("errors"):
        raise RuntimeError(r["errors"])
    return r["data"]

# fetch label ids
labels = {n["name"]: n["id"] for n in gql("{ issueLabels { nodes { id name } } }")["issueLabels"]["nodes"]}

CREATE = """mutation($input: IssueCreateInput!) {
  issueCreate(input: $input) { success issue { id identifier title url } }
}"""

def make(title, desc="", priority=0, label_names=(), parent=None, state=None):
    inp = {"teamId": TEAM, "projectId": PROJECT, "title": title,
           "description": desc, "priority": priority,
           "labelIds": [labels[n] for n in label_names if n in labels]}
    if parent: inp["parentId"] = parent
    if state: inp["stateId"] = state
    d = gql(CREATE, {"input": inp})["issueCreate"]
    iid = d["issue"]["identifier"]
    print(f"  {iid}  {title}")
    return d["issue"]["id"]

# ---- EPICS ----
print("E0 Research (done)")
e0 = make("E0 — Research & Strategy", 
    "Research complete. See repo: STRATEGY.md, PIPELINE.md, research/q1-q4.\n\n"
    "**Bet:** PrivyFactor — privacy-preserving autonomous invoice-factoring agent on Canton.\n"
    "Grok-ranked #1 (feasibility 4 + wow 5). Converges with Q4 'AI Treasury Co-Pilot' archetype.",
    priority=3, label_names=["research"], state=STATE_DONE)
for t in [
    ("Capture Canton hackathon brief (tracks, prizes, judging, deadlines)", "Done — $7k, 4 wks, Track 3 agentic commerce w/ privacy."),
    ("Grok research: Canton/Daml tech stack", "research/q1_tech_stack.md"),
    ("Grok research: 6 agentic-commerce build ideas + ranking", "research/q2_build_ideas.md — PrivyFactor wins (9)."),
    ("Grok research: winning strategy + judging analysis", "research/q3_winning_strategy.md"),
    ("Grok research: competitive landscape + resources", "research/q4_landscape_resources.md"),
    ("Synthesize STRATEGY.md (decide the bet)", "Done — PrivyFactor primary; TradeGuard/PrivySweep backups."),
]:
    make(t[0], t[1], priority=3, label_names=["research"], parent=e0, state=STATE_DONE)

print("E1 Week1 Infra")
e1 = make("E1 — Week 1: Infra & Foundations",
    "Stand up the Canton dev environment and first templates. BLOCKS everything.", 
    priority=1, label_names=["infra"])
for t in [
    ("Run cn-quickstart LocalNet end-to-end",
     "git clone github.com/digital-asset/cn-quickstart; direnv allow; cd quickstart; make setup/build/start.\n"
     "Needs Docker + 8GB+ RAM, JDK21. LocalNet only (no DevNet post-Jul2025).", ["infra"]),
    ("Clone + study daml-finance and daml-finance-app",
     "github.com/digital-asset/daml-finance (+ -app for wiring patterns). Source of Instrument/Holding/Account/Settlement.", ["daml"]),
    ("Resolve Daml Finance dep versions into daml.yaml",
     "⚠️ RISK: exact current package names/versions + integration into latest cn-quickstart is under-documented. "
     "Experiment or ask in workshop/forum.", ["daml"]),
    ("Build first templates: Invoice/Claim + private Offer",
     "Tokenized invoice claim + an Offer contract visible only to authorized Factor.", ["daml","privacy"]),
    ("Wire JSON Ledger API + PQS read path for the agent",
     "JSON Ledger API = practical agent interface. PQS projects contracts→Postgres for SQL state reads. dpm codegen-ts.", ["agent","infra"]),
    ("Learn tx trees / Daml Shell / Canton console",
     "make shell, make canton-console. Verify who-sees-what in transaction trees.", ["daml"]),
]:
    make(t[0], t[1], priority=1, label_names=t[2], parent=e1, state=STATE_TODO)

print("E2 Week2 Core flow")
e2 = make("E2 — Week 2: Core Private Settlement Flow",
    "Agent→counterparty→atomic settlement with real Canton privacy.", priority=2, label_names=["daml","privacy"])
for t in [
    ("Design signatory/observer model (privacy architecture)",
     "#1 time-sink. Map exact info flow: agent proposes → Factor reviews privately → atomic settle. Wrong model = leak or block.", ["privacy","daml"]),
    ("SupplierAgent posts private Offer (visible only to Factor)", "", ["agent","privacy"]),
    ("FactorAgent reviews + accepts/counters via Daml choice", "", ["agent","daml"]),
    ("Atomic DvP: cash ↔ invoice claim in one Settlement batch",
     "Use Daml Finance Settlement (batches/instructions). Canton enforces all-or-nothing + sub-tx privacy.", ["daml","privacy"]),
    ("Verify privacy via tx-tree (A sees X, B sees Y, outsider nothing)",
     "This is the demo money-shot. Must be provable, not cosmetic.", ["privacy"]),
]:
    make(t[0], t[1], priority=2, label_names=t[2], parent=e2, state=STATE_TODO)

print("E3 Week3 Agent layer")
e3 = make("E3 — Week 3: Agent Autonomy + LLM Orchestration",
    "Turn the flow into an autonomous agent co-pilot.", priority=2, label_names=["agent"])
for t in [
    ("Agent decision loop: query state (PQS) → decide → submit command", "", ["agent"]),
    ("LLM orchestration: NL instruction → propose/validate/execute Daml choices",
     "'Factor invoice X privately if liquidity allows' → agent drives on-ledger choices.", ["agent"]),
    ("Conditional logic + multi-party coordination", "", ["agent","daml"]),
    ("Role-based UI for demo video (per-party private views)", "", ["demo"]),
]:
    make(t[0], t[1], priority=2, label_names=t[2], parent=e3, state=STATE_TODO)

print("E4 Week4 Submission")
e4 = make("E4 — Week 4: Submission Package",
    "Ship the proof-of-seriousness submission.", priority=3, label_names=["demo"])
for t in [
    ("Polish scenarios + exception handling", "", ["agent"]),
    ("Record 3-min video (private views + atomic settle + agent trace)",
     "Show multi-party privacy + real settlement + agent reasoning. Avoid 'LLM wrapper' look.", ["demo"]),
    ("Presentation deck (problem/market/why-Canton-privacy-essential)", "", ["demo"]),
    ("Clean documented public repo + live LocalNet demo link", "", ["demo","infra"]),
    ("Submit on Encode Club (repo+deck+video+live link)", "", ["demo"]),
]:
    make(t[0], t[1], priority=3, label_names=t[2], parent=e4, state=STATE_TODO)

print("\nDONE.")
