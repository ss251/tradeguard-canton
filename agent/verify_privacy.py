# Copyright (c) 2026 TradeGuard. SPDX-License-Identifier: Apache-2.0
"""
Live privacy verification against the running ledger.

Proves the only-on-Canton property on a REAL ledger (not just in unit tests):
the same SettlementBatch / holdings are visible to stakeholders and the regulator,
and invisible to an outsider — enforced by the ledger + the party-scoped JWT.
"""
from ledger_client import Ledger

BATCH = "Settlement:SettlementBatch"
HOLDING = "Holding:Holding"
ATTEST = "Trade:DeliveryAttestation"
ALL_TEMPLATES = [BATCH, HOLDING, ATTEST]


def main():
    led = Ledger()
    assert led.ready(), "ledger not ready — start the sandbox first"
    P = led.parties()

    print("=" * 64)
    print("TradeGuard — LIVE privacy verification (batch TG-0042)")
    print("=" * 64)

    def visible(party_name):
        party = P[party_name]
        rows = led.query(party, ALL_TEMPLATES)
        by = {BATCH: 0, HOLDING: 0, ATTEST: 0}
        for r in rows:
            for t in ALL_TEMPLATES:
                if r.get("templateId", "").endswith(t):
                    by[t] += 1
        print(f"\n[{party_name}]  visible: batch={by[BATCH]} "
              f"holding={by[HOLDING]} attest={by[ATTEST]}")
        return by

    v_coord = visible("Coordinator")
    v_reg = visible("Regulator")
    v_seller = visible("Seller")
    v_buyer = visible("Buyer")
    v_out = visible("Outsider")

    print("\n" + "=" * 64)
    print("ASSERTIONS")
    print("=" * 64)
    checks = [
        ("Coordinator sees the batch (agent can act)",  v_coord[BATCH] >= 1),
        ("Regulator (observer) sees the batch",         v_reg[BATCH] >= 1),
        ("Seller sees their locked holding",            v_seller[HOLDING] >= 1),
        ("Buyer sees their locked holding",             v_buyer[HOLDING] >= 1),
        ("Coordinator sees the delivery attestation",   v_coord[ATTEST] >= 1),
        ("Outsider sees NO batch",                       v_out[BATCH] == 0),
        ("Outsider sees NO holdings",                    v_out[HOLDING] == 0),
        ("Outsider sees NO attestation",                 v_out[ATTEST] == 0),
    ]
    ok = True
    for label, passed in checks:
        if not passed:
            ok = False
        print(f"  [{'PASS' if passed else 'FAIL'}] {label}")

    print("\n" + ("ALL LIVE PRIVACY CHECKS PASSED" if ok else "SOME CHECKS FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
