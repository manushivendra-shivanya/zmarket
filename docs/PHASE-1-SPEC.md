# Phase 1 — the signal logger (spec, not built)

**Status:** designed 2026-08-20, **deliberately not built in that session** (owner:
different repo, don't build here). This is the spec so whoever builds it inherits the
reasoning rather than re-deriving it.

**Cost to run: ₹0.** No capital, no Kite market-data tier, no subscription.

---

## 1. Why this is the only thing that matters right now

Every number in `PLAN.md`, `docs/COST-MODEL.md` and `docs/DECISIONS.md` is a function
of **one unmeasured input: the hit rate.** Break-even at 4:1 is 23.3%; at 1:1 it is
52.1%; ₹1,000/day needs ~3.5 trades/day at 45%. All of that is arithmetic. **Nobody
knows whether the signal clears any of those thresholds**, and no amount of further
modelling will find out.

Phase 1 turns "I think I have an edge" into **a number with an error bar.** Nothing
downstream should be built until it produces one.

---

## 2. What it does

Three commands.

**`log`** — record a candidate entry *at the moment you would have taken it*:
timestamp, trade date, symbol, direction, entry price, target %, stop %, and a
**reason in your own words**. The reason is not decoration — you will read it back
when clustering winners against losers, and "looked good" tells you nothing.

**`score`** — for signals whose day has closed, fetch that day's OHLC and decide the
outcome.

**`stats`** — hit rate, confidence interval, expectancy net of the real cost model.

**Storage:** JSON-lines at `data/signals.jsonl`, gitignored. Append-only; scoring
rewrites outcomes in place.

**Data source:** yfinance (`SYMBOL.NS`), free. Kite's Personal tier has no market
data and none is needed here.

---

## 3. Three refusals — these are the design, not details

### 3.1 A daily bar cannot order two intraday touches

If the day's range touched **both** the target and the stop, which came first is
**unknowable from daily OHLC**. Recording it as a WIN is how a backtest lies to you,
and it lies in the flattering direction every time.

**Outcome is one of four**, never three:

| Outcome | Meaning |
|---|---|
| `WIN` | target touched, stop not touched |
| `LOSS` | stop touched, target not touched |
| `AMBIGUOUS` | **both touched — order unknowable** |
| `NEITHER` | neither touched; MIS squared off between them |

`AMBIGUOUS` is reported **separately and never folded into wins.** Hit rate is
computed over decisive signals only (`WIN + LOSS`).

**And the ambiguous share is itself a finding.** If it exceeds ~20%, the stop is
sitting inside the day's ordinary noise — the setup is being stopped out by
randomness, not by being wrong. That is a reason to widen the stop *in the design*
(and re-check the R:R), never to widen it mid-trade.

*(Resolving ambiguity properly needs intraday bars — 1-minute data, which is the paid
Connect tier. Defer. The ambiguous count tells you whether it is worth paying for.)*

### 3.2 No hit rate below 30 signals

At n=20, an observed 60% has a 95% interval of roughly **39–78%**. Break-even at 4:1
is 23.3% and at 1:1 is 52.1% — an interval that wide straddles the decision. It is not
a number anyone can act on.

Use the **Wilson score interval**, not the normal approximation, which is badly wrong
at small n and near the extremes. Print the interval beside every estimate.

### 3.3 Judge on the interval floor, never the observed rate

Expectancy is reported three times — at the observed rate, at the CI floor, at the CI
ceiling. **The floor is what you can defend. The observed rate is what luck may have
lent you.** A system that is profitable only at the ceiling is not a system yet; it is
a small sample.

---

## 4. Guardrails it enforces at entry

- **Reject any target below 0.5%** (`PLAN.md` §3). Friction decides outcomes below
  that, not skill. The logger should refuse the entry, not warn.
- **Print the break-even win rate for the R:R being logged**, at log time. Seeing
  "break-even 23.3%" as you record a 4:1 setup is the cheapest possible calibration.
- Position size for expectancy defaults to **₹40,000** (₹10,000 own at 4x, per
  `PLAN.md`), with costs from `tools/zerodha_costs.py`.

---

## 5. Exit gate

**100+ logged signals, 30+ decisive, and a hit rate with its interval.**

Then, and only then:

- Interval floor **above** the break-even for the logged R:R → proceed to phase 2
  (live micro-size, ₹1,000–2,000 positions).
- Interval floor **below** it → either the setup or the R:R is wrong. Change one, log
  another 100. Do not proceed to money.
- Ambiguous share **>20%** → the stop is inside the noise. Fix the design first.

---

## 6. What it deliberately does not do

- **No automated execution.** Phase 1 places no orders and holds no credentials.
- **No strategy.** It measures whatever setup you feed it. Choosing the setup —
  opening-range breakout, VWAP reversion, volume-spike momentum, gap fade — is yours;
  the logger is indifferent and that is the point.
- **No intraday resolution.** See §3.1.
- **No LLM anywhere.** This is arithmetic over a text file.
