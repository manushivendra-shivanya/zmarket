#!/usr/bin/env python3
"""
"What would last week have made?" -- and why one week cannot answer it.

THE QUESTION. Ten watched symbols, Rs 10,000 own capital plus MIS margin, the
six daily-tier rules, one trading week. What is the P&L?

THE PROBLEM. A week is ~5 sessions. Across 10 symbols that is 50 symbol-days,
which yields a couple of dozen signals and maybe a dozen DECISIVE ones. PHASE-1
-SPEC S3.2 refuses to report a hit rate below n=30 precisely because an interval
that wide straddles every threshold in the plan. So the honest answer to "what
would last week have made" is not a number -- it is a RANGE, and the width of
that range is the finding.

This tool measures that width. It runs thousands of independent 5-day windows
and reports the distribution of outcomes. Feed it real bars and it does the same
thing over real history.

WHAT IT ADDS over backtest.py: portfolio-level capital accounting. The daily
loss cap from PLAN.md S3 (-Rs 1,000, stop for the day, no exceptions) is a
PORTFOLIO rule -- it cannot be seen one trade at a time, and nothing in this repo
had ever simulated it. It binds more often than anyone assumed.
"""
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backtest import run                                   # noqa: E402
from fixtures import random_walk                           # noqa: E402
from stats import wilson_interval                          # noqa: E402
from strategies import runnable                            # noqa: E402
from zerodha_costs import round_trip                       # noqa: E402

# Plausible daily volatilities for the watched names. ESTIMATES, not measured --
# they set the character of the simulation, not any conclusion. Replace with
# measured ATR the moment real bars exist.
WATCH_VOL = {
    "HINDUNILVR": 1.0, "TCS": 1.2, "SUZLON": 3.5, "GLENMARK": 2.2, "ITC": 1.1,
    "SBIN": 1.5, "M&MFIN": 2.0, "TMPV": 2.0, "DLF": 2.0, "ULTRACEMCO": 1.2,
}
PRICES = {
    "HINDUNILVR": 2015, "TCS": 2302, "SUZLON": 46.71, "GLENMARK": 2317.9,
    "ITC": 269.8, "SBIN": 1045.4, "M&MFIN": 380.2, "TMPV": 317.7,
    "DLF": 678.4, "ULTRACEMCO": 11551,
}
DAILY_CAP = -1_000.0


def one_window(seed, position, window=5, warmup=40, cap=DAILY_CAP):
    """One independent 5-session week across the watchlist.

    Returns (pnl_uncapped, pnl_capped, n_signals, n_wins, n_decisive, cap_days).
    """
    series = {}
    for i, (sym, vol) in enumerate(WATCH_VOL.items()):
        _, bars = random_walk(sym, n=warmup + window, start=PRICES[sym],
                              daily_vol_pct=vol, seed=seed * 100 + i)
        series[sym] = bars

    # Collect every signal in the window, tagged by day.
    by_day = {}
    wins = dec = 0
    for name in runnable("daily"):
        r = run(name, series, position)
        for sig, outcome, pnl in r["rows"]:
            day = sig.date
            if day < f"D{warmup:04d}":
                continue                      # warmup, not part of the week
            by_day.setdefault(day, []).append((sig, outcome, pnl))
            if outcome == "WIN":
                wins += 1; dec += 1
            elif outcome == "LOSS":
                dec += 1

    uncapped = capped = 0.0
    n = 0
    cap_days = 0
    for day in sorted(by_day):
        day_total = 0.0
        stopped = False
        for sig, outcome, pnl in by_day[day]:
            n += 1
            uncapped += pnl
            if stopped:
                continue                       # cap hit: no more trades today
            capped += pnl
            day_total += pnl
            if day_total <= cap:
                stopped = True
                cap_days += 1
    return uncapped, capped, n, wins, dec, cap_days


def study(position, trials=400, window=5):
    rows = [one_window(s, position, window) for s in range(1, trials + 1)]
    unc = sorted(r[0] for r in rows)
    cap = sorted(r[1] for r in rows)
    sigs = [r[2] for r in rows]
    dec = [r[4] for r in rows]
    capdays = [r[5] for r in rows]

    def pct(xs, p):
        return xs[min(len(xs) - 1, int(len(xs) * p))]

    return {
        "position": position, "trials": trials,
        "median_unc": pct(unc, .5), "median_cap": pct(cap, .5),
        "p05": pct(cap, .05), "p25": pct(cap, .25),
        "p75": pct(cap, .75), "p95": pct(cap, .95),
        "best": cap[-1], "worst": cap[0],
        "mean_sigs": statistics.fmean(sigs), "mean_dec": statistics.fmean(dec),
        "losing_share": sum(1 for x in cap if x < 0) / len(cap),
        "cap_hit_share": sum(1 for c in capdays if c) / len(capdays),
        "mean_cap_days": statistics.fmean(capdays),
    }


if __name__ == "__main__":
    print("=" * 84)
    print("ONE TRADING WEEK — 10 watched symbols, all 6 daily rules")
    print("=" * 84)
    print("  Bars are SIMULATED (random walks at each name's plausible volatility).")
    print("  Market data is unreachable from this sandbox, so this measures the")
    print("  NOISE FLOOR: how much a one-week result swings on luck alone, when the")
    print("  true edge is exactly ZERO. Any real week must be read against this.\n")

    results = []
    for pos, label in ((40_000, "Rs 10,000 own x 4 — ALL-IN, what the R:R tools assume"),
                       (16_000, "Rs  4,000 own x 4 — PLAN S1 maximum per trade"),
                       (8_000,  "Rs  2,000 own x 4 — PLAN S1 typical")):
        s = study(pos)
        results.append((label, s))
        print(f"  {label}")
        print(f"    signals/week {s['mean_sigs']:>5.1f}   decisive {s['mean_dec']:>5.1f}"
              f"   friction alone Rs {round_trip(pos)['total']*s['mean_sigs']:>7,.0f}")
        print(f"    median week  Rs {s['median_cap']:>8,.0f}"
              f"   (no daily cap: Rs {s['median_unc']:>8,.0f})")
        print(f"    5th–95th     Rs {s['p05']:>8,.0f}  ..  Rs {s['p95']:>8,.0f}"
              f"   spread Rs {s['p95']-s['p05']:,.0f}")
        print(f"    worst/best   Rs {s['worst']:>8,.0f}  ..  Rs {s['best']:>8,.0f}")
        print(f"    losing weeks {s['losing_share']:>5.0%}"
              f"   weeks hitting the -Rs1,000 daily cap {s['cap_hit_share']:>4.0%}")
        print()

    print("=" * 84)
    print("WHAT A ONE-WEEK NUMBER IS WORTH")
    print("=" * 84)
    s = results[0][1]
    lo, hi = wilson_interval(round(s["mean_dec"] * 0.5), round(s["mean_dec"]))
    print(f"  A week yields ~{s['mean_dec']:.0f} decisive trades. Even at a perfect")
    print(f"  coin-flip 50%, the Wilson 95% interval on that sample is "
          f"{lo:.0%}–{hi:.0%}.")
    print(f"  Break-even for these rules sits inside that range, so the week")
    print(f"  CANNOT distinguish a real edge from none. PHASE-1-SPEC S3.2's n>=30")
    print(f"  floor is roughly {30/s['mean_dec']:.0f} weeks of this watchlist.\n")
    print(f"  The spread between a 5th-percentile and 95th-percentile week at")
    print(f"  Rs 40,000 is Rs {results[0][1]['p95']-results[0][1]['p05']:,.0f} — "
          f"{(results[0][1]['p95']-results[0][1]['p05'])/10_000:.1f}x the entire")
    print(f"  Rs 10,000 of capital. A good week and a bad week look nothing alike")
    print(f"  even when the underlying edge is identical, and zero.")
