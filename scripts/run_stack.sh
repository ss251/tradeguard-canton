#!/usr/bin/env bash
# TradeGuard — bring up the full local stack reliably.
# Usage: scripts/run_stack.sh   (idempotent; safe to re-run)
set -euo pipefail
source ~/.tg-env.sh
ROOT="$HOME/Developer/canton-hackathon"
DAML="$ROOT/tradeguard"
DAR="$DAML/.daml/dist/tradeguard-1.0.0.dar"

echo "[1/6] building DAR..."
( cd "$DAML" && daml build >/dev/null 2>&1 )

echo "[2/6] stopping any existing stack..."
for port in 6865 7575 8080; do
  lsof -nP -iTCP:$port -sTCP:LISTEN 2>/dev/null | awk 'NR>1{print $2}' | sort -u | xargs kill 2>/dev/null || true
done
sleep 3

echo "[3/6] starting Canton sandbox (6865)..."
( cd "$DAML" && nohup daml sandbox --port 6865 --dar "$DAR" >/tmp/tg-sandbox.log 2>&1 & )
# wait for ready
for i in $(seq 1 60); do
  if grep -q "Canton sandbox is ready" /tmp/tg-sandbox.log 2>/dev/null; then break; fi
  sleep 2
done
echo "      sandbox ready."

echo "[4/6] starting JSON Ledger API (7575)..."
( cd "$DAML" && nohup daml json-api --ledger-host localhost --ledger-port 6865 \
    --http-port 7575 --allow-insecure-tokens >/tmp/tg-jsonapi.log 2>&1 & )
for i in $(seq 1 40); do
  if curl -sS --max-time 3 http://localhost:7575/readyz >/dev/null 2>&1; then break; fi
  sleep 2
done
echo "      json-api ready."

echo "[5/6] seeding ledger (idempotent)..."
( cd "$DAML" && daml script --dar "$DAR" \
    --script-name TradeGuard.Init:initWithAccepted \
    --ledger-host localhost --ledger-port 6865 \
    --output-file accepted-result.json >/dev/null 2>&1 )
( cd "$DAML" && daml script --dar "$DAR" \
    --script-name TradeGuard.Init:initLedger \
    --ledger-host localhost --ledger-port 6865 \
    --output-file init-result.json >/dev/null 2>&1 )
# refresh tokens
for p in coordinator buyer seller regulator outsider; do
  python3 "$ROOT/scripts/make_token.py" $p >/dev/null 2>&1
done
echo "      seeded + tokens refreshed."

echo "[6/6] starting UI bridge (8080)..."
( cd "$ROOT/ui" && nohup python3 ui_server.py >/tmp/tg-ui.log 2>&1 & )
sleep 3
echo ""
echo "STACK UP:"
echo "  ledger gRPC : localhost:6865"
echo "  JSON API    : http://localhost:7575"
echo "  UI          : http://localhost:8080"
echo ""
echo "Next: scripts/demo.sh   (runs watch -> approve -> settle and verifies privacy)"
