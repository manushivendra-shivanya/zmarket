#!/usr/bin/env python3
"""
Run the portfolio allocator on REAL intraday bars, day by day.

    python3 tools/fetch_data.py --intraday
    python3 tools/backtest_intraday.py data/intraday/*.csv

This is the tool that decides whether the paid Kite Connect tier is worth buying.
The 15/30-minute window model cannot be tested on daily bars, and Kite's free
Personal tier serves no market data -- which looked like a forced upgrade. It is
not: Yahoo serves 15-minute bars over roughly 60 days for free, and 60 days is
enough to find out whether the window/box design clears friction at all. Pay for
data only to scale a design that has already survived on free data.

Bars are grouped by CALENDAR DAY and each day is run as an independent session:
positions never carry overnight (MIS squares off ~15:20, PLAN.md S3 rule 6), and
capital resets each morning to the fixed Rs 10,000 -- no compounding, per the
target ruling in DECISIONS.md.
"""
import csv
import os
import statistics
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from portfolio import (LONG, SHORT, Allocation, MinuteBar,          # noqa: E402
                       Session, conviction_weights)
from zerodha_costs import round_trip                                # noqa: E402


def load_intraday(path):
    """{'YYYY-MM-DD': [MinuteBar, ...]} from a CSV with a Date/Datetime column."""
    days = defaultdict(list)
    sym = os.path.splitext(os.path.basename(path))[0]
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            r = {k.strip().lower(): v for k, v in r.items() if k}
            ts = r.get("date") or r.get("datetime")
            if not ts:
                continue
            try:
                bar = MinuteBar(len(days[ts[:10]]), float(r["open"]), float(r["high"]),
                                float(r["low"]), float(r["close"]))
            except (KeyError, ValueError, TypeError):
                continue        # repeated headers, blanks, N/A rows
            days[ts[:10]].append(bar)
    return sym, dict(days)


def infer_bar_minutes(days):
    """Bars per session -> minutes per bar. NSE runs 375 minutes."""
    counts = [len(v) for v in days.values() if len(v) > 2]
    if not counts:
        return 15
    typical = statistics.median(counts)
    return max(1, int(round(375 / typical)))


def momentum(bars, i, lookback=1):
    out = []
    for sym, b in bars.items():
        if i < lookback:
            continue
        now, then = b[i].close, b[i - lookback].close
        move = (now - then) / then * 100
        if abs(move) < 0.15:
            continue
        out.append((sym, LONG if move > 0 else SHORT))
    return out


def run(paths, capital=10_000.0, leverage=4.0, window=30, box=60,
        target=0.6, stop=0.3, daily_cap=-1_000.0, conviction=None):
    series = {}
    for p in paths:
        sym, days = load_intraday(p)
        if days:
            series[sym] = days
    if not series:
        return None
    bar_min = infer_bar_minutes(next(iter(series.values())))
    common = sorted(set.intersection(*(set(d) for d in series.values())))
    weights = conviction_weights(conviction or {s: 1.0 for s in series})

    results, halted = [], 0
    for day in common:
        bars = {s: series[s][day] for s in series if len(series[s].get(day, [])) > 3}
        if len(bars) < 2:
            continue
        alloc = Allocation(capital=capital, leverage=leverage,
                           weights={k: v for k, v in weights.items() if k in bars},
                           max_concurrent=len(bars))
        sess = Session(alloc, daily_cap=daily_cap, window=window, box=box,
                       target_pct=target, stop_pct=stop, bar_minutes=bar_min)
        s = sess.run(bars, momentum)
        results.append(s)
        halted += bool(s["halted"])
    return {"bar_minutes": bar_min, "days": len(results), "symbols": len(series),
            "results": results, "halted": halted}


def report(r, label):
    if not r or not r["days"]:
        print(f"  {label}: no usable sessions")
        return
    res = r["results"]
    nets = sorted(x["net"] for x in res)
    trades = sum(x["trades"] for x in res)
    cost = sum(x["cost"] for x in res)
    gross = sum(x["gross"] for x in res)
    reasons = defaultdict(int)
    for x in res:
        for k, v in x["reasons"].items():
            reasons[k] += v
    n = sum(reasons.values()) or 1
    print(f"  {label}")
    print(f"    {r['days']} sessions · {trades} trades "
          f"({trades/r['days']:.1f}/day) · {r['bar_minutes']}-min bars")
    print(f"    gross Rs {gross:>10,.0f}   friction Rs {cost:>9,.0f}   "
          f"NET Rs {sum(nets):>10,.0f}")
    print(f"    TARGET {reasons['TARGET']/n:.0%}  STOP {reasons['STOP']/n:.0%}  "
          f"BOX {reasons['BOX']/n:.0%}  SQUAREOFF {reasons['SQUAREOFF']/n:.0%}  "
          f"AMBIG {reasons['AMBIGUOUS']/n:.0%}")
    print(f"    median day Rs {nets[len(nets)//2]:>8,.0f}   "
          f"worst Rs {nets[0]:>8,.0f}   best Rs {nets[-1]:>8,.0f}   "
          f"cap hit {r['halted']/r['days']:.0%} of days")
    print()


if __name__ == "__main__":
    paths = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not paths:
        print(__doc__)
        print("No files given.\n")
        print("  python3 tools/fetch_data.py --intraday")
        print("  python3 tools/backtest_intraday.py data/intraday/*.csv\n")
        print("  If zsh says 'no matches found', the fetch has not run yet.")
        sys.exit(2)

    print("=" * 80)
    print("PORTFOLIO ON REAL INTRADAY BARS")
    print("=" * 80)
    print("  Rs 10,000 own capital, reset every morning. Momentum entry is a")
    print("  PLACEHOLDER rule -- this measures the DESIGN (windows, boxes, friction,")
    print("  the circuit breaker), not a strategy worth trading.\n")
    for lev in (1.0, 4.0):
        for window, box in ((30, 60), (60, 120)):
            r = run(paths, leverage=lev, window=window, box=box)
            report(r, f"{lev:.0f}x leverage · {window}-min window · {box}-min box")
    print("  Read the BOX share first: high BOX means the target is unreachable in")
    print("  the time allowed, so the two must be resized together before anything")
    print("  else in the design is worth tuning.")
