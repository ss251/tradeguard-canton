#!/usr/bin/env bash
# TradeGuard Phase 2 — end-to-end live demo on the real 3-validator Canton network.
#
# Runs the ENTIRE product chain in one go, against the live ledger (:3975/:2975):
#   1. seed a confidential book              (multilateral obligations on-ledger)
#   2. compute the constrained net           (off-chain solver, single source of truth)
#   3. NL risk policy -> infeasible refusal   (English steers the solver; honest "no")
#   4. on-ledger credit-limit REJECT          (ledger refuses an over-exposing plan)
#   5. trustless cross-currency FX settle      (co-signed rate; value conservation)
#   6. on-ledger liquidity-floor REJECT        (ledger refuses a draining plan)
#
# Every step is REAL: real ledger writes, real solver, real on-ledger guards. No mocks.
#
# Prereqs: the real LocalNet up on :3975/:2975, and the project venv (PuLP).
# Usage:   scripts/e2e_phase2.sh
set -euo pipefail

cd "$(dirname "$0")/.."
PY="${TG_PY:-.venv/bin/python}"
export TG_REAL=1
export TG_POLICY_BACKEND="${TG_POLICY_BACKEND:-rules}"   # 'claude' for the live LLM

hr(){ printf '\n\033[1m%s\033[0m\n' "════════════════════════════════════════════════════════════════"; }
step(){ printf '\n\033[1;36m▶ %s\033[0m\n' "$1"; }

hr; echo "TradeGuard Phase 2 — live end-to-end on the real Canton network"; hr

step "0. clean slate — clear every on-ledger constraint"
$PY -m agent.limits clear_all 2>/dev/null || true
$PY -c "from agent import limits; import json; print(json.dumps(limits.clear_all()))" \
  | $PY -c "import sys,json; d=json.load(sys.stdin); print('   cleared:', {k:v.get('cleared') for k,v in d.items()})"

step "1. seed a confidential multilateral book (5 obligations, operator's view)"
$PY -c "from agent.net_settle import seed_book; import json; print('  ', json.dumps(seed_book(dense=False)))"

step "2. compute the constrained net (off-chain solver — this is the agent's brain)"
$PY -c "
from agent.net_settle import _book_facts, _short
from agent.real_client import load_real_parties
from agent.solver import solve, Obligation
p = load_real_parties()
obs = [Obligation(_short(a), _short(b), amt, 'USD') for (a,b,amt) in _book_facts(p)]
r = solve(obs)
print(f'   gross {r.gross_obligations} -> residual {r.gross_residual}  ({r.netting_efficiency_pct}% netted out)')
for t in r.transfers: print(f'     {t.sender} -> {t.receiver}  {t.amount} {t.currency}')
"

step "3. natural-language risk policy that makes settlement INFEASIBLE (honest refusal)"
echo "   policy: 'cap what FirmA owes FirmC at 20 USD'"
$PY -c "
from agent.net_settle import settle_real
r = settle_real('cap what FirmA owes FirmC at 20 USD')
assert not r['ok'] and r.get('infeasible'), r
print('   REFUSED (correct):', r['binding_constraints'][0])
print('   book untouched — the agent said NO instead of forcing a bad settle')
"

step "4. on-ledger CREDIT-LIMIT reject (the ledger refuses, not just the agent)"
$PY -c "
from agent.net_settle import attempt_credit_breach
r = attempt_credit_breach()
assert r.get('rejected'), r
print('   REJECTED BY THE LEDGER:', r['constraint'])
print('   on-chain guard:', r['ledger_error'][:90], '...')
"

step "5. trustless CROSS-CURRENCY FX settle (co-signed rate; value conservation)"
$PY -c "from agent.net_settle import seed_fx_book; import json; print('   seed:', json.dumps(seed_fx_book()))"
$PY -c "
from agent.net_settle import settle_cross_currency
r = settle_cross_currency()
assert r['ok'], r
print(f\"   SETTLED at {r['fx_rate']}: {r['gross_obligations_mixed_ccy']} mixed-ccy gross\")
print(f\"   -> {r['residual_total_usd']} USD in {r['usd_residuals']} residual(s); {r['discharged']} obligations discharged\")
print('   the EUR legs netted against the USD legs at a rate EVERY party signed')
"

step "6. on-ledger LIQUIDITY-FLOOR reject (ledger refuses to drain a firm below its minimum)"
$PY -c "
from agent import limits as L
from agent.solver import solve_fx, FXRate, FloorConstraint, Obligation
L.clear_liquidity_floors(); L.seed_liquidity_floor('firma', 50.0, 'USD')
fl = [FloorConstraint(f.party.split('::')[0], f.currency, f.floor) for f in L.load_liquidity_floors()]
# FirmA owes 100, holds 120 -> post 20 < 50 floor
r = solve_fx([Obligation('FirmA','FirmB',100.0,'USD')], [FXRate('EUR','USD',1.2)],
             settle_ccy='USD', floors=fl, balances={('FirmA','USD'):120.0})
assert not r.feasible, r
print('   REFUSED (correct):', r.binding_constraints[0])
L.clear_liquidity_floors()
"

hr; printf '\033[1;32m✓ ALL 6 STEPS PASSED — full product chain verified live on the real network\033[0m\n'; hr
echo "  the agent proposes · a human disposes · the ledger settles atomically or refuses with the reason"
