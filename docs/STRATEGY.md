# Strategy catalogue — how money would actually be made

**Written 2026-08-23. Status: six rules implemented and null-tested, none yet run
on real data.** `PHASE-1-SPEC.md` §6 deliberately declined to choose a strategy —
correctly, because the logger should be indifferent. That left the hole this file
fills: **you cannot log signals without a rule that generates them.**

---

## 1. Where the money comes from — and what it costs to find out

At the plan's own target frequency, friction is not a rounding error:

| Position | Trades/day | Cost/month | As % of ₹10,000 capital |
|---|---|---|---|
| ₹40,000 | 1 | ₹900 | 9.0% |
| ₹40,000 | 3.5 | **₹3,150** | **31.5%** |
| ₹16,000 | 3.5 | ₹1,260 | 12.6% |

**A trader with no edge at all, at ₹40,000 × 3.5 trades/day, loses ₹3,150/month
— the ₹10,000 capital in 3.2 months and the full ₹40,000 of contributions in
12.7.** `PLAN.md` §1 accepts "total loss of ₹40,000". That accepted loss *is* the
friction bill of a zero-edge strategy at the stated frequency. The plan already
priced in being wrong; it never said so out loud.

So the goal is not to find a big winner. It is to **learn whether an edge exists
for less than ₹3,150/month** — which is why the backtester exists and why phase 2
is micro-sized.

### The second reason asymmetry matters

`DECISIONS.md` argues for asymmetric R:R because it lowers the break-even win
rate. True, and there is a second argument it does not make. How many decisive
trades are needed before a Wilson floor clears break-even:

| True edge | Break-even | Trades needed | At 3.5/day |
|---|---|---|---|
| 55% | 52.1% (1:1) | **1,130** | 15.4 months |
| 60% | 52.1% (1:1) | 160 | 2.2 months |
| 45% | 23.3% (4:1) | **20** | 0.3 months |
| 30% | 23.3% (4:1) | 160 | 2.2 months |

A marginal 55% edge at 1:1 takes **over a year to detect**, costing ~₹47,000 in
friction to learn. The same setup at 4:1 resolves in weeks. **Asymmetry does not
just lower the bar — it makes the experiment affordable.** Prefer the R:R that
resolves fastest, not merely the one with the lowest break-even.

---

## 2. The four models

A rule with no structural claim behind it is a coincidence waiting to be found.
Every rule in the catalogue names the model it rests on:

| Model | The claim | Rules |
|---|---|---|
| **vol-expansion** | Volatility clusters and mean-reverts: a quiet range is followed by a loud one. The most robust of the four. | `nr7_expansion`, `inside_day` |
| **momentum** | Intraday order-flow imbalance persists. | `gap_and_go`, `orb_15m` |
| **mean-reversion** | Overreaction gets provided liquidity and partially retraces. | `gap_fade`, `pullback_uptrend`, `vwap_reversion` |
| **liquidity** | Stops cluster at obvious levels, so those levels attract price. | `pdh_pdl_break` |

Deliberately **four independent models, not four variations of one.** If three
rules sharing a model all fail, that is one finding, not three.

---

## 3. The catalogue

**Tier `daily` — runnable today, free data, entry at the open:**

| Rule | Model | Fires when |
|---|---|---|
| `gap_fade` | mean-reversion | Open gaps 1.5–8% → fade it |
| `gap_and_go` | momentum | Open gaps 1–5% on above-average volume → go with it |
| `nr7_expansion` | vol-expansion | Yesterday was narrowest range in 7 days |
| `inside_day` | vol-expansion | Yesterday's range inside the day before's |
| `pullback_uptrend` | mean-reversion | 2 down closes while above SMA20 |
| `pdh_pdl_break` | liquidity | Open beyond yesterday's high/low |

**Tier `intraday` — declared, blocked:** `orb_15m` (opening-range breakout, the
intraday workhorse) and `vwap_reversion`. Both need minute bars, which Kite
Personal does not provide. They raise `NotImplementedError` with the reason
rather than silently missing from the list — **the gap between what the daily
tier achieves and what these promise is the only honest argument for paying for
the Connect tier.**

### Targets are in ATR, never in flat percent

`PLAN.md` §3 rule 1 bans rupee-per-share targets: ₹5 is 2.5% of a ₹200 stock and
1.25% of a ₹400 one. **The same argument goes one level further.** A flat 1% is a
routine wiggle on a volatile stock and a major move on a quiet one — so every
rule sizes its target and stop as a multiple of 14-day ATR. A "2:1 setup" then
means the same thing across the whole universe, which is what makes results
comparable at all.

---

## 4. Why this is a filter, not evidence

`tools/backtest.py` scores with the four-outcome rule from `PHASE-1-SPEC.md`
§3.1 — `WIN` / `LOSS` / `AMBIGUOUS` / `NEITHER` — because a daily bar **cannot
order two intraday touches**, and calling that a win is how a backtest lies in
the flattering direction every time. `AMBIGUOUS` is excluded from the hit rate
and booked at its **worst case** in P&L.

It still cannot see spread, slippage, partial fills, queue position, or the fact
that your own order moves the book. **A rule that dies here is dead. A rule that
survives has earned a forward-log — nothing more.** The gate in `PHASE-1-SPEC.md`
§5 is unchanged; the backtest just stops you spending seven weeks forward-logging
a rule that history could have killed in seconds.

### The null test

`tools/selftest.py` runs the whole catalogue over **random walks with no
structure**. Every rule keys on trend, gaps or volatility clustering; the
generator has none; so everything must come back **dead**. It does.

This caught a real bug on its first run. The fixture generator derived each
close from the *previous* close independently of the open — mechanically undoing
every gap by the end of the day, and baking a **−0.375 correlation** between the
overnight gap and the intraday move into supposedly random data. `gap_fade`
scored a **94% hit rate on noise.** The engine was fine; the *null* was not.

**Run `python3 tools/selftest.py` before trusting any leaderboard.** A backtest
that has not proven it finds nothing where nothing exists is decoration.

---

## 5. What is still open

- **Sizing** (`PLAN.md` §8) — ₹40,000 vs ₹16,000 changes the friction bill by
  2.5× and every number in §1 above. Unruled.
- **The universe** — no liquidity floor, price band or ADV minimum is defined,
  so there is nothing to run the catalogue *over*. This is now the binding
  blocker, ahead of any further rule work.
- **Real data** — no bars are in this repo. `data/` is gitignored, and this
  session's network policy blocks Yahoo/NSE/Kite, so bars must be fetched on the
  owner's machine.
- **Parameters are guesses.** Every threshold in the catalogue (`min_gap_pct`,
  `target_atr`, …) was chosen by reasoning, not fitting. They are starting
  points. Fitting them on the same data used to judge them is the fastest way to
  a beautiful backtest and a losing account — hold out a period, or walk forward.
