#!/usr/bin/env python3
"""
The allocator, run end to end: Rs 10,000 across six scripts, margin on top,
several time-boxed trades each per day.

Bars here are SYNTHETIC minute data with zero edge -- so every rupee of the
result is friction and luck. That is the point: it prices the MACHINE (how many
trades the design generates, what they cost, how often the circuit breaker
fires) independently of whether any signal works. Swap in real minute bars and
the same numbers become a real answer.
"""
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fixtures import intraday                                          # noqa: E402
from portfolio import (LONG, SHORT, Allocation, Session,               # noqa: E402
                       conviction_weights)
from zerodha_costs import round_trip                                   # noqa: E402

# Conviction, not equal weights -- your Rs 1,500 / Rs 2,000 / Rs 800 example.
CONVICTION = {
    "SUZLON": 2.0,      # most volatile -> most room to reach a target
    "TMPV": 1.6,
    "GLENMARK": 1.5,
    "SBIN": 1.2,
    "DLF": 1.2,
    "ITC": 0.8,         # quietest -> smallest slice
}
PRICES = {"SUZLON": 46.71, "TMPV": 317.70, "GLENMARK": 2317.90,
          "SBIN": 1045.40, "DLF": 678.40, "ITC": 269.80}
VOL = {"SUZLON": 3.5, "TMPV": 2.0, "GLENMARK": 2.2, "SBIN": 1.5,
       "DLF": 2.0, "ITC": 1.1}


def momentum_signal(bars, minute, lookback=15):
    """Placeholder rule: go with the last `lookback` minutes of direction.

    NOT a strategy -- a stand-in so the ENGINE can be measured. Replace with a
    real rule once minute data exists.
    """
    out = []
    for sym, b in bars.items():
        if minute < lookback:
            continue
        now, then = b[minute].close, b[minute - lookback].close
        move = (now - then) / then * 100
        if abs(move) < 0.15:
            continue
        out.append((sym, LONG if move > 0 else SHORT))
    return out


def one_day(seed, leverage, window, box, target, stop, cap=10_000.0,
            daily_cap=-1_000.0):
    bars = {s: intraday(s, PRICES[s], VOL[s], seed=seed * 17 + i)
            for i, s in enumerate(CONVICTION)}
    alloc = Allocation(capital=cap, leverage=leverage,
                       weights=conviction_weights(CONVICTION), max_concurrent=6)
    sess = Session(alloc, daily_cap=daily_cap, window=window, box=box,
                   target_pct=target, stop_pct=stop)
    return sess.run(bars, momentum_signal), alloc


def study(leverage, window, box, target, stop, days=250):
    rows = [one_day(d, leverage, window, box, target, stop)[0]
            for d in range(1, days + 1)]
    nets = sorted(r["net"] for r in rows)
    return {
        "lev": leverage, "window": window, "box": box,
        "trades": statistics.fmean(r["trades"] for r in rows),
        "turnover": statistics.fmean(r["turnover"] for r in rows),
        "cost": statistics.fmean(r["cost"] for r in rows),
        "net": statistics.fmean(nets),
        "median": nets[len(nets) // 2],
        "p05": nets[int(len(nets) * .05)], "p95": nets[int(len(nets) * .95)],
        "halted": sum(1 for r in rows if r["halted"]) / len(rows),
        "hold": statistics.fmean(r["avg_hold"] for r in rows),
    }


if __name__ == "__main__":
    a = Allocation(capital=10_000, leverage=4.0,
                   weights=conviction_weights(CONVICTION))
    print("=" * 84)
    print("THE ALLOCATION — Rs 10,000 split by conviction, 4x margin on each slice")
    print("=" * 84)
    print(f"{'script':<12} {'weight':>8} {'own Rs':>9} {'position':>10} "
          f"{'price':>9} {'qty':>6} {'1% is':>8}")
    print("-" * 84)
    tot_own = tot_pos = 0
    for s in CONVICTION:
        own, pos = a.slice_for(s), a.position_value(s)
        qty = int(pos // PRICES[s])
        tot_own += own; tot_pos += pos
        print(f"{s:<12} {a.weights[s]:>7.1%} {own:>9,.0f} {pos:>10,.0f} "
              f"{PRICES[s]:>9,.2f} {qty:>6} {pos*0.01:>8,.0f}")
    print("-" * 84)
    print(f"{'TOTAL':<12} {'100%':>8} {tot_own:>9,.0f} {tot_pos:>10,.0f}")
    print(f"\n  Own capital Rs {tot_own:,.0f}; buying power Rs {tot_pos:,.0f} at 4x.")
    print(f"  Note ITC: Rs {a.slice_for('ITC'):,.0f} own -> "
          f"{int(a.position_value('ITC')//PRICES['ITC'])} shares. Small slices on")
    print(f"  high-priced scripts round down badly -- GLENMARK at Rs 2,318 needs")
    print(f"  Rs {2317.90/4:,.0f} own just to buy ONE share at 4x.")

    print()
    print("=" * 84)
    print("WHAT THE DESIGN COSTS — 250 simulated days, ZERO edge, friction only")
    print("=" * 84)
    print(f"{'lev':>4} {'window':>7} {'box':>5} {'trades/d':>9} {'turnover/d':>12} "
          f"{'cost/d':>8} {'cost/mo':>9} {'%cap/mo':>8} {'cap hit':>8}")
    print("-" * 84)
    for lev in (1.0, 4.0):
        for window, box in ((15, 30), (30, 60), (60, 120)):
            s = study(lev, window, box, 0.6, 0.3, days=250)
            print(f"{lev:>3.0f}x {window:>6}m {box:>4}m {s['trades']:>9.1f} "
                  f"{s['turnover']:>12,.0f} {s['cost']:>8,.0f} {s['cost']*21:>9,.0f} "
                  f"{s['cost']*21/10_000*100:>7.0f}% {s['halted']:>7.0%}")
    print("\n  'cap hit' = share of days the -Rs 1,000 circuit breaker fired.")
    print("  Every row has NO edge, so net P&L is just the friction bill and noise.")

    print()
    print("=" * 84)
    print("THE TIME BOX — can a position make its target before the box expires?")
    print("=" * 84)
    print(f"{'target':>7} {'stop':>6} {'R:R':>6} {'trades/d':>9} {'TARGET':>7} "
          f"{'STOP':>6} {'BOX':>6} {'AMBIG':>7}  {'net/day':>9}")
    print("-" * 84)
    for target, stop in ((0.3, 0.15), (0.6, 0.3), (1.0, 0.5), (2.0, 0.5)):
        rows = [one_day(d, 4.0, 15, 30, target, stop)[0] for d in range(1, 251)]
        rs = {}
        for r in rows:
            for k, v in r["reasons"].items():
                rs[k] = rs.get(k, 0) + v
        n = sum(rs.values()) or 1
        print(f"{target:>6.1f}% {stop:>5.2f}% {target/stop:>5.1f}:1 "
              f"{statistics.fmean(r['trades'] for r in rows):>9.1f} "
              f"{rs.get('TARGET',0)/n:>6.0%} {rs.get('STOP',0)/n:>5.0%} "
              f"{rs.get('BOX',0)/n:>5.0%} {rs.get('AMBIGUOUS',0)/n:>6.0%}  "
              f"{statistics.fmean(r['net'] for r in rows):>9,.0f}")
    print("\n  BOX = the box expired with neither level touched, so the position")
    print("  closed at whatever the market happened to be. A high BOX share means")
    print("  the target is too far for the time allowed -- the two must be sized")
    print("  TOGETHER. That pairing is the design decision this whole file exists")
    print("  to expose, and it is invisible in a daily-bar model.")
