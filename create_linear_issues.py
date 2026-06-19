#!/usr/bin/env python3
"""Create TradeGuard issues in Linear (team THE, project TradeGuard) + wire dependency relations."""
import os, json, urllib.request

KEY = os.environ["LINEAR_API_KEY"]
TEAM = "4358a3b0-2202-4701-bb6b-feebdef13ff6"
PROJ = "a1070c3d-25a0-4766-bd9f-d95c77a75c85"
L = {
    "infra": "f4ce45c3-f2fd-48e0-a3d6-9a6dde588fed",
    "daml": "21860d5d-7e1e-400a-a750-410145db8ecc",
    "privacy": "c7509465-57e9-4404-91f7-297d1dbc4cc3",
    "agent": "793579cd-cea3-4dbc-95be-ecd079c42aad",
    "demo": "5564fbaf-e334-48c9-8d64-773d6dcb3aa0",
    "research": "5eb20011-a2e4-421b-a7ad-f1c01c45e64a",
}

def gql(query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request("https://api.linear.app/graphql", data=body,
        headers={"Authorization": KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        d = json.load(r)
    if d.get("errors"):
        raise RuntimeError(json.dumps(d["errors"], indent=2))
    return d["data"]

CREATE = """mutation($i: IssueCreateInput!){issueCreate(input:$i){success issue{identifier id title}}}"""

# (title, description, priority, [label keys]). Order = creation order; we key by short name.
ISSUES = [
 ("c1", "Checkpoint 1: create project + team on Encode platform (DUE Jun 21)",
  "MANDATORY checkpoint - miss it and you're cut. On the Encode platform: create project 'TradeGuard', add team, pick the Payments/Agentic track, submit stage-1 proof. Hard deadline Sun Jun 21.", 1, ["infra"]),
 ("wallet", "Get loop wallet on devnet.cport.io + send party ID to Jatin",
  "Log in to devnet.cport.io with loop wallet (auto-creates). Copy your party ID (top-right). Send it to Jatin on Canton Discord to join the 'encode hackathon' org. UNBLOCKS all deployment.", 1, ["infra"]),
 ("smoke", "Deploy hello-world Daml token to CPort DevNet (smoke test)",
  "Write a minimal token template, Build to a DAR, Deploy via CPort to the DevNet validator. Goal: 'something live on DevNet'. De-risks the toolchain end to end.", 2, ["infra","daml"]),
 ("damlfin", "Resolve OPEN Q: does daml-finance DAR deploy on CPort DevNet?",
  "Week-1 de-risk / architecture fork. If a daml-finance DAR uploads + runs on CPort -> Path B (settlement primitives). If not -> Path A (hand-roll templates). Ask in Canton Discord / docs Ask-Assistant.", 2, ["research","daml"]),
 ("skeleton", "Build TradeProposal -> Accept -> Trade (propose-accept skeleton)",
  "Core Daml. TradeProposal: signatory seller, observer buyer. Accept choice controlled by buyer creates Trade with BOTH as signatories. Add regulator as observer. The workshop's worked example = our skeleton.", 2, ["daml"]),
 ("dvp", "Implement atomic DvP: cash leg + asset leg in one choice body",
  "Both legs move inside ONE choice do-block = all-or-nothing. The Herstatt-risk killer and core differentiator. Cash leg = tokenized deposit/holding; asset leg = title/holding.", 2, ["daml","privacy"]),
 ("ui", "Role-based UI: Buyer / Seller / Regulator / Outsider views",
  "The demo money shot: same atomic tx, four different truths. Buyer sees its legs, seller its legs, regulator sees a valid settlement finalized, outsider sees nothing. queryContractId per party.", 3, ["demo","privacy"]),
 ("agent", "Off-chain governed AI agent: watch -> propose -> human gate",
  "Agent reads party-scoped ACS via PQS/JSON Ledger API, detects the delivery condition, PREPARES a settlement command, waits behind a human approval gate. NEVER moves money itself.", 3, ["agent"]),
 ("submit", "Submission package: repo + deck + 3-min video + live link",
  "Final deliverables via Encode platform (~Jul 12): public repo w/ README (problem, Why-Canton, architecture, setup), 8-12 slide deck, 3-min video, live product link.", 3, ["demo"]),
]

ids = {}
for key, title, desc, prio, labels in ISSUES:
    d = gql(CREATE, {"i": {
        "teamId": TEAM, "projectId": PROJ, "title": title,
        "description": desc, "priority": prio,
        "labelIds": [L[x] for x in labels],
    }})
    issue = d["issueCreate"]["issue"]
    ids[key] = issue["id"]
    print(f'{issue["identifier"]:>8}  {issue["title"]}')

# Dependency relations (blocks): parent blocks child
RELATIONS = [
    ("wallet", "smoke"), ("wallet", "damlfin"),
    ("smoke", "skeleton"), ("skeleton", "dvp"),
    ("dvp", "ui"), ("dvp", "agent"),
    ("ui", "submit"), ("agent", "submit"),
]
REL = """mutation($i: IssueRelationCreateInput!){issueRelationCreate(input:$i){success}}"""
print("\nDependencies (blocks):")
for a, b in RELATIONS:
    try:
        gql(REL, {"i": {"issueId": ids[a], "relatedIssueId": ids[b], "type": "blocks"}})
        print(f"  {a} blocks {b}")
    except Exception as e:
        print(f"  ! {a}->{b} failed: {str(e)[:80]}")

print("\nProject: https://linear.app/thescoho/project/tradeguard-canton-hackathon-38e7d5315650")
