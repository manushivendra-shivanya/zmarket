# Cost model — Zerodha equity intraday

**Computed 2026-08-20.** Rates as understood at that date. **Verify against
zerodha.com/charges before risking money** — they change, and a stale rate makes the model worse
than no model. Every rate is isolated in `RATES` at the top of `tools/zerodha_costs.py`; correct
one number and re-run everything.

Not F&O. Not delivery — no DP charges here, those apply only on a delivery sell.

## 1. The charges

| Charge | Rate | Applies to |
|---|---|---|
| Brokerage | 0.03% **or ₹20, whichever is lower** | each leg |
| STT | 0.025% | **sell side only** |
| Exchange transaction (NSE) | 0.00297% | both sides |
| SEBI | ₹10/crore | both sides |
| IPFT (NSE) | ₹10/crore | both sides |
| Stamp duty | 0.003% | **buy side only** |
| GST | 18% | on brokerage + exchange + SEBI |

## 2. Round-trip cost by position size

| Position | Brokerage | STT | Other | GST | **Total** | **% of position** |
|---|---|---|---|---|---|---|
| ₹5,000 | 3.00 | 1.25 | 0.47 | 0.60 | **₹5.31** | **0.1062%** |
| ₹10,000 | 6.00 | 2.50 | 0.93 | 1.19 | **₹10.62** | **0.1062%** |
| ₹25,000 | 15.00 | 6.25 | 2.33 | 2.98 | **₹26.56** | **0.1062%** |
| ₹50,000 | 30.00 | 12.50 | 4.67 | 5.95 | **₹53.12** | **0.1062%** |
| ₹66,667 | 40.00 | 16.67 | 6.23 | 7.94 | **₹70.83** | **0.1062%** |
| ₹100,000 | 40.00 | 25.00 | 9.34 | 8.31 | **₹82.65** | 0.0826% |
| ₹500,000 | 40.00 | 125.00 | 46.70 | 12.73 | **₹224.43** | 0.0449% |

**The percentage is flat below ₹66,667 per order.** Brokerage is 0.03% *or* ₹20/leg whichever is
lower, so the ₹20 cap does not bind until ₹66,667 turnover. Below that you pay the percentage and
position size buys you nothing. Above it, cost per rupee starts falling.

**Practical consequence:** at ₹4,000–16,000 positions there is no size advantage to chase. Cost
is a fixed 0.1062% tax on every round trip regardless of how the position is assembled.

## 3. Break-even win rate

With average win = average loss = target `T`, cost `c` per round trip:

```
w·T − (1−w)·T − c = 0     →     w = (c/T + 1) / 2
```

At c = 0.1062%:

| Target move | On a ₹400 share | Win rate needed | |
|---|---|---|---|
| 0.10% | ₹0.40 | **103.1%** | impossible |
| 0.20% | ₹0.80 | **76.6%** | dead on arrival |
| 0.25% | ₹1.00 | 71.2% | very hard |
| 0.50% | ₹2.00 | 60.6% | |
| 0.75% | ₹3.00 | 57.1% | |
| **1.00%** | **₹4.00** | **55.3%** | the realistic floor |
| 1.50% | ₹6.00 | 53.5% | |
| 2.00% | ₹8.00 | 52.7% | |
| 3.00% | ₹12.00 | 51.8% | |

**This table is the whole argument.** Small moves are not cheap to chase — they are the most
expensive thing you can do, because friction is constant and the edge shrinks.

## 4. The scenario as actually specified

₹2,000–4,000 own capital per trade, margin on top, 2 trades/day, ₹5/share target.

| Own × Lev | Position | Price | Shares | Cost | Win | Loss | B/E |
|---|---|---|---|---|---|---|---|
| ₹2,000 × 2 | ₹4,000 | ₹200 | 20 | 4.25 | +96 | −104 | 52.1% |
| ₹2,000 × 2 | ₹4,000 | ₹400 | 10 | 4.25 | +46 | −54 | 54.2% |
| ₹2,000 × 4 | ₹8,000 | ₹400 | 20 | 8.50 | +92 | −108 | 54.2% |
| ₹4,000 × 2 | ₹8,000 | ₹400 | 20 | 8.50 | +92 | −108 | 54.2% |
| ₹4,000 × 4 | ₹16,000 | ₹200 | 80 | 17.00 | +383 | −417 | 52.1% |
| ₹4,000 × 4 | ₹16,000 | ₹400 | 40 | 17.00 | +183 | −217 | 54.2% |

Monthly, 42 trades (2/day × 21 days), **no API fee**:

| Setup | 55% | 60% | 65% | 70% | 80% |
|---|---|---|---|---|---|
| ₹2,000 2x @₹400 | 32 | 242 | 452 | 662 | 1,082 |
| ₹4,000 2x @₹400 | 63 | 483 | 903 | 1,323 | 2,163 |
| ₹4,000 2x @₹200 | 483 | 1,323 | 2,163 | 3,003 | 4,683 |
| ₹4,000 4x @₹200 | 966 | 2,646 | 4,326 | 6,006 | 9,366 |

## 5. Platform fees — ₹0 on the free tier

> **Corrected 2026-08-20.** This section originally argued against a ₹2,000/month
> subscription. That figure was **assumed and never verified**. Kite Connect has a
> **free Personal tier** (trading + reports APIs, no market data), which is the tier
> in use. The tables below are retained as the argument for why the paid **Connect**
> tier stays deferred — not as a live cost. See `docs/DECISIONS.md`.


**Everything in §4 is fee-free, and that is the real plan.** No API subscription is being bought
(`PLAN.md` §5), so no platform fee belongs in the numbers you actually plan against.

**Naming, because two different ₹2,000s caused a real mix-up on 2026-08-20:**

| Term | Meaning |
|---|---|
| **Per-trade capital** | ₹2,000–4,000. **Your own money in a single trade.** Margin sits on top. |
| **Platform fee** | Any monthly charge for API access. **Currently ₹0 — nothing is subscribed.** |

They are unrelated. The tables in §4 use the first and assume the second is zero.

### Sensitivity — what any monthly fee would do

Kept only to show why the no-subscription decision was made, not because a fee is planned.
Kite Connect is understood to be ~₹2,000/month (historical data a separate ~₹2,000/month) —
**verify before ever subscribing.**

At a strong 70% hit rate, a ₹2,000/month fee would consume this share of gross edge:

| Setup | Gross/mo @70% | Fee would eat | Net |
|---|---|---|---|
| ₹2,000 2x @₹400 | ₹662 | **302%** | −₹1,338 |
| ₹2,000 4x @₹400 | ₹1,323 | 151% | −₹677 |
| ₹4,000 4x @₹400 | ₹2,646 | 76% | +₹646 |
| ₹4,000 4x @₹200 | ₹6,006 | 33% | +₹4,006 |

At ₹2,000 own × 2x on a ₹400 share, a ₹2,000/month fee would lose money **even at an 80% win
rate** — the fee alone exceeds the entire edge. At 2 trades/day, manual execution costs nothing
and performs identically.

**Conclusion: fee stays at ₹0. Revisit only if frequency or size rises by an order of
magnitude,** at which point re-run this table with the real gross edge before subscribing.

## 6. Two structural findings

**Leverage and own capital are interchangeable for P&L, not for risk.** ₹2,000 at 4x and ₹4,000
at 2x are both an ₹8,000 position returning +₹92/−₹108 identically. But a 3% adverse move is
₹240 either way — 12% of the first stake, 6% of the second. **Same money, half the ruin risk.**

**A rupee-per-share target is not a strategy.** ₹5 on a ₹200 stock is 2.5%; on a ₹400 stock it is
1.25%. The tables above credit both at the same win rate, which silently flatters the ₹200 rows —
they are *harder* trades, not better ones. Comparisons are meaningless until the target is a
percentage.

## 7. Risk, at the stated leverage

One bad day, ₹10,000 capital:

| Leverage | 1% adverse | 2% | 3% |
|---|---|---|---|
| 2x | −₹200 (2%) | −₹400 (4%) | −₹600 (6%) |
| 3x | −₹300 (3%) | −₹600 (6%) | −₹900 (9%) |
| 4x | −₹400 (4%) | −₹800 (8%) | −₹1,200 (12%) |

At 3–4x, two bad days erase a good month. This is why the −₹1,000 daily cap in `PLAN.md` §3 is a
hard rule and not a guideline.

## 8. What this model does not capture

- **Slippage and spread.** Assumes you get your price. At 10–80 shares of a liquid stock, fills
  are a non-issue — but the spread is real and is not modelled here.
- **Partial fills** and queue position.
- **Gap risk** — a stock that opens away from your stop.
- **Correlation.** Two simultaneous positions in the same sector are one position.
- **Taxation of gains.** Intraday profit is speculative business income, taxed at slab rate.
  **Not modelled anywhere here, and it is not small.**
- **The hit rate.** The single input every number above depends on, and the one nobody has
  measured. That is phase 1.
