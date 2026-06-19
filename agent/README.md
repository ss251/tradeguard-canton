# TradeGuard Settlement Agent

A governed, off-chain reasoning agent for the TradeGuard Canton application.

## What it does

The agent connects to the Canton ledger (via the JSON Ledger API) as the
**Coordinator** party and continuously:

1. **Monitors** the ledger for trade lifecycle events — accepted trades awaiting
   settlement, delivery attestations, holding balances.
2. **Reasons** about whether each trade is *ready to settle*: are both legs funded?
   Is the delivery condition attested? Do amounts and instruments match?
3. **Proposes** a settlement plan when conditions are met — but it **never executes
   unilaterally**. It writes a `SettlementRecommendation` and waits.
4. **Defers to a human gate**: a human approver reviews the recommendation and
   authorizes (or rejects) it. Only on approval does the agent orchestrate the
   atomic batch settlement (lock → allocate → settle).
5. **Handles exceptions**: detects stale/expired conditions and recommends
   cancellation (releasing locks) instead of settling.

## Why this is "only on Canton"

The agent can only optimize/settle over data it is a stakeholder in. It computes
settlement plans over the Coordinator's view of the ledger — it cannot see (and
therefore cannot leak) counterparties' positions it isn't party to. The same agent
logic on a transparent chain would expose every position it reasons about.

## Architecture

```
  Canton ledger ──JSON API (7575)──┐
                                    │  read: proposals, accepted trades,
                                    │        attestations, holdings
                                    ▼
                          ┌──────────────────┐
                          │  ledger_client   │  thin HTTP client + JWT
                          ├──────────────────┤
                          │  reasoner        │  decides: settle / wait / cancel
                          ├──────────────────┤
                          │  agent (loop)    │  monitor → reason → recommend
                          ├──────────────────┤
                          │  governance gate │  human approve/reject
                          ├──────────────────┤
                          │  orchestrator    │  lock → allocate → settle (on approval)
                          └──────────────────┘
```

## Run

```
source ~/.tg-env.sh                      # daml + java on PATH
cd tradeguard && daml sandbox ...        # ledger on 6865
daml json-api ... --http-port 7575       # JSON API
python3 -m agent.cli status              # snapshot the ledger
python3 -m agent.cli watch               # run the monitoring loop
python3 -m agent.cli approve <id>        # human gate: approve a recommendation
```
