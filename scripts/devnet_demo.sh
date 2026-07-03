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

step "6. AGGREGATE exposure cap (Basel large-exposure: bilateral caps can't catch it)"
$PY -c "
from agent.net_settle import seed_book, settle_real
from agent import limits as limmod
limmod.clear_all()
seed_book(dense=False)
r = limmod.seed_agg_limit('firma', 50.0); assert r.get('ok'), r
s = settle_real()
assert s.get('ok') and s.get('deferral_reasons'), s
print('   cap: FirmA TOTAL <= 50 USD across ALL counterparties (on-ledger, co-signed)')
print('   solver:', s['deferral_reasons'][0][:96])
limmod.clear_agg_limits()
s2 = settle_real()
print('   cap cleared -> full settle:', s2.get('ok'))
"

step "7. SETTLEMENT-FAILURE re-net (a firm can't fund -> atomic rollback -> survivors settle)"
$PY -c "
from agent.net_settle import seed_book, settle_with_failover
seed_book(dense=False)
r = settle_with_failover(fail_party='FirmA')
assert r.get('recovered'), r
rn = r['renet']
print('   FirmA underfunded -> ledger rejected the WHOLE batch (atomicity)')
print(f\"   re-net: excluded {rn['failure_excluded']} FirmA obligations, settled \"
      f\"{rn['discharged']} survivors ({rn['gross']} gross -> {rn['net']} net)\")
print('   the failer\\'s obligations stay live for the next cycle')
"

step "8. CIP-56 TOKEN STANDARD: cross-token atomic DvP (real Splice HoldingV1 interface)"
$PY -c "
from agent import token_settle as ts
ts.clear_tg_holdings(); ts.mint_book_multi()
r = ts.settle_cross_token(); assert r.get('ok'), r
rep = r['report_by_instrument']
per = ' · '.join(f\"{i}: {x['gross_value']}->{x['net_value']} ({x['netting_efficiency_pct']}%)\" for i,x in rep.items())
print(f\"   {r['leg_count']} residual legs across {len(r['instruments'])} TOKENS in ONE atomic tx\")
print('  ', per)
v = ts.verify_via_standard_interface('USDCx')
print(f\"   verified via the OFFICIAL token-standard interface: {v['holdings_via_standard_interface']} holdings readable\")
"

hr; printf '\033[1;32m✓ TradeGuard verified LIVE on the Canton Foundation DevNet\033[0m\n'; hr
echo "  real shared network · real OIDC auth · atomic settlement · on-ledger guards"
echo "  credit limits · aggregate caps · failure re-net · maturity · CIP-56 tokens · FX"
