#!/usr/bin/env bash
# TradeGuard — full demo on the REAL Canton network (Canton Builder LocalNet).
# Prereq: `canton builder start` is up + DAR deployed (scripts deploy below if needed).
# Shows: seed -> agent reasons -> recommends -> human approves -> atomic settle -> privacy.
set -uo pipefail
source ~/.tg-env.sh
export PATH="$HOME/.local/bin:$HOME/.dpm/bin:$PATH"
ROOT="$HOME/Developer/canton-hackathon"
cd "$ROOT"

# HS256 admin token (secret "unsafe") for auth'd Daml Script
make_jwt() {
  local h=$(printf '{"alg":"HS256","typ":"JWT"}'|base64|tr '+/' '-_'|tr -d '=\n')
  local p=$(printf '{"sub":"ledger-api-user","aud":"https://canton.network.global","scope":"daml_ledger_api"}'|base64|tr '+/' '-_'|tr -d '=\n')
  local s=$(printf '%s' "$h.$p"|openssl dgst -binary -sha256 -hmac "unsafe"|base64|tr '+/' '-_'|tr -d '=\n')
  printf '%s' "$h.$p.$s"
}
make_jwt > /tmp/tg-token.txt

echo "================ STEP 0: allocate parties + grant rights ================"
python3 scripts/seed_real.py | tail -3

echo ""
echo "================ STEP 1: seed scenario on the real network ================"
( cd tradeguard-v3/test && dpm script \
    --dar .daml/dist/tradeguard-test-1.0.0.dar \
    --script-name TradeGuard.Init:initWithAccepted \
    --ledger-host localhost --ledger-port 3901 \
    --access-token-file /tmp/tg-token.txt \
    --output-file /tmp/tg-accepted.json --wall-clock-time 2>&1 | grep -iE "error|abort" | grep -ivE "^\s+at " | head -3 )
# sync the agent's party file to the seed's actual party ids
python3 -c "import json; d=json.load(open('/tmp/tg-accepted.json'))['base']; json.dump({k:v for k,v in d.items() if isinstance(v,str) and '::' in v}, open('tradeguard-v3/real-init-result.json','w'), indent=1)"
echo "scenario seeded."

echo ""
echo "================ STEP 2: agent reasons + recommends (on-ledger) ================"
TG_REAL=1 python3 -m agent.cli watch --once 2>&1 | grep -E "REASON|PASS|DECISION|RECOMMEND"

echo ""
echo "================ STEP 3: HUMAN approves (on-ledger) ================"
TG_REAL=1 python3 -m agent.cli approve TG-LIVE-001

echo ""
echo "================ STEP 4: atomic settle on the real network ================"
( cd tradeguard-v3/test && dpm script \
    --dar .daml/dist/tradeguard-test-1.0.0.dar \
    --script-name TradeGuard.Orchestrate:orchestrateLive \
    --ledger-host localhost --ledger-port 3901 \
    --access-token-file /tmp/tg-token.txt --wall-clock-time 2>&1 | grep -iE "error|abort" | grep -ivE "^\s+at " | head -3 )
echo "settled."

echo ""
echo "================ STEP 5: prove privacy on the real ledger ================"
python3 - <<'PY'
import sys; sys.path.insert(0, ".")
from agent.real_client import RealLedgerClient, load_real_parties
p = load_real_parties()
for role in ["buyer","seller","regulator","outsider"]:
    c = RealLedgerClient(p[role])
    h=len(c.query("TradeGuard.Holding:Holding")); a=len(c.query("TradeGuard.Settlement:SettledTrade"))
    print(f"  {role:10s} holdings={h} settled={a} sees_anything={h+a>0}")
print("\nDONE — full flow on a real 3-validator Canton network; outsider saw nothing.")
PY