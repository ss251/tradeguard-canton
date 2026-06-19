#!/usr/bin/env bash
# Create TradeGuard issues in Linear team THE, project TradeGuard. Prints identifiers + UUIDs.
set -e
TEAM="4358a3b0-2202-4701-bb6b-feebdef13ff6"
PROJ="a1070c3d-25a0-4766-bd9f-d95c77a75c85"
# label ids
L_infra="f4ce45c3-f2fd-48e0-a3d6-9a6dde588fed"
L_daml="21860d5d-7e1e-400a-a750-410145db8ecc"
L_privacy="c7509465-57e9-4404-91f7-297d1dbc4cc3"
L_agent="793579cd-cea3-4dbc-95be-ecd079c42aad"
L_demo="5564fbaf-e334-48c9-8d64-773d6dcb3aa0"
L_research="5eb20011-a2e4-421b-a7ad-f1c01c45e64a"

create() {
  local title="$1" desc="$2" prio="$3" labels="$4"
  curl -s -X POST https://api.linear.app/graphql \
    -H "Authorization: $LINEAR_API_KEY" -H "Content-Type: application/json" \
    -d "$(python3 -c "
import json,sys
print(json.dumps({
  'query':'mutation(\$i: IssueCreateInput!){issueCreate(input:\$i){success issue{identifier id title}}}',
  'variables':{'i':{
     'teamId':'$TEAM','projectId':'$PROJ',
     'title':sys.argv[1],'description':sys.argv[2],
     'priority':int(sys.argv[3]),
     'labelIds':sys.argv[4].split(',') if sys.argv[4] else []
  }}
}))
" "$title" "$desc" "$prio" "$labels")" | python3 -c "import sys,json; d=json.load(sys.stdin); i=d['data']['issueCreate']['issue']; print(i['identifier'], i['id'], '|', i['title'])"
}

create "Checkpoint 1: create project + team on Encode platform (DUE Jun 21)" "MANDATORY checkpoint — miss it and you're cut. On the Encode platform: create project 'TradeGuard', add team, pick the Payments/Agentic track, submit stage-1 proof. Hard deadline Sun Jun 21." 1 "$L_infra"
create "Get loop wallet on devnet.cport.io + send party ID to Jatin" "Log in to devnet.cport.io with loop wallet (auto-creates). Copy your party ID (top-right). Send it to Jatin on Canton Discord to be added to the 'encode hackathon' org. UNBLOCKS all deployment." 1 "$L_infra"
create "Deploy hello-world Daml token to CPort DevNet (smoke test)" "Write a minimal token template, Build to a DAR, Deploy via CPort to the DevNet validator. Goal: 'something live on DevNet'. De-risks the whole toolchain end to end." 2 "$L_infra,$L_daml"
create "Resolve OPEN Q: does daml-finance DAR deploy on CPort DevNet?" "Week-1 de-risk / architecture fork. If a daml-finance-based DAR uploads + runs on CPort DevNet -> Path B (use settlement primitives). If not/too risky -> Path A (hand-roll templates). Ask in Canton Discord / docs Ask-Assistant." 2 "$L_research,$L_daml"
create "Build TradeProposal -> Accept -> Trade (propose-accept skeleton)" "Core Daml. TradeProposal: signatory seller, observer buyer. Accept choice controlled by buyer creates Trade with BOTH as signatories. Add regulator as observer for selective disclosure. This is the workshop's worked example = our skeleton." 2 "$L_daml"
create "Implement atomic DvP: cash leg + asset leg in one choice body" "Both legs move inside ONE choice do-block = all-or-nothing. The Herstatt-risk killer and the core differentiator. Cash leg = tokenized deposit/holding; asset leg = title/holding." 2 "$L_daml,$L_privacy"
create "Role-based UI: Buyer / Seller / Regulator / Outsider views" "The demo money shot: same atomic tx, four different truths. Buyer sees its legs, seller its legs, regulator sees a valid settlement finalized, outsider sees nothing. Visual proof of selective disclosure. Use queryContractId per party." 3 "$L_demo,$L_privacy"
create "Off-chain governed AI agent: watch -> propose -> human gate" "Agent reads party-scoped ACS via PQS/JSON Ledger API, detects the delivery condition, PREPARES a settlement command, then waits behind a human approval gate. NEVER moves money itself. Authorization stays with Daml signatories." 3 "$L_agent"
create "Submission package: repo + deck + 3-min video + live link" "Final deliverables via Encode platform (~Jul 12): public repo w/ README (problem, Why-Canton, architecture diagram, setup), 8-12 slide deck, 3-min video (problem -> privacy visual -> live demo -> impact), live product link." 3 "$L_demo"
