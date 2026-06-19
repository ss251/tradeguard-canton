# THE CANTON BUILD BIBLE
### A complete living reference: finance -> DeFi/TradFi -> Canton -> Daml -> the TradeGuard build

> Built for a crypto-native builder who needs to understand finance AND the Daml/Canton
> tech stack from first principles. Self-contained. When a word confuses you, check the
> INDEX at the very bottom -- it points to the exact section.
>
> PARTS:
>   I.   Finance Foundations (the atoms + the next layer)
>   II.  The DeFi <-> TradFi Bridge
>   III. Canton Architecture
>   IV.  Daml -- the complete language reference  (the technical core of the build)
>   V.   Canton Dev Toolchain & Deployment
>   VI.  The TradeGuard Build -- how every concept maps onto real code
>   VII. Glossary / Quick Index

================================================================================
# PART I -- FINANCE FOUNDATIONS
================================================================================

## I.0 -- What all finance is
Moving value (1) across people, (2) across time, and (3) managing the trust gap.
- across people -> payments, trading, settlement
- across time   -> lending, borrowing, saving
- trust gap     -> collateral, custody, clearing, regulation (the intermediaries)
Every term below is one of these three verbs in a costume.

--------------------------------------------------------------------------------
## I.1 -- THE ATOMS (smallest building blocks, each with a DeFi twin)
--------------------------------------------------------------------------------

### IOU = "I Owe You"
A written promise/claim that someone owes you value. The most primitive instrument.
- Napkin: "I owe you $20 - Dave" = an IOU. Not the $20; a *claim on* $20.
- BIG IDEA: almost all finance is IOUs in costume. Bond = tradable IOU. Bank balance = bank's
  IOU to you. Dollar bill = govt IOU. USDC = Circle's IOU.
- DeFi twins: USDC, aUSDC (Aave's IOU for your deposit), wETH/wBTC (wrapper's IOU).
- 2-sec: IOU = a CLAIM ON value, not the value itself.

### Claim
The formal word for "a right to receive value from someone." A bond is a claim on its issuer.

### Collateral
Valuable thing locked up as a promise you'll repay. Pawn shop watch. 

### Overcollateralization
Lock up MORE value than you borrow (the "over" = >100%).
- Aave: borrow $100 USDC -> deposit $150 ETH = 150% = overcollateralized.
- WHY: collateral value MOVES and code trusts no one. The extra $50 is a SAFETY BUFFER. If it
  erodes toward your debt you get LIQUIDATED (force-sold) before the buffer is gone.
- = the buffer that makes TRUSTLESS lending safe (no credit check).
- TradFi twins: haircut, margin call; REPO is literally this.

### Liquidation / Margin call
Buffer failed. DeFi "liquidation" = force-sell collateral. TradFi "margin call" = "post more or
we sell." Same event.

### Haircut
TradFi's conservative discount on collateral ("$150 of bonds counts as $140"). The $10 = haircut.

### Bond
A loan chopped into a tradable paper. Buy a bond = YOU are the lender.
- Apple issues: you pay $1000 (PRINCIPAL/face value); Apple pays 5%/yr = $50 (COUPON); after
  10 yrs (MATURITY) returns your $1000.
- DeFi twin: an Aave deposit you can SELL. Borrower = ISSUER.
- TRADABLE: sell early on the SECONDARY market (primary = first issuance).
- THE SEESAW: bond prices move OPPOSITE to rates. Hold 5% bond, new bonds pay 7% -> drop your
  price to sell. Rates up -> price down. (Most important fact in fixed income.)
- "Fixed income" = the whole bond universe (income fixed in advance).
- Biggest market on Earth (~$130T). Govts fund via bonds (US Treasuries = safest, the benchmark).
  Tokenized treasuries (bonds on-chain) = hottest RWA on Canton.

### THE FUNDAMENTAL FORK: own vs lend
- EQUITY (stock) = you OWN a slice. Upside if it grows. Owner. Riskier; paid last if firm fails.
- BOND/DEBT = you LENT. Fixed payments, no upside beyond interest. Creditor. Safer; paid first.
- "Own it or lend to it" is the deepest fork in finance.

### Coupon / Principal / Maturity / Yield
Principal = amount lent. Coupon = periodic interest. Maturity = when principal returns.
Yield = your return % (DeFi: APY).

### Issuer / Creditor / Debtor
Issuer = creates instrument & owes (Apple/govt). Creditor = is owed (you). Debtor = owes.

--------------------------------------------------------------------------------
## I.2 -- THE NEXT LAYER (markets, trading, instruments, money)
--------------------------------------------------------------------------------

### Equity / Stock (the "own" side, in full)
A share = a fractional ownership slice of a company. Returns come two ways: price goes up
(capital gain) and/or DIVIDENDS (a cut of profits paid to owners; equity's version of a coupon,
but NOT guaranteed). Shareholders vote and own the upside, but are last in line if the company
dies. DeFi twin: a governance token with revenue share.

### Market / Exchange / Order book
A market = where buyers and sellers meet. An EXCHANGE = an organized public market (NYSE, Nasdaq).
The ORDER BOOK = the live list of buy orders (BIDS) and sell orders (ASKS/OFFERS).
- BID = highest price a buyer will pay. ASK = lowest a seller will accept.
- SPREAD = ask - bid (the gap). Tighter spread = more LIQUID market.
- DeFi twin: an order book DEX; Uniswap replaces the book with an AMM formula.

### Market maker / Liquidity / Slippage
MARKET MAKER = a firm that always quotes both a bid and an ask, holding INVENTORY so you can
always trade. They earn the SPREAD. LIQUIDITY = how easily you can trade without moving the price.
SLIPPAGE = the price moving against you because your order is big vs the available liquidity.
DeFi twins: LPs (liquidity providers) = market makers; the AMM curve = the quote; slippage is the same word.

### OTC (Over-the-Counter)
A trade negotiated PRIVATELY and bilaterally, off any exchange. No public order book. Most
institutional volume is OTC. Inherently a privacy story -> a core Canton use case. DeFi twin:
an OTC desk / RFQ ("request for quote") instead of a public pool.

### Spread / Bid-Ask / Mid
Mid = (bid+ask)/2, the "fair" reference price. "Crossing the spread" = paying the ask to buy now
(taking liquidity) vs posting a bid and waiting (making liquidity). Maker vs taker -- same as DeFi.

### Derivative (value DERIVED from something else)
A contract whose value comes from an underlying asset/rate/event. The four you must know:
- FORWARD = private agreement to buy/sell an asset at a set price on a future date. (OTC.)
- FUTURE = a standardized, exchange-traded forward (cleared by a CCP).
- OPTION = the RIGHT but not the obligation to buy (CALL) or sell (PUT) at a set STRIKE price by
  a date. You pay a PREMIUM for the right. DeFi twin: on-chain options protocols.
- SWAP = exchange one stream of cash flows for another. Most common: INTEREST-RATE SWAP (trade
  fixed-rate payments for floating-rate). FX SWAP = trade currency streams. Governed by ISDA contracts.
Why they exist: HEDGING (insurance against price moves) and SPECULATION (leveraged bets).

### Repo (repurchase agreement) -- deep
Sell an asset now + agree to buy it back later at a slightly higher price.
- Economically = a COLLATERALIZED SHORT-TERM LOAN. The asset is collateral; the price gap is the
  interest (the "repo rate"). Haircut applies.
- The cash lender is safe (holds your bond); the borrower gets cheap short-term funding.
- TRILLIONS/day -- the plumbing of institutional funding. The Fed steers rates via repo markets.
- Broadridge's Canton repo platform (DLR) = THE flagship Canton success story. Know it cold.
- DeFi twin: collateralized lending (Aave), but for institutions and short-dated.

### Leverage / Margin / Short selling
LEVERAGE = using borrowed money to amplify a position (and the risk). MARGIN = the collateral you
post to a broker to use leverage; a MARGIN CALL demands more if it moves against you. SHORT SELLING
= borrow an asset, sell it now, hope to buy it back cheaper later (a bet it falls). DeFi twins:
perps, leveraged vaults, borrowing to short.

### Securitization
Bundle many small IOUs (mortgages, car loans, invoices) into one big tradable instrument and sell
slices. Turns illiquid loans into tradable securities. (2008's villain when done on bad mortgages.)
DeFi twin: tokenizing a pool of receivables.

### Money markets / Credit / Interest rates
MONEY MARKET = where short-term borrowing/lending happens (repo, T-bills). CREDIT = lending in
general; "credit risk" = chance the borrower doesn't pay. INTEREST RATE = the price of money over
time. The CENTRAL BANK (the Fed) sets the base rate; everything else is priced as "base rate +
a spread for risk." The YIELD CURVE = interest rates plotted across maturities (short vs long).

### FX (Foreign Exchange)
Trading one currency for another. The biggest market by volume (~$7T/day). Settlement here is
where Herstatt risk was born; PvP (Payment vs Payment) is the FX version of atomic DvP.

### Tokenized deposit vs Stablecoin
Both are on-chain cash. STABLECOIN (USDC) = a claim on a private issuer's reserves. TOKENIZED
DEPOSIT = an actual regulated bank deposit represented on-chain (a claim on a bank, inside the
banking system). Institutions prefer tokenized deposits for legal/regulatory reasons. Likely the
"cash leg" in TradeGuard.

### RWA (Real-World Asset)
Any off-chain asset represented on-chain: tokenized treasuries, real estate, invoices, deposits,
gold. The bridge between TradFi value and on-chain settlement. A whole hackathon track.

### Treasury operations
How an organization manages its OWN cash: where it sits, moving between subsidiaries/currencies,
ensuring each entity has enough liquidity ("trapped liquidity" = stuck in the wrong place).
DeFi twin: DAO treasury management.

### Settlement vocabulary (the obsession)
- SETTLEMENT = the final, irreversible exchange of value. The moment everything exists to protect.
- CLEARING = the prep between trade and settlement (confirm, net, reserve).
- FINALITY = once settled, cannot be reversed. Legal in banking; probabilistic on most chains;
  instant/legal on Canton.
- T+2 / T+1 / T+0 = settle N business days after trade. Industry racing to T+0/atomic.
- NETTING = settle the NET difference, not each gross obligation. Multilateral = many parties.
- DvP (Delivery vs Payment) = asset leg + cash leg settle together or neither = atomic swap in a
  suit. PvP = the FX (currency-for-currency) version.

--------------------------------------------------------------------------------
## I.3 -- RISK (the language finance THINKS in)
--------------------------------------------------------------------------------
- COUNTERPARTY / CREDIT risk: the other side defaults generally.
- SETTLEMENT risk (Herstatt, 1974): you delivered your leg, they didn't deliver theirs -> exposed
  in the gap. ATOMIC DvP makes this impossible. *TradeGuard's #1 claim.* (Distinct from counterparty risk.)
- LIQUIDITY risk: can't get cash when/where needed even if solvent.
- OPERATIONAL risk: the process breaks (manual error, fraud, system failure).
- SYSTEMIC risk: one failure cascades through the connected system (2008).
- MARKET risk: prices simply move against your position.

================================================================================
# PART II -- THE DeFi <-> TradFi BRIDGE  (print on eyelids)
================================================================================
Same machine, different names. When a judge says the right column, your brain whispers the left.

| DeFi (you know) | TradFi (their world) | shared job |
|-----------------|----------------------|-----------|
| wallet address | account @ custodian / PARTY | who you are |
| token (ERC-20) | security / instrument | the tradable thing |
| stablecoin (USDC) | tokenized deposit / cash | the cash leg |
| Uniswap / DEX | exchange / market maker / OTC desk | where you trade |
| liquidity pool | market maker's inventory | who takes the other side |
| LP / liquidity provider | market maker | quotes both sides |
| Aave lending | money market / repo / credit desk | lending across time |
| overcollateralization | margin / collateral / haircut | trust buffer |
| liquidation | margin call / default mgmt | buffer fails |
| yield / APY | interest / coupon / dividend | reward for capital |
| gas fee | fee / spread / commission | cost to transact |
| ATOMIC SWAP | DvP (Delivery vs Payment) | both legs or neither |
| block finality | settlement finality | truly "done" |
| public mempool | order flow (kept PRIVATE) | where leakage happens |
| MEV / front-running | front-running / info leakage | the predator |
| smart contract | legal contract / ISDA | the rulebook |
| composability | interoperability across institutions | snapping pieces |
| DAO treasury | corporate treasury | managing org cash |
| TVL | AUM (assets under management) | the scale flex |
| governance token | equity / share | ownership + a say |
| wrapping a token | tokenizing an RWA | put real thing on ledger |

WHY TRADFI IS HEAVIER: DeFi shares ONE ledger -> settlement is automatic/atomic -> no middlemen.
TradFi has a private DB per institution -> bridging them needs custodians, clearing houses/CCPs,
and slow T+2 settlement systems. Every intermediary exists ONLY because there is no shared ledger.
=> Canton = a shared ledger for institutions -> collapse intermediaries like DeFi, WITHOUT going public.

================================================================================
# PART III -- CANTON ARCHITECTURE
================================================================================

## III.1 -- The one-paragraph thesis
DeFi gets trust via RADICAL TRANSPARENCY (everything public) -> cost: information leakage / MEV.
TradFi REQUIRES privacy (a $2B bond sale can't be announced = market impact). These are OPPOSED:
you can't put Uniswap on Wall St (too public) or go back to bank silos (lose atomic settlement).
CANTON resolves it: trustless, atomic, shared-ledger settlement WITHOUT radical transparency, via
SELECTIVE DISCLOSURE. First system to give DeFi's settlement AND TradFi's privacy. Why Goldman,
DTCC, JP Morgan build there.

## III.2 -- Network of networks
- Not one global ledger. Each VALIDATOR runs its own sub-network = its own slice of the ledger,
  storing ONLY the contracts it is a party to. Privacy-first, isolated.
- "Canton = a network of networks" (like the internet: many private sites + open ones, all
  interoperating at the protocol level).

## III.3 -- The Global Synchronizer
- Connects every validator to provide ATOMICITY across them.
- Sees NOTHING: receives only cryptographically ENCRYPTED messages. It only SEQUENCES, ORDERS,
  and BATCHES them, with BFT consensus, to guarantee all-or-nothing settlement across validators.
- It's the shared CLOCK, never a shared database. (A US bank and a Tokyo bank settle atomically
  while each sees only their slice.)

## III.4 -- Sub-transaction privacy ("proof of stakeholders")
- Only the parties NAMED in a contract (as signatory or observer) can ever see it.
- A non-party sees NOTHING -- enforced at the PROTOCOL level, not by an app-layer filter.
- This is THE moat, and it's literally encoded by Daml's signatory/observer rules (Part IV).

## III.5 -- Selective disclosure
The product of the above: each party sees only its own legs; a regulator/auditor gets an OBSERVER
view; outsiders/competitors see nothing -- while the settlement is still atomic and verifiable.

## III.6 -- Why institutions can't use a public chain
Public data + MEV + market impact make it legally and competitively impossible. Permissioned bank
silos lose cross-institution atomic settlement. Canton is the only thing doing both.

================================================================================
# PART IV -- DAML: THE COMPLETE LANGUAGE REFERENCE
#            (this is the technical core that GOVERNS the build)
================================================================================

## IV.0 -- What Daml is, in one breath
Daml ("Digital Asset Modeling Language") is a strongly-typed, FUNCTIONAL, Haskell-derived language
for writing SMART CONTRACTS as templates on a ledger. You don't write loops mutating global state
(Solidity) -- you DECLARE contracts, who must authorize them, and what ACTIONS (choices) transform
them. It is an ACCESS-CONTROL language first: every line is about WHO can see and WHO can do.

Mental model vs other chains:
- Solidity: a contract is a deployed object with mutable storage + functions anyone may call (gated
  by require()).
- Daml: a contract is an immutable RECORD on the ledger; you "change" it by ARCHIVING the old one
  and CREATING a new one inside a CHOICE. Authorization is structural (signatories), not an if-check.

## IV.1 -- Project structure & the build artifact
```
my-project/
  daml.yaml        # manifest: sdk-version, name, version, source dir, dependencies, init-script
  daml/
    Token.daml     # a MODULE. Module name MUST match file path/name.
```
- `daml.yaml` lists dependencies: `daml-prim`, `daml-stdlib` (always), `daml-script` (for tests),
  and optionally `daml-finance-*` packages.
- BUILD with DPM (Daml Package Manager) -> produces a **DAR** file (Daml ARchive) = your compiled,
  deployable package. You upload the DAR to a validator (Part V).
- Multi-template / multi-party apps may need a MULTI-PACKAGE file (CPort scaffolds this).

## IV.2 -- Modules & imports
```daml
module Token where          -- must match the filename (Token.daml)

import Daml.Script           -- the testing/scripting library
import DA.Optional (fromSome)
import DA.List (sortOn)
import DA.Time (addRelTime)
```
Module declaration is mandatory and first. Imports pull in the standard library (`DA.*`) and Daml.Script.

## IV.3 -- The type system (everything is typed)
Built-in types you will use:
- `Party`    -- an on-ledger identity (NOT an address). Capital P. Comes from the loop wallet.
- `Text`     -- a string.
- `Int`      -- 64-bit integer.
- `Decimal`  -- fixed-point number for money (use this for quantities/prices, never floats).
- `Bool`     -- True / False.
- `Date`, `Time`, `RelTime` -- calendar date, absolute timestamp, a duration.
- `ContractId t` -- a typed pointer to a live contract of template `t` on the ledger.
- `Optional a`   -- `Some a` or `None` (Daml's null-safety; like Rust's Option / Haskell's Maybe).
- `[a]`          -- a list of `a`.
- `Either a b`   -- `Left a` (usually error) or `Right b` (usually success).
- tuples `(a, b)`, and `()` (unit, the "void" return).

Type signatures read right-to-left in returns: `transfer : Party -> Decimal -> Update (ContractId Token)`
means "takes a Party and a Decimal, returns a ledger action producing a ContractId Token."

## IV.4 -- Records (data types): the shape of data
```daml
data TokenInfo = TokenInfo
  with
    symbol   : Text
    quantity : Decimal
    price    : Decimal
  deriving (Eq, Show)
```
- A RECORD groups named fields (like a struct/class WITHOUT methods).
- `deriving (Eq, Show)` auto-generates equality and printing.
- Access a field with dot: `info.quantity`. Update with `info with quantity = 5.0`.
VARIANTS / enums:
```daml
data Status = Proposed | Accepted | Settled | Cancelled  deriving (Eq, Show)
```

## IV.5 -- TEMPLATES: the contract definition (the heart)
```daml
template Token
  with
    issuer : Party          -- the FIELDS (parameters) of the contract
    owner  : Party
    info   : TokenInfo
  where
    signatory issuer, owner             -- who MUST authorize (the owners)
    observer info                        -- (illustrative) who can SEE but not act
    ensure info.quantity > 0.0           -- a PRECONDITION; contract can't exist if false

    -- a CHOICE = an executable action ON this contract
    choice Transfer : ContractId Token   -- name : return type
      with
        newOwner : Party                 -- choice arguments
      controller owner                    -- WHO may exercise this choice
      do                                  -- the body: ledger actions (an Update)
        create this with owner = newOwner -- archive old, create new with a changed field
```
Key pieces:
- `with ... where` -- fields, then the rules.
- `signatory` -- the authorizing parties. NOTHING happens to the contract without their authority.
  This is the structural core of Canton privacy + authorization.
- `observer` -- parties who can SEE the contract but cannot act (e.g., a REGULATOR). This is how
  you implement selective disclosure.
- `ensure` -- a boolean precondition; a contract that violates it cannot be created.
- `key` / `maintainer` (optional) -- a unique business key for lookups (see IV.8).
- `this` = the current contract's data; `self` = the current contract's ContractId.

## IV.6 -- CHOICES in depth (the only way to change the ledger)
A choice is the verb. Exercising it runs its body and (by default) ARCHIVES the contract.
```daml
choice Name : ReturnType
  with field : Type        -- optional arguments
  controller party          -- who is authorized to exercise
  do
    -- Update actions: create / exercise / fetch / archive / assert ...
```
Consuming behaviour:
- `choice` (default) = CONSUMING: archives this contract when exercised (a state transition).
- `nonconsuming choice` = leaves the contract alive (use for read-only or repeatable actions, e.g.
  an agent querying or a recurring action).
- `preconsuming` / `postconsuming` = archive before/after the body (advanced).
Return types:
- `ContractId T` when the choice creates/returns a new contract.
- `()` (unit) when it returns nothing (e.g., a `Burn` that just archives -- `do return ()`).
- any type: `Decimal`, a tuple, a list, etc.
Multiple controllers / authorization:
- A party can ONLY create a contract that names them as signatory, OR via a choice they control on
  a contract whose signatories already authorized that path. This is why you can't unilaterally
  transfer a token to someone who must also sign -- you need the PROPOSE-ACCEPT pattern (IV.10).

## IV.7 -- The Update monad & `do` notation (how ledger actions compose)
`Update a` = "a recipe that, when submitted, changes the ledger and yields an `a`." `Script a` is
the analogous type for TESTS. You sequence actions in a `do` block:
```daml
do
  cid <- create Token with issuer, owner, info     -- <- BINDS the result of a ledger action
  newCid <- exercise cid Transfer with newOwner = bob
  t <- fetch newCid                                 -- read a contract's current data
  let total = info.quantity * info.price            -- let = PURE (non-ledger) binding
  assertMsg "must be positive" (total > 0.0)        -- guard; aborts the whole tx if false
  return newCid                                     -- produce the final value
```
- `<-` binds the result of an Update/Script action. `let` binds a pure value (no `<-`).
- The whole `do` block is ONE ATOMIC transaction: if any line fails/aborts, the ENTIRE thing rolls
  back. (This is where atomic DvP comes from -- both legs in one do block = both or neither.)

## IV.8 -- Ledger primitives (the verbs you call inside `do`)
- `create T with ...`            -> create a contract, returns `ContractId T`.
- `exercise cid Choice with ...` -> run a choice on a contract by its id.
- `exerciseByKey @T key Choice`  -> exercise by business key instead of id.
- `fetch cid`                    -> read current contract data (must be a stakeholder).
- `fetchByKey @T key`            -> read by key.
- `lookupByKey @T key`           -> `Optional (ContractId T)` -- does it exist?
- `archive cid`                  -> explicitly archive (most choices archive implicitly).
- `getTime`                      -> the ledger time (for deadlines/maturities).
- `assertMsg msg cond` / `abort msg` / `error msg` -> guards & failures (roll back the tx).
Contract keys:
```daml
key (issuer, info.symbol) : (Party, Text)   -- a unique business identifier
maintainer key._1                            -- the party responsible for uniqueness
```

## IV.9 -- Functional concepts you'll meet (Haskell DNA)
- PURE & IMMUTABLE: values don't mutate; you produce new values. No global mutable state.
- FUNCTIONS are values: `map`, `filter`, `foldr/foldl` over `[a]`. Lambdas: `\x -> x * 2`.
- CURRYING: `f a b` is `(f a) b`; partial application is normal.
- `let ... in` for local bindings; `where` clauses for helpers under a definition.
- `Optional` handling: `case mx of Some x -> ...; None -> ...`, or helpers `fromOptional`, `fromSome`.
- Monadic helpers over actions: `forA xs f` (do f for each), `mapA`, `traverse`, `when cond act`,
  `unless`, `void`. These let an agent/choice loop over many items inside one transaction.
- TYPECLASSES: `Eq` (==), `Ord` (<,>), `Show` (printing) -- usually auto-derived.

## IV.10 -- THE PROPOSE-ACCEPT PATTERN (the one you'll actually build)
Because both sides of a real trade must authorize, you split it in two contracts:
```daml
template TradeProposal
  with
    seller : Party
    buyer  : Party
    asset  : Text
    price  : Decimal
  where
    signatory seller        -- seller proposes & signs
    observer  buyer         -- buyer can SEE the offer (privacy: only these two)

    choice Accept : ContractId Trade
      controller buyer       -- only the buyer can accept
      do
        create Trade with seller, buyer, asset, price   -- now BOTH have authorized

    choice Reject : ()
      controller buyer
      do return ()

template Trade
  with
    seller : Party; buyer : Party; asset : Text; price : Decimal
  where
    signatory seller, buyer  -- both signed -> the deal is real
```
Flow: seller `create`s a TradeProposal -> buyer `exercise`s `Accept` -> a `Trade` is created with
both as signatories. This is EXACTLY the workshop's example, and the skeleton of TradeGuard.
The regulator becomes an `observer` on `Trade` for selective disclosure.

## IV.11 -- Daml Script (how you TEST multi-party flows)
```daml
setup : Script ()
setup = script do
  seller <- allocateParty "Seller"
  buyer  <- allocateParty "Buyer"
  reg    <- allocateParty "Regulator"

  propId <- submit seller do
    createCmd TradeProposal with seller, buyer, asset = "Gold", price = 100.0

  tradeId <- submit buyer do
    exerciseCmd propId Accept

  -- assert the buyer can see it, an outsider cannot:
  Some _ <- queryContractId buyer tradeId
  pure ()
```
- `allocateParty` -- make test parties. `submit p do ...` -- p authorizes these commands.
- `submitMustFail` -- assert an unauthorized/invalid action is REJECTED (great for proving privacy
  and authorization rules hold). `createCmd` / `exerciseCmd` -- the command versions.
- `query` / `queryContractId` -- read the ledger AS a given party (this is how you DEMONSTRATE that
  party A sees X and party B/outsider does not -- your demo's money shot).

## IV.12 -- Gotchas (field-tested)
- A party can't be made a signatory of a contract they didn't authorize -> use propose-accept.
- Choices are CONSUMING by default; forgetting `nonconsuming` archives a contract you wanted to keep.
- Use `Decimal` for money, never `Int`/floats; mind rounding.
- `ensure` failures and `assertMsg`/`abort` roll back the WHOLE transaction (atomicity -- a feature).
- Privacy is structural: if the regulator isn't an `observer`, they literally cannot see it -- and
  if you accidentally add an observer, you've leaked. Model the observer set deliberately.
- Module name MUST match the file, or you get a wall of errors.

================================================================================
# PART V -- CANTON DEV TOOLCHAIN & DEPLOYMENT
================================================================================

## V.1 -- The pieces
- DPM (Daml Package Manager) -- builds/test/codegen. `dpm build` -> DAR; `dpm test` -> run Scripts;
  `dpm studio` -> VS Code IDE; `dpm codegen-js|java` -> typed client libs for your agent.
- DAR -- the compiled package artifact you deploy.
- Validator / Participant node -- your gateway to the ledger; you DEPLOY to a validator (not an RPC).
- DevNet -- the shared hackathon test network (pre-configured for you).
- Canton Console / Daml Shell -- interactive tools to inspect parties, contracts, queries.
- PQS (Participant Query Store) -- projects your party's contracts into PostgreSQL so you can read
  state with plain SQL (ideal for the off-chain agent and the UI).
- JSON Ledger API (HTTP/JSON) -- easiest interface for an agent (Python/TS/curl): submit
  create/exercise commands, query the active contract set (ACS), stream transactions.
- gRPC Ledger API -- the lower-level, high-performance equivalent.
- loop wallet -- gives you your PARTY ID (your on-ledger identity) on cport.

## V.2 -- The hackathon deployment path (SEAPORT) -- USE THIS
> NOTE: the workshop auto-transcript garbled the names. The tool is **Seaport** (NOT "CPort"),
> and the wallet is **Canton Loop** (NOT just "loop"). `cport.io` does not exist. Correct URLs below.
> Official guide: https://github.com/Jatinp26/Seaport-Guide
1. **Get DevNet wallet**: go to **https://devnet.cantonloop.com**, create your Canton Loop wallet,
   copy your **Party ID** (looks like `abc123::122...34a`).
2. **Send Party ID to the organizer** (Jatin / Canton Discord) -> they INVITE you to the hackathon
   **org** by Party ID (no "join" button; admin adds you; pending invite applies on first sign-in).
3. **Log in** at **https://app.devnet.seaport.to** with the Loop wallet -> use the **org switcher**
   (top-left, next to logo) to enter your hackathon team. The shared **`5n sandbox`** DevNet
   validator is pre-configured for the org -- no setup.
4. In Seaport (web IDE): **New Blank Project**, OR start from a **template** (e.g. "DAML Intro Data"),
   OR **Connect GitHub** to import a repo.
5. **Build Project** -> produces a `.dar` (appears under the **Builds** folder). **Deploy** -> push
   the DAR to the `5n sandbox` validator. Then create live contracts + exercise choices in-browser.
6. Two MODES: **Personal** (private workspace) vs **Org** (the hackathon team -- USE THIS to deploy).
   Tabs are mode-scoped; a project opened in Personal stays Personal (transfer ownership to move it).
7. MINIMUM BAR: "something live on DevNet."
- OPEN QUESTION to resolve W1: does a daml-finance-based DAR upload+run cleanly on the Seaport
  `5n sandbox` validator? If yes -> use daml-finance settlement primitives; if risky -> hand-roll
  templates (the propose-accept pattern already gets you most of the way).

## V.3 -- daml-finance (the primitive library, if it deploys)
Pre-built, composable Daml libraries so you don't rebuild money:
- INSTRUMENTS (Token/Bond/Equity/Generic) -- the economic terms + lifecycle of an asset.
- HOLDINGS (Fungible/Transferable) -- a balance/position in an account (your ERC-20-equivalent).
- ACCOUNTS -- custodial account model (credit/debit, custody hierarchies).
- SETTLEMENT -- an atomic engine for multi-leg, multi-party DvP (Batches/Instructions). Canton
  enforces all-or-nothing + sub-transaction privacy per leg.
Massive leverage: your agent layer focuses on decisions; the primitives handle tokens + atomic settle.

## V.4 -- The hackathon resources
- docs.canton.network (modules incl. "from Ethereum/Solana"; has an "Ask Assistant" AI button).
- Canton DevHub -- a catalog of ecosystem tools (IDEs, SDKs, indexers).
- Canton Network GitHub (git devs) -- hackathon resources, tutorials, FAQs, Canton quick start.
- forum.canton.network -- app-dev Q&A.
- Discord: Canton (tech) + Encode (logistics). Send party ID to Jatin here.

================================================================================
# PART VI -- THE TRADEGUARD BUILD (how every concept maps to code)
================================================================================

## VI.1 -- One-line product
TradeGuard gives B2B trade finance the ATOMIC SWAP it never had: replace the slow, costly LETTER OF
CREDIT (a bank middleman bridging the trust gap) with private ATOMIC DvP on Canton -- cash leg +
asset leg settle together or neither moves -- with SELECTIVE DISCLOSURE so each party sees only its
legs and a regulator observes. TradFi's privacy + DeFi's settlement in one system.

## VI.2 -- Three layers
1. DAML CONTRACTS (on-ledger, the source of truth):
   - `TradeProposal` (seller signatory, buyer observer) -> `Accept` -> `Trade`/`Settlement`.
   - The cash leg = a tokenized-deposit/holding; the asset leg = a title/holding.
   - Atomic DvP = both legs moved inside ONE choice's `do` block (all-or-nothing).
   - Regulator = `observer` on the settled contract (selective disclosure).
   - Optional conditional release: settle only when a private delivery ATTESTATION exists (turns a
     payment into a workflow).
2. OFF-CHAIN AGENT (governed automation, your edge -- NEVER moves money itself):
   - Reads party-scoped state via PQS (SQL) or the JSON Ledger API (ACS query).
   - Watches for the delivery/condition, PREPARES the settlement command, then waits behind a HUMAN
     APPROVAL GATE. It proposes/exercises commands but authorization stays with the Daml signatories.
   - Built in Python/TS using `dpm codegen` clients or raw JSON API.
3. UI (the demo's money shot):
   - Role-based views: Buyer view, Seller view, Regulator view, Outsider view.
   - Same atomic transaction -> four different truths. This visual = the privacy proof judges want.

## VI.3 -- The pitch script (every bolded word now yours)
"TradeGuard replaces the **letter of credit** in B2B **trade finance**. Today **settlement risk**
-- the **Herstatt** problem -- forces buyers and sellers to trust slow, expensive intermediaries.
We do **atomic DvP**: the cash leg and asset leg settle together or not at all, eliminating
**counterparty risk** at settlement. Because **prices and counterparties are competitive
information**, Canton's **selective disclosure** lets each party see only its own legs while a
**regulator** gets an **observer** view -- impossible on a public chain (**MEV / information
leakage**), impossible in **siloed** bank systems (can't settle **atomically** across institutions)."

## VI.4 -- The 5-beat thesis (say it cold)
institutions must settle together (shared ledger) -> but cannot leak (privacy) -> public chains leak
(MEV/transparency) -> bank silos can't settle atomically across each other -> Canton is the only
thing that does both.

================================================================================
# PART VII -- QUICK INDEX (where every confusing word lives)
================================================================================
- IOU, claim, collateral, overcollateralization, liquidation, haircut, bond, equity vs debt,
  coupon/principal/maturity, yield, issuer/creditor/debtor .......... I.1
- equity/stock, order book, bid/ask/spread, market maker, slippage, OTC, derivative
  (forward/future/option/swap), repo, leverage/margin/short, securitization, money market,
  interest rates/yield curve, FX, tokenized deposit vs stablecoin, RWA, treasury ops,
  settlement/clearing/finality/T+2, netting, DvP/PvP ................ I.2
- counterparty/settlement/liquidity/operational/systemic/market risk, Herstatt ... I.3
- DeFi<->TradFi name map .......................................... II
- network of networks, global synchronizer, sub-transaction privacy, selective disclosure . III
- Daml: modules, types, records, templates, signatory/observer/controller, choices (consuming/
  nonconsuming), Update monad, do-notation, create/exercise/fetch/archive, keys, propose-accept,
  Daml Script, gotchas ............................................. IV
- DPM, DAR, validator, DevNet, PQS, JSON/gRPC Ledger API, loop wallet, CPort deploy, daml-finance . V
- TradeGuard layers, agent, role-based UI, pitch script, 5-beat thesis ... VI

--------------------------------------------------------------------------------
SIBLING DOCS in this folder:
- DEFI_TO_TRADFI_JOURNEY.md  -- the narrative/intuition version of Parts I-III
- FINANCE_GLOSSARY.md        -- terse pitch-prep glossary
- SYNTHESIS.md / OPERATIONS.md -- strategy + hackathon logistics
- diagrams/canton-mental-model.excalidraw -- the visual map
This file (CANTON_BUILD_BIBLE.md) is the SUPERSET / master reference.
--------------------------------------------------------------------------------
