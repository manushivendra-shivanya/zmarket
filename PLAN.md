# zmarket — plan

**Last updated:** 2026-08-20 · **Status:** nothing built, no capital deployed.

## 1. Scope

- **Equity intraday (MIS) only.** No F&O. No options. No overnight positions initially.
- **Capital:** ₹10,000/day cap. ₹5,000–10,000/month in, for 3–4 months. **~₹40,000 total at risk.**
- **Per trade:** ₹2,000–4,000 of own capital, margin **on top** → positions of ₹4,000–16,000.
- **Leverage:** 2–4x (SEBI peak-margin rules cap intraday equity; varies by stock).
- **Accepted outcome:** total loss of the ₹40,000. Bounded, and decided in advance.

Long-term positions, options and weekly expiries are explicitly **out of scope for now** and
each need their own cost model before being considered — the numbers here do not transfer.

## 2. What a trade costs — the number everything hangs on

**Round trip = 0.1062% of position value.** Flat below ₹66,667 per order, so a ₹4,000 position
and a ₹50,000 position cost the same percentage. Relief only past that threshold (0.083% at ₹1L,
0.045% at ₹5L) where the ₹20/leg brokerage cap starts to bind.

Break-even win rate, symmetric win/loss: **w = (cost% / target% + 1) / 2**

| Target move | Win rate needed |
|---|---|
| 0.20% | **76.6%** — dead on arrival |
| 0.50% | 60.6% |
| 1.00% | 55.3% |
| 2.00% | 52.7% |

**Rule: never target below 0.5%.** Below that, friction decides the outcome, not skill.

**But the table above assumes win == loss, and that is not the plan.** Every trade
caps both sides — a target and a tighter stop. That is the main lever in this
whole system:

| Target / Stop | R:R | Break-even win rate |
|---|---|---|
| 2.6% / 2.6% | 1:1 | 52.1% |
| 2.6% / 1.30% | 2:1 | 36.1% |
| 2.6% / 0.65% | 4:1 | **23.3%** |

At 4:1 you can be wrong three times in four and still profit. **₹1,000/day is
then a frequency question:** ~3.5 trades/day at 45% accuracy. Run
`tools/risk_reward.py`.

Full derivation: [`docs/COST-MODEL.md`](docs/COST-MODEL.md).

## 3. Hard rules

1. **Percentage targets, never rupee-per-share targets.** "₹5 a share" is not a strategy — it is
   2.5% on a ₹200 stock and 1.25% on a ₹400 one, two completely different problems. Fix the
   percentage and size to it.
2. **Prefer own capital over leverage.** ₹4,000 at 2x and ₹2,000 at 4x are the *same position*
   and the same P&L to the rupee — but a 3% adverse move is 6% of the first and 12% of the
   second. Same return, half the ruin risk. Lower leverage, more capital, always.
3. **Stop-loss on every entry**, set before the entry, **never widened. Ever.**
   Prefer **Cover Orders** — they enforce the stop at entry and remove the choice.
   Three widened stops turn a ₹5,925 month into ₹1,830.
4. **Daily loss cap: −₹1,000.** Stop trading for the day. No exceptions, no "one more".
5. **No averaging down. No revenge trade. No discretionary override** of a systematic signal.
6. **MIS auto-squares around 15:20.** No strategy may depend on holding past it.
7. **Credentials in env vars only.** Never committed, never shared with any zhealth key.
8. **Every phase gate is real.** A phase that fails ends the experiment. That is what they are for.

## 4. Phases — no money moves until the previous one passes

### Phase 1 — signal logger · ₹0, no subscription, no capital
Record every candidate entry: timestamp, symbol, price, direction, **reason**, target %, stop %.
Score against what actually happened, minus 0.1062%.

**Exit gate:** 100+ logged signals and a measured hit rate with a confidence interval.

This is the only phase that matters right now. Everything downstream is an assumption until it
produces a number.

### Phase 2 — live micro-size · ₹1,000–2,000 positions, one month
Real money, real fills, real queue position, real psychology. Costs are still 0.1062%, so the
economics are identical to full size — only the rupee loss is smaller.

**This is deliberately not paper trading.** Paper trading models neither slippage nor partial
fills nor the fact that your own order moves the book, and it cannot model what it feels like to
be down. Micro-sizing gives all of that at a fifth of the risk.

**Exit gate:** measured hit rate within 5pp of phase 1. A large gap means phase 1 was measuring
something that does not survive contact with a real order book.

### Phase 3 — scale to ₹10,000/day
Only if phase 2 clears the break-even row for the intended target size.

## 5. Platform tier — Personal (free), decided 2026-08-20

**Fee is ₹0.** Kite Connect has three app types and **Personal is free**: investing,
trading and reports APIs, with **no historical data and no live quotes/WebSockets**.
That is the right tier for now, because phase 1 needs no Kite market data — it runs
on free sources — and Personal still exposes `/charges/orders`, so the cost model can
be reconciled against Zerodha's own numbers at no cost.

**Connect is deferred, not rejected.** It is a credit model ("500 credits for 30
days"; **rate unverified — check the Billing tab**) and its only advantage is ticks
and historical data. Upgrade when phase 1 produces a hit rate worth streaming for.

**Correction:** earlier versions of this plan assumed ₹2,000/month and concluded
"₹40,000 is the break-even capital". **That was an unverified figure and the
conclusion does not hold at ₹0.** See `docs/DECISIONS.md`.

**Redirect URL: `http://127.0.0.1:8765/`** — what `tools/auth.py` listens on.

Execution stays manual regardless: 2–4 trades/day is two taps in the Kite app, and
automated order placement is blocked by §6.0 anyway.

## 6. Regulatory position

### 6.0 SEBI static-IP mandate — LIVE since 1 April 2026

**API orders from an unregistered static IP are rejected.** Not upcoming; in force.
Market data appears exempt (the rule names *orders*) but **that reading is
unverified**.

Consequence, and it is load-bearing: **phases 1 and 2 are unaffected** because both
read data and execute manually. **Automated execution is blocked** until a static IP
exists — an ISP add-on at ~₹500–1,500/month or a cloud VM at ~₹400–800/month, which
on ₹10,000 capital is ≥5%/month before a single trade. Do not buy one speculatively.


Self-directed algos on **your own account** through your own broker's API are permitted. SEBI's
February 2025 framework targets algo **providers and vendors**, with broker-registration and
exchange-approval thresholds keyed to order rates far above this volume.

**The exposure is the friends, not the trading.** Supplying a strategy to others, or placing
orders in their accounts, can look like the regulated activity *even with no money changing
hands* — the framework keys on the activity, not the fee.

**Structure:** each person runs their own copy, on their own subscription, in their own account.
You operate nobody's account but your own.

Confirm Kite Connect's personal-use terms with Zerodha directly. **This is not legal advice and
must be verified independently.**

## 7. Where LLM agents fit — and where they do not

**Not execution.** Too slow (hundreds of ms to seconds per call), non-deterministic, and jagged —
strong on one case, confidently wrong on an adjacent one. Trading logic must be deterministic and
backtestable: numpy and plain Python, not an agent in the loop.

**Genuinely useful:** research, backtest code generation, trade journaling, and post-hoc "why did
this lose" analysis over the accumulated signal log. That last one is the real prize — a
structured log is exactly the input an LLM is good at reading.

## 8. Open questions

- **Verify every rate** in `tools/zerodha_costs.py` against zerodha.com/charges before phase 2.
  A model built on a stale rate is worse than no model.
- **Define the universe:** liquidity floor, price band, average-daily-volume minimum.
- **Choose the target %:** 0.5% or 1.0%. This one decision drives every number above.
- **Confirm actual MIS leverage** available on the intended universe — it varies by stock and has
  been tightened since 2021.
