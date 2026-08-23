#!/usr/bin/env python3
"""
Score any registered strategy on daily bars, net of the real cost model, with an
interval instead of a point estimate. Then rank them against each other.

WHAT THIS IS FOR. PHASE-1-SPEC.md gates phase 2 on "100+ logged signals, 30+
decisive, and a hit rate with its interval". Forward-logging that by hand is ~7
weeks per candidate rule, and it is contaminated: a human choosing which signals
to write down is also, unavoidably, choosing which to omit. A rule applied
mechanically to history reaches the same n in seconds, over far more samples,
with the selection bias removed.

WHAT THIS IS NOT. It is a FILTER, not evidence. It cannot see spread, slippage,
partial fills, queue position, or the fact that your own order moves the book --
PLAN.md S4 is explicit that phase 2 exists precisely because those are
unmodellable here. A rule that dies in backtest is dead. A rule that survives has
earned a forward-log, nothing more.

THE HONEST-SCORING RULE (PHASE-1-SPEC S3.1). A daily bar cannot order two
intraday touches. If the day's range covered BOTH target and stop, which came
first is unknowable, and calling it a win is how a backtest lies in the
flattering direction every single time. Four outcomes, never three:

    WIN        target touched, stop not
    LOSS       stop touched, target not
    AMBIGUOUS  both touched -- ORDER UNKNOWABLE, excluded from the hit rate
    NEITHER    neither touched; MIS squares off at the close, P&L booked there
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zerodha_costs import round_trip                      # noqa: E402
from stats import wilson_interval                         # noqa: E402
from strategies import REGISTRY, LONG, generate, runnable  # noqa: E402

WIN, LOSS, AMBIGUOUS, NEITHER = "WIN", "LOSS", "AMBIGUOUS", "NEITHER"


def score(signal, bar, position, cost=None):
    """Outcome and P&L for one signal against the day it was taken.

    `bar` is the trading day itself -- the strategy never saw it.
    """
    e = signal.entry
    long = signal.direction == LONG
    tgt = e * (1 + signal.target_pct / 100) if long else e * (1 - signal.target_pct / 100)
    stp = e * (1 - signal.stop_pct / 100) if long else e * (1 + signal.stop_pct / 100)

    hit_t = bar.high >= tgt if long else bar.low <= tgt
    hit_s = bar.low <= stp if long else bar.high >= stp

    cost = round_trip(position)["total"] if cost is None else cost
    if hit_t and hit_s:
        # Both touched. Book the WORST case -- assuming the stop came first is
        # the only assumption that cannot flatter the result.
        return AMBIGUOUS, -(position * signal.stop_pct / 100) - cost
    if hit_t:
        return WIN, position * signal.target_pct / 100 - cost
    if hit_s:
        return LOSS, -(position * signal.stop_pct / 100) - cost
    move = (bar.close - e) / e * 100 * (1 if long else -1)
    return NEITHER, position * move / 100 - cost


def run(name, series, position=40_000, cost=None, **overrides):
    """Apply one strategy across {symbol: [Bar, ...]}. Returns a result dict."""
    rows = []
    for symbol, bars in series.items():
        for i in range(1, len(bars)):
            history, today = bars[:i], bars[i]
            sig = generate(name, symbol, history, today.open, date=today.date,
                           **overrides)
            if sig is None:
                continue
            if sig.stop_pct <= 0 or sig.target_pct <= 0:
                continue
            outcome, pnl = score(sig, today, position, cost)
            rows.append((sig, outcome, pnl))

    counts = defaultdict(int)
    for _, o, _ in rows:
        counts[o] += 1
    decisive = counts[WIN] + counts[LOSS]
    lo, hi = wilson_interval(counts[WIN], decisive)
    total = len(rows)
    return {
        "strategy": name, "signals": total, "counts": dict(counts),
        "decisive": decisive,
        "hit_rate": counts[WIN] / decisive if decisive else None,
        "ci": (lo, hi),
        "ambiguous_share": counts[AMBIGUOUS] / total if total else 0.0,
        "pnl": sum(p for _, _, p in rows),
        "pnl_per_signal": sum(p for _, _, p in rows) / total if total else 0.0,
        "avg_rr": (sum(s.rr for s, _, _ in rows) / total) if total else 0.0,
        "rows": rows,
    }


def breakeven_for(rows, position):
    """Average break-even win rate implied by the R:R actually traded."""
    if not rows:
        return None
    cost = round_trip(position)["total"]
    tot = 0.0
    for s, _, _ in rows:
        win = position * s.target_pct / 100 - cost
        loss = position * s.stop_pct / 100 + cost
        tot += loss / (win + loss)
    return tot / len(rows)


def leaderboard(series, position=40_000, tier="daily"):
    results = [run(n, series, position) for n in runnable(tier)]
    print("=" * 100)
    print(f"LEADERBOARD — {len(series)} symbol(s), position Rs {position:,}, "
          f"cost Rs {round_trip(position)['total']:.2f}/round trip")
    print("=" * 100)
    print(f"{'strategy':<18} {'sigs':>5} {'dec':>5} {'amb%':>6} {'hit':>7} "
          f"{'Wilson 95%':>17} {'B/E':>7} {'verdict':>10} {'P&L':>11}")
    print("-" * 100)
    for r in sorted(results, key=lambda x: x["pnl"], reverse=True):
        if not r["decisive"]:
            print(f"{r['strategy']:<18} {r['signals']:>5} {0:>5} "
                  f"{'—':>6} {'—':>7} {'—':>17} {'—':>7} {'no data':>10} {'—':>11}")
            continue
        be = breakeven_for(r["rows"], position)
        lo, hi = r["ci"]
        # The judgement is made on the interval FLOOR, per PHASE-1-SPEC S3.3.
        # The observed rate is what luck may have lent you.
        if r["decisive"] < 30:
            verdict = "n<30"
        elif lo > be:
            verdict = "SURVIVES"
        elif hi < be:
            verdict = "dead"
        else:
            verdict = "unproven"
        print(f"{r['strategy']:<18} {r['signals']:>5} {r['decisive']:>5} "
              f"{r['ambiguous_share']*100:>5.0f}% {r['hit_rate']*100:>6.1f}% "
              f"{f'{lo*100:.1f}–{hi*100:.1f}%':>17} {be*100:>6.1f}% "
              f"{verdict:>10} {r['pnl']:>11,.0f}")
    print("\n  verdict is judged on the interval FLOOR vs the break-even implied by")
    print("  the R:R actually traded — never on the observed rate (S3.3).")
    print("    SURVIVES = floor clears break-even     dead     = ceiling below it")
    print("    unproven = interval straddles it       n<30     = not a number yet")
    print("\n  AMBIGUOUS is excluded from the hit rate and booked at the WORST case")
    print("  in P&L. An ambiguous share above ~20% means the stop is sitting inside")
    print("  the day's ordinary noise (S3.1) — fix the design, not the trade.")
    return results


def load_csv(path, symbol=None):
    """Daily bars from CSV. Accepts the common yfinance/NSE column names.

    Expected header (case-insensitive, order-free):
        date, open, high, low, close, volume
    """
    import csv
    from strategies import Bar
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            r = {k.strip().lower(): v for k, v in r.items() if k}
            try:
                rows.append(Bar(r["date"], float(r["open"]), float(r["high"]),
                                float(r["low"]), float(r["close"]),
                                float(r.get("volume") or 0)))
            except (KeyError, ValueError, TypeError):
                continue        # skip headers repeated mid-file, blanks, N/A rows
    rows.sort(key=lambda b: b.date)
    return symbol or os.path.splitext(os.path.basename(path))[0], rows


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    position = 40_000
    for a in sys.argv[1:]:
        if a.startswith("--position="):
            position = int(a.split("=", 1)[1])

    if not args:
        print(__doc__)
        print("USAGE")
        print("  python3 tools/backtest.py data/*.csv [--position=40000]")
        print("\n  CSV columns: date, open, high, low, close, volume")
        print("\n  No data in this repo — data/ is gitignored and market data is")
        print("  not fetched here. Get daily bars on your own machine, e.g.:")
        print("    import yfinance as yf")
        print("    yf.download('RELIANCE.NS', period='5y')"
              ".to_csv('data/RELIANCE.csv')")
        print("\n  FIRST, always:  python3 tools/selftest.py")
        print("  A leaderboard from an engine that has not passed the null test")
        print("  is decoration.")
        sys.exit(2)

    series = {}
    for path in args:
        sym, bars = load_csv(path)
        if len(bars) < 40:
            print(f"  skipping {sym}: only {len(bars)} bars, need ~40+ for ATR/SMA")
            continue
        series[sym] = bars
    if not series:
        print("No usable series loaded.")
        sys.exit(1)
    span = min(len(b) for b in series.values())
    print(f"Loaded {len(series)} symbol(s), shortest series {span} bars.\n")
    leaderboard(series, position)
