#!/usr/bin/env bash
# TradeGuard — LIVE on the Canton Foundation's shared DevNet (5N Seaport validator).
#
# Proves the full product chain running on the REAL shared Canton network, not a local
# sandbox — the strongest possible "deployed on Canton" evidence. Every step is a real
# authenticated JSON Ledger API v2 call over OIDC M2M auth against the 5N validator.
#
#   1. connect + auth        (OIDC client-credentials -> live ledger-end offset)
#   2. seed a book           (multilateral obligations on DevNet)
#   3. maximal-netting settle (atomic; discharge all, move only residuals)
#   4. verify on-chain        (0 obligations remain; residual holdings exist)
#   5. on-ledger credit-limit REJECT (the ledger refuses an over-exposing plan)
#
# Prereqs: creds sourced from ~/.tradeguard/devnet.env, parties allocated
#   (agent.devnet_setup), tradeguard DAR uploaded to the validator, project venv.
#
# Usage:  source ~/.tradeguard/devnet.env && scripts/devnet_demo.sh
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -z "${TG_DEVNET_CLIENT_SECRET:-}" ]; then
  if [ -f "$HOME/.tradeguard/devnet.env" ]; then source "$HOME/.tradeguard/devnet.env"; fi
fi
: "${TG_DEVNET_CLIENT_SECRET:?source ~/.tradeguard/devnet.env first}"

export TG_NET=devnet
export TG_POLICY_BACKEND="${TG_POLICY_BACKEND:-rules}"
PY="${TG_PY:-.venv/bin/python}"

hr(){ printf '\n\033[1m%s\033[0m\n' "════════════════════════════════════════════════════════════════"; }
step(){ printf '\n\033[1;36m▶ %s\033[0m\n' "$1"; }

hr; echo "TradeGuard — LIVE on Canton DevNet (5N Seaport validator)"; hr

step "1. connect + OIDC M2M auth against the real 5N validator"
$PY -c "
from agent.real_client import RealLedgerClient, load_real_parties, HOST
p = load_real_parties(); op = RealLedgerClient(p['operator'])
print('   ledger:', HOST)
print('   live ledger-end offset:', op._ledger_end(), '(the real shared DevNet)')
print('   operator party:', p['operator'][:46], '...')
"

step "2. seed a confidential multilateral book on DevNet"
$PY -c "from agent.net_settle import seed_book; import json; print('  ', json.dumps(seed_book(dense=False)))"

step "3. maximal-netting settle (atomic: discharge all, move only the residual)"
$PY -c "
from agent.net_settle import settle_real; import json
r = settle_real()
print(f\"   gross {r['gross']} -> net {r['net']} ({r['efficiency_pct']}% netted); \"
      f\"{r['discharged']} discharged, {r['residuals']} residual transfer(s)\")
"

step "4. verify on-chain: obligations discharged, residual cash moved"
$PY -c "
from agent.real_client import RealLedgerClient, load_real_parties
p = load_real_parties(); op = RealLedgerClient(p['operator'])
obls = len(op.query('TradeGuard.Netting:Obligation'))
hold = sum(len(RealLedgerClient(p[f]).query('TradeGuard.Holding:Holding')) for f in ['firma','firmb','firmc'])
print(f'   obligations remaining: {obls} (0 = all discharged atomically)')
print(f'   residual holdings at firms: {hold}')
assert obls == 0, 'expected all obligations discharged'
"

step "5. on-ledger CREDIT-LIMIT reject (the ledger refuses, not just the agent)"
$PY -c "
from agent.net_settle import seed_book, attempt_credit_breach
seed_book(dense=False)
r = attempt_credit_breach()
assert r.get('rejected'), r
print('   REJECTED BY THE LEDGER:', r['constraint'])
print('   on-chain guard:', (r.get('ledger_error') or '')[:100], '...')
"

hr; printf '\033[1;32m✓ TradeGuard verified LIVE on the Canton Foundation DevNet\033[0m\n'; hr
echo "  real shared network · real OIDC auth · real atomic settlement · real on-ledger guards"
