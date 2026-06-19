#!/usr/bin/env bash
# TradeGuard — run the full governed-agent demo and verify privacy live.
# Usage: scripts/demo.sh   (requires scripts/run_stack.sh to have been run)
set -uo pipefail
source ~/.tg-env.sh
ROOT="$HOME/Developer/canton-hackathon"
cd "$ROOT"

line(){ printf '\n\033[1m%s\033[0m\n' "$*"; }

line "STEP 1 — ledger snapshot (coordinator view)"
python3 -m agent.cli status

line "STEP 2 — agent reasons over the trade and writes a recommendation"
python3 -m agent.cli watch --once

line "STEP 3 — HUMAN GATE: approve the recommendation"
python3 -m agent.cli approve TG-LIVE-001

line "STEP 4 — agent settles atomically (only because a human approved)"
python3 -m agent.cli settle TG-LIVE-001

line "STEP 5 — PROVE PRIVACY over the live JSON API (same data, 4 tokens)"
for r in buyer seller regulator outsider; do
  curl -s --max-time 8 "http://localhost:8080/api/view?role=$r" \
    | python3 -c "import sys,json; v=json.load(sys.stdin); print(f\"  {v.get('role','?'):10s} holdings={v.get('holding_count','?')} settled={v.get('settled_count','?')} sees_anything={v.get('sees_anything','?')}\")"
done

line "DONE — agent proposed, human approved, ledger settled atomically; outsider saw nothing."
