#!/usr/bin/env bash
# Preflight for the demo video — verify the real network + DAR + parties are ready.
source ~/.tg-env.sh
export PATH="$HOME/.local/bin:$HOME/.dpm/bin:$PATH"
cd "$HOME/Developer/canton-hackathon"
ok=1
chk(){ if eval "$2" >/dev/null 2>&1; then echo "  ✓ $1"; else echo "  ✗ $1"; ok=0; fi; }

echo "TradeGuard demo preflight:"
chk "Canton network up (App Provider :3975)" "curl -s --max-time 5 http://localhost:3975/readyz"
chk "DPM toolchain on PATH" "command -v dpm"
chk "test DAR built" "test -s tradeguard-v3/test/.daml/dist/tradeguard-test-1.0.0.dar"
chk "real party file present" "test -s tradeguard-v3/real-init-result.json"
# package loaded on the network?
TOKEN=$(python3 scripts/make_token.py >/dev/null 2>&1; printf '')
chk "agent can read the ledger (v2)" "python3 -c \"import sys;sys.path.insert(0,'.');from agent.real_client import RealLedgerClient,load_real_parties as L;RealLedgerClient(L()['operator']).query('TradeGuard.Netting:Obligation')\""

if [ "$ok" = 1 ]; then
  echo "READY — run:  PACE=4 scripts/demo_video.sh"
else
  echo "NOT READY — bring up the stack first:"
  echo "  canton builder start                         # ~90s"
  echo "  (cd tradeguard-v3/main && dpm build) && deploy tradeguard-1.1.0 to :3975/:2975"
  echo "  python3 scripts/seed_real.py                 # allocate+grant 14 parties"
fi
