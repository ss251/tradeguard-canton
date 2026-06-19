# DeFi -> TradFi: The Journey (a first-principles bridge for a crypto-native builder)

> For someone who knows DeFi and needs to *understand* (not memorize) TradFi before building
> on Canton. The spine: TradFi and DeFi are the SAME machine with different names. Row from
> the shore you know (DeFi) to the one that's foreign (TradFi).
>
> READ ORDER: Appendix A (the atoms) first if any single word trips you up, then Ch.0 onward.

---

# APPENDIX A — THE ATOMS (plain-English building blocks)

> The smallest concepts everything else is built from. Each has a DeFi twin so it locks in.
> If a word in the main journey confuses you, it's almost certainly defined here.

### IOU = "I Owe You"
A written promise/claim that someone owes you value. The most primitive instrument there is.
- Napkin: "I owe you $20 - Dave." That napkin is an IOU. It's not the $20; it's a *claim on* $20.
- THE BIG IDEA: almost all of finance is IOUs in costume.
  - Bond = a formal, tradable IOU (Apple's napkin: "I owe you $1000 + interest").
  - Your bank balance = the bank's IOU to you (you hold the bank's promise, not the dollars).
  - A dollar bill = historically a government IOU.
  - USDC = Circle's IOU ("I owe you 1 real dollar, redeemable").
- DeFi twins: USDC (Circle's IOU), aUSDC (Aave's IOU for your deposit+yield), wETH/wBTC
  (wrapper's IOU for the real asset).
- 2-sec translation: IOU = a CLAIM ON value, not the value itself.

### Claim
The formal word for "a right to receive value from someone." An IOU gives you a claim.
A bond is a claim on the issuer. A bank balance is a claim on the bank. Same idea, lawyer's word.

### Collateral
Something valuable you lock up as a promise you'll repay. Pawn shop: leave your watch, get cash,
reclaim the watch when you repay. The watch = collateral.

### Overcollateralization  (you asked about this)
You must lock up MORE value than you borrow. The "over" = more than 100%.
- Aave example: to borrow $100 USDC you deposit $150 ETH = 150% = overcollateralized.
- WHY the system demands it: collateral's value MOVES, and the protocol trusts code, not your
  name. If you posted only $100 and ETH dipped 1%, your collateral ($99) < debt ($100) and you'd
  walk away. The extra $50 is a SAFETY BUFFER against the collateral dropping.
- If the buffer erodes toward your debt -> you get LIQUIDATED (force-sold) before it's gone.
- => overcollateralization = the buffer that makes TRUSTLESS lending safe (no credit check needed).
- TradFi twins: haircut (value your $150 as only $140 of borrowing power), margin call (post more
  or we sell), and REPO is literally this (bond for cash, overcollateralized with a haircut).

### Liquidation / Margin call
The buffer failed. DeFi "liquidation" = protocol force-sells your collateral to recover its money.
TradFi "margin call" = "post more collateral or we sell you out." Same event, different name.

### Haircut
TradFi's conservative discount on collateral: "your $150 of bonds counts as only $140."
The $10 trimmed = the haircut. Same job as DeFi's overcollateral buffer.

### Bond  (you asked about this)
A loan chopped into a tradable piece of paper. When you BUY a bond, YOU are the lender.
- Apple needs $1000 -> issues a bond:
  - You pay $1000 today = the PRINCIPAL / face value.
  - Apple pays you 5%/yr = $50/yr = the COUPON (interest). (Name is from old paper coupons you clipped.)
  - After 10 yrs = MATURITY, Apple returns your $1000.
- DeFi twin: a bond ~ an Aave deposit you can SELL.
  - deposit USDC -> buy bond | earn APY -> earn coupon | withdraw principal -> principal at maturity
  - borrower = the ISSUER (Apple, a government).
- KEY difference: a bond is TRADABLE. Need cash in year 3? Sell it on the SECONDARY market;
  the buyer collects the rest. (primary market = asset first issued; secondary = traded after.)
- THE SEESAW (most important fact in bonds): bond prices move OPPOSITE to interest rates.
  You hold a 5% bond; new bonds pay 7% -> nobody wants yours -> you must drop its price. Rates up,
  price down. New bonds pay 3% -> yours is a gem -> price up. Rates down, price up.
- "Fixed income" = the whole bond universe (income is FIXED in advance).
- Why it matters for you: bonds are the BIGGEST market on Earth (~$130T, bigger than stocks).
  Governments fund via bonds (US Treasuries = safest asset, the benchmark everything's priced off).
  Tokenized treasuries (bonds on-chain as RWAs) are one of the hottest things on Canton.

### THE FUNDAMENTAL FORK: own it vs lend to it
- EQUITY (stock) = you OWN a slice of the company. Upside if it grows. You're an owner.
- BOND / DEBT = you LENT to the company. Fixed payments, no upside beyond interest. You're a creditor.
  Safer than equity (creditors get paid before owners if things go bad).
- This own-vs-lend split is the most fundamental fork in all of finance.

### Coupon / Principal / Maturity / Yield
- Principal = the amount lent (the $1000). Coupon = the periodic interest ($50/yr).
- Maturity = the date principal is returned. Yield = your return % (DeFi: APY).

### Issuer / Creditor / Debtor
- Issuer = who creates the instrument & owes the money (Apple, the government).
- Creditor = who is owed (you, the bond buyer). Debtor = who owes (the issuer).

---

# Ch.0 — What all finance is
Moving value (1) across people, (2) across time, and (3) managing the trust gap that opens when you do.
- across people -> payments, trading, settlement
- across time -> lending, borrowing, saving
- the trust gap -> collateral, custody, clearing houses, regulation (all intermediaries)
Every term below is just one of these three verbs in a costume.

## Ch.1 — DeFi, named precisely
- Token (ERC-20) = unit of value. Stablecoin (USDC) = DeFi's cash.
- AMM/DEX (Uniswap) = robot market; swaps against a liquidity pool (math sets price).
- Lending (Aave) = deposit -> others borrow -> you earn yield/APY. Borrowers post
  overcollateralization; if collateral drops they're liquidated.
- Atomic swap = one tx, both legs or neither (you never fear "I send, they don't").
- Composability = money legos. Mempool = public waiting room -> MEV/front-running.
- KEY TENSION: DeFi's superpower (public + automatic) IS its disease (public -> front-run).

## Ch.2 — THE BRIDGE (print on eyelids): same machine, different names
| DeFi | TradFi | shared job |
|------|--------|-----------|
| wallet address | account @ custodian / party | who you are |
| token | security / instrument | the tradable thing |
| stablecoin (USDC) | tokenized deposit / cash | the cash leg |
| Uniswap/DEX | exchange / market maker / OTC desk | where you trade |
| liquidity pool | market maker's inventory | who takes the other side |
| Aave lending | money market / repo / credit desk | lending across time |
| overcollateralization | margin / collateral / haircut | trust buffer |
| liquidation | margin call / default mgmt | buffer fails |
| yield/APY | interest / coupon / return | reward for lending |
| gas fee | fee / spread / commission | cost to transact |
| ATOMIC SWAP | DvP (Delivery vs Payment) | both legs or neither |
| block finality | settlement finality | truly "done" |
| public mempool | order flow (kept PRIVATE) | where leakage happens |
| MEV / front-running | front-running / info leakage | the predator |
| smart contract | legal contract / ISDA | the rulebook |
| composability | interoperability across institutions | snapping pieces |
| DAO treasury | corporate treasury | managing org cash |
| TVL | AUM (assets under management) | the scale flex |

## Ch.3 — Why TradFi is more complicated: NO SHARED LEDGER
DeFi: everyone reads/writes the same chain -> settlement is automatic & atomic -> no middlemen.
TradFi: every institution has its own private DB -> bridging two private ledgers needs
intermediaries (custodian holds assets; clearing house/CCP guarantees both sides; settlement
systems move value slowly, often T+2). Every intermediary exists ONLY because there's no
shared ledger. => Canton = a shared ledger for institutions -> collapses intermediaries like
DeFi did, but WITHOUT forcing business into public view. DeFi proved the idea; Canton makes
it private.

## Ch.4 — The 4 mechanics TradFi makes you stare at (DeFi hides them)
1. Settlement = the final exchange. DeFi: instant/atomic/invisible. TradFi: multi-day ordeal.
   Goal = drag T+2 -> T+0/atomic. TradeGuard = "give TradFi the atomic swap it never had."
2. DvP (Delivery vs Payment) = asset leg + cash leg settle simultaneously or not at all =
   an atomic swap in a suit. Kills the pay-but-not-receive gap. (PvP = FX version, currency-for-currency.)
3. Netting = settle the NET difference, not each gross obligation. ($100 owed - $70 owed = one $30).
   multilateral = across many parties. Mnemonic: gross = pay everything; net = pay the difference.
4. Collateral = assets pledged for trust (= DeFi overcollateralization). haircut = value it
   conservatively; collateral mobility = move it fast (a $B problem, again from no shared ledger).

## Ch.5 — Risk (the language finance thinks in)
- counterparty/credit risk: they default generally.
- settlement risk (Herstatt, 1974): you delivered your leg, they didn't deliver theirs -> exposed
  in the gap. ATOMIC DvP makes this impossible. TradeGuard's #1 claim. (Distinct from counterparty risk!)
- liquidity risk: can't get cash when/where needed even if solvent.
- operational risk: the process breaks (error/fraud/system).
- systemic risk: one failure cascades (2008).

## Ch.6 — THE DEEPEST POINT: privacy is where DeFi breaks & Canton wins
- DeFi gets trust via radical transparency -> cost = information leakage (MEV, competitors read your hand).
- TradFi REQUIRES radical privacy (a $2B bond sale can't be announced = market impact; legal + competitive necessity).
- The trap: DeFi's transparency and TradFi's privacy are fundamentally OPPOSED. Can't port Uniswap
  to Wall St (too public); can't return to bank silos (lose atomic shared-ledger settlement).
- CANTON resolves it: trustless atomic shared-ledger settlement WITHOUT radical transparency, via
  selective disclosure / sub-transaction privacy (each party sees only its slice; regulator observes;
  outsiders see nothing). First system to give BOTH. Why Goldman/DTCC/JPM are there.

## Ch.7 — TradeGuard, now fully visible
Gives B2B trade finance the atomic swap it never had. Today buyer+seller in different institutions
can't settle directly (no shared ledger) -> pay a Letter of Credit (bank middleman), slow/expensive,
exposed to settlement/Herstatt risk. TradeGuard replaces it with atomic DvP on Canton: cash leg
(tokenized deposit) + asset leg (title) settle together or neither moves = the DeFi atomic swap.
Prices/counterparties are competitive info -> Canton selective disclosure: each party sees only its
legs, regulator observes -> TradFi's privacy + DeFi's settlement, finally in one system.

---

## QUICK-LOOKUP INDEX (where to find a confusing word)
- IOU, claim, collateral, overcollateralization, liquidation, haircut, bond, equity vs debt,
  coupon/principal/maturity, yield, issuer/creditor/debtor -> APPENDIX A
- netting, DvP, PvP, settlement, T+2/T+0, collateral mobility -> Ch.4
- counterparty/settlement/liquidity/operational/systemic risk, Herstatt -> Ch.5
- why privacy matters, market impact, info leakage, selective disclosure -> Ch.6
- DeFi<->TradFi name map -> Ch.2
- repo, custodian, clearing house/CCP, OTC, intermediaries -> Ch.3 + FINANCE_GLOSSARY.md
