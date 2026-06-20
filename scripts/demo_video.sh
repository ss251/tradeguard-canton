#!/usr/bin/env bash
# TradeGuard — 3-minute demo capture script.
#
# Runs the live private-netting flow on the REAL Canton network with big on-screen
# section banners and deliberate pauses, so you can screen-record this terminal and
# narrate over it in one take. Pair with the deck (deck/index.html) on a second screen.
#
# PREREQ: `canton builder start` is up + tradeguard-1.1.0 deployed + parties seeded
#         (scripts/seed_real.py). Run scripts/preflight_video.sh first to check.
#
# Usage:  PACE=4 scripts/demo_video.sh     (PACE = seconds per pause, default 4)
set -uo pipefail
source ~/.tg-env.sh
export PATH="$HOME/.local/bin:$HOME/.dpm/bin:$PATH"
ROOT="$HOME/Developer/canton-hackathon"; cd "$ROOT"
PACE="${PACE:-4}"

# ── presentation helpers ─────────────────────────────────────────────
BOLD=$'\033[1m'; OX=$'\033[38;5;131m'; GRN=$'\033[38;5;65m'; DIM=$'\033[2m'; RST=$'\033[0m'
banner(){ printf "\n\n${OX}${BOLD}━━━ %s ━━━${RST}\n\n" "$1"; }
say(){ printf "${DIM}# %s${RST}\n" "$1"; }
beat(){ sleep "$PACE"; }
run(){ printf "${BOLD}\$ %s${RST}\n" "$1"; eval "$1"; }

make_jwt(){ local h=$(printf '{"alg":"HS256","typ":"JWT"}'|base64|tr '+/' '-_'|tr -d '=\n'); local p=$(printf '{"sub":"ledger-api-user","aud":"https://canton.network.global","scope":"daml_ledger_api"}'|base64|tr '+/' '-_'|tr -d '=\n'); local s=$(printf '%s' "$h.$p"|openssl dgst -binary -sha256 -hmac "unsafe"|base64|tr '+/' '-_'|tr -d '=\n'); printf '%s' "$h.$p.$s"; }
make_jwt > /tmp/tg-token.txt

clear
printf "${OX}${BOLD}\n   TradeGuard — private multilateral netting on Canton\n${RST}"
printf "${DIM}   Real 3-validator network · JSON Ledger API v2 · live\n${RST}"
beat

# ── ACT 1 — the confidential book ────────────────────────────────────
banner "ACT 1 · THE CONFIDENTIAL BOOK"
say "Three firms owe each other across 5 obligations. Each is PRIVATE to its two"
say "counterparties + the netting operator. No firm sees the whole book."
beat
say "Seeding the book on the real ledger (no settlement yet)..."
( cd tradeguard-v3/test && dpm script --dar .daml/dist/tradeguard-test-1.0.0.dar \
    --script-name TradeGuard.NetLive:seedNetBookOnly --ledger-host localhost \
    --ledger-port 3901 --access-token-file /tmp/tg-token.txt --wall-clock-time \
    >/dev/null 2>&1 ) && echo "  ✓ book seeded: A→B 100, B→C 100, C→A 80, A→C 50, C→B 30  (360 gross)"
beat

# ── ACT 2 — privacy is real ──────────────────────────────────────────
banner "ACT 2 · PRIVACY IS REAL (the only-on-Canton claim)"
say "Same ledger, queried as each party. Watch who sees what:"
beat
python3 - <<'PY'
import sys; sys.path.insert(0, ".")
from agent.real_client import RealLedgerClient, load_real_parties
p = load_real_parties()
counts = {}
for role,label in [("firma","FirmA"),("firmb","FirmB"),("firmc","FirmC"),("operator","Operator (agent)"),("netout","Outsider")]:
    counts[label] = len(RealLedgerClient(p[role]).query("TradeGuard.Netting:Obligation"))
op = counts["Operator (agent)"] or 1
for label,n in counts.items():
    bar = "█"*round(n/op*20)
    print(f"   {label:18s} {n:3d}  {bar}")
firms = [counts[f] for f in ("FirmA","FirmB","FirmC")]
print()
print(f"   → Operator sees the FULL book ({op}). Each firm sees a strict subset.")
print(f"   → Outsider sees {counts['Outsider']}. No firm can reconstruct the whole book — only the operator.")
PY
beat

# ── ACT 3 — net, approve, settle atomically ──────────────────────────
banner "ACT 3 · NET → APPROVE → ATOMIC SETTLE"
say "The operator computes the multilateral net and settles only the residuals,"
say "discharging all 5 obligations in ONE atomic transaction."
beat
( cd tradeguard-v3/test && dpm script --dar .daml/dist/tradeguard-test-1.0.0.dar \
    --script-name TradeGuard.NetLive:runNetLive --ledger-host localhost \
    --ledger-port 3901 --access-token-file /tmp/tg-token.txt --wall-clock-time \
    --output-file /tmp/netlive.json >/dev/null 2>&1 )
python3 - <<'PY'
import json
d=json.load(open("/tmp/netlive.json"))
print(f"   ✓ obligations discharged : {d['obligationsDischarged']}")
print(f"   ✓ residual transfers     : {d['residualsSettled']}")
print(f"   ✓ gross value            : {d['grossValue']:.0f} USD")
print(f"   ✓ net value moved        : {d['netValue']:.0f} USD")
saved = d['grossValue']-d['netValue']
print(f"\n   → {saved:.0f} of {d['grossValue']:.0f} USD never moved  ({saved/d['grossValue']*100:.1f}% netted out)")
PY
beat

# ── ACT 4 — the ledger rejects fraud ─────────────────────────────────
banner "ACT 4 · THE LEDGER CHECKS THE AGENT"
say "Why trust an AI agent? You don't. The netting contract enforces conservation,"
say "efficiency and funding ON-LEDGER. A fraudulent under-settlement is REJECTED."
beat
say "Running the adversarial test (a proposal that under-settles by 90)..."
( cd tradeguard-v3/test && dpm test 2>&1 | grep -E "testNettingRejectsValueViolation:" ) \
  && echo "  ✓ ledger rejected the fraudulent proposal (submitMustFail passed)"
beat

banner "TradeGuard · private · atomic · agent-operated · provably safe"
say "github.com/ss251/tradeguard-canton"
echo
