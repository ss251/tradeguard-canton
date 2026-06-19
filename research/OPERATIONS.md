# Canton Hackathon — Operations & Build Reality (from workshop transcripts)

> Supersedes guesses in SYNTHESIS.md where they conflict. Source: Intro video (Anthony/Encode + Shre/Digital Asset) + Canton Tech Deep Dive (Jatin/Canton Foundation).

## TIMELINE (hard)
| Date | Milestone | Notes |
|---|---|---|
| Mon **15 Jun** | Launch | 4-week program |
| **Sun 21 Jun** | **Checkpoint 1: create project + team on platform** | MANDATORY — miss checkpoints = cut. Must also submit proof on stage 1. |
| Mon 23 Jun 2pm | Canton ecosystem overview workshop | — |
| **Sun 28 Jun** | Checkpoint 2: ideation | mid-hackathon |
| **~12 Jul** | Final submission | "kicked out if you don't submit by the 12th" |
| After | Finale — best teams pitch live for overall prizes | — |

**Checkpoints are accountability, not elimination** — you're only cut for being disorganized (missing checkpoints) or not submitting. Not battle-royale on quality.

## PRIZE (resolved)
**$7,000 total pool, split across the best projects, across all tracks.** ("five" = theme count / garbled, not 5×$7k). Target = top overall, span ≥1 theme.

## DEPLOYMENT PATH — USE THIS, NOT cn-quickstart LocalNet
The hackathon's intended path is **SEAPORT** (transcript garbled it as "CPort"; the tool is Seaport,
the wallet is Canton Loop. `cport.io` does NOT exist). Guide: https://github.com/Jatinp26/Seaport-Guide
1. **Get DevNet wallet** at **https://devnet.cantonloop.com** → copy your **Party ID** (`abc123::122...34a`).
2. **Send Party ID to Jatin / organizer on Discord** → they INVITE you to the hackathon **org** by Party ID (no join button; pending invite applies on first sign-in).
3. **Log in** at **https://app.devnet.seaport.to** with the Loop wallet → **org switcher** (top-left) → your team → shared **`5n sandbox`** validator pre-configured.
4. In Seaport (web IDE): New Blank Project OR template ("DAML Intro Data") OR Connect GitHub (import a repo / DAR built locally w/ **DPM**).
5. **Build Project** → produces a `.dar` (under Builds folder). **Deploy** → push DAR to `5n sandbox`. Create live contracts + exercise choices in-browser.
6. Two MODES: **Personal** (private) vs **Org** (hackathon team — USE THIS to deploy). Tabs are mode-scoped.
7. **Minimum viable bar: "something live on DevNet."**

### ⚠️ OPEN TECHNICAL DECISION (week-1 de-risk)
Bare Seaport Daml = simple, guaranteed deploy, but no financial primitives.
daml-finance (settlement engine, holdings, instruments) = richer/institutional, but lives in libraries you compile locally via DPM.
**Question to resolve:** does a daml-finance-based DAR upload + run cleanly on the Seaport `5n sandbox` DevNet validator?
- If YES → use daml-finance for credible atomic DvP + settlement.
- If NO / too risky → hand-roll minimal templates (the workshop's propose-accept trade pattern already gets us 80% there).
Resolve via: Canton docs (docs.canton.network), Canton GitHub quick start, forum.canton.network, or just ask in Discord / the docs "Ask Assistant" AI.

## DAML MENTAL MODEL (from Jatin's live build — confirmed)
- **template** = definition w/ params (the `with` fields). Many templates = a contract/app.
- **party** = on-ledger identity (NOT an address). You get a party ID from loop wallet.
- **signatory** = owner/authorizer; must sign every tx on the contract.
- **observer** = can see, cannot act (e.g., a **regulator** — Jatin's exact example).
- **controller** = who may exercise a given choice.
- **choice** = executable action (e.g., `transfer`, `accept`, `burn`). Returns a ContractId or `()` for void.
- `do create X with ...` = creates new contract, archives the old (state transition).
- **ensure** = precondition guard (e.g., `ensure info.quantity > 0.0`).
- **Proof of stakeholders** = THE privacy model: only parties named in a contract (signatory/observer) see it. A non-party ("Anthony") sees *nothing*. Sub-transaction privacy is native at the smart-contract level — Canton is the only L1 doing this.

### The workshop's worked example == our TradeGuard skeleton
Jatin taught a **Trade Proposal**: `seller` = signatory, `buyer` = observer, choice `accept` controlled by `buyer` → `do create Trade with seller buyer asset price`. Seller proposes, buyer sees + accepts, Trade contract is created, both done. **This is exactly the propose-accept DvP pattern TradeGuard extends.** Regulator-as-observer = our selective-disclosure pane. The curriculum hands us the bones.

## ARCHITECTURE (global synchronizer)
- Network of networks: every validator runs its own sub-network (a slice of the ledger), privacy-first/isolated.
- **Global Synchronizer** sees NOTHING — gets cryptographically encrypted messages; only sequences/orders/batches w/ BFT to guarantee **native atomicity across validators**. (e.g., US bank ↔ Korea/Japan bank settle atomically.)
- Selective disclosure = need-to-know, like logging into chase.com — you see only your data.

## RESOURCES (concrete)
- **docs.canton.network** — choose-your-own-adventure modules (zero-blockchain / from-Ethereum-Solana / no-code architect paths). Has **"Ask Assistant"** AI button (top) — use for plain-text Q's.
- **Canton DevHub** (devhub / "devub.[canton].foundation") — Lego-block tool catalog (AI tools, IDEs, SDKs, indexers).
- **Canton Network GitHub (git devs)** — hackathon resources, tutorials, FAQs, **Canton quick start** (full-stack).
- **forum.canton.network** — app-development section, active ecosystem help.
- **Discord** (run by Encode) — tech support + where you send party ID to Jatin.
- **CPort** — `devnet.cport.io` (deploy). **DPM** — local Daml compile.

## AI POLICY
AI tools explicitly **encouraged**. BUT: code must be your own, no plagiarism, prizes rescinded for malpractice. Agentic transactions explicitly flagged as "a lot of interest" for Track 3 → governed-automation positioning is welcome, not a liability.

## INSTITUTIONAL PROOF POINTS (for the pitch)
Goldman Sachs, DTCC, JP Morgan are building on Canton. Cite for credibility.

## IMMEDIATE ACTIONS (next 72h, before 21 Jun)
1. **Create project + team on the Encode platform** (Checkpoint 1) — pick a working title, choose the Payments/Agentic track (or whichever we lock). Submit stage-1 proof.
2. **Get loop wallet on `devnet.cport.io`**, copy party ID, send to Jatin on Discord → join "encode hackathon" org. Unblocks deployment.
3. **Resolve the daml-finance-on-CPort question** (docs/forum/Discord/Ask-Assistant).
4. Skim docs.canton.network "from Ethereum/Solana" module + the Canton quick start repo.
