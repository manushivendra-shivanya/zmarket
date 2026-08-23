#!/usr/bin/env python3
"""
Prove the backtest engine does not manufacture edges. Run before trusting it.

    python3 tools/selftest.py        # exits 1 if the engine invents an edge
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backtest import (AMBIGUOUS, LOSS, NEITHER, WIN, breakeven_for,  # noqa: E402
                      leaderboard, run, score)
from fixtures import universe                                        # noqa: E402
from strategies import Bar, Signal, LONG, SHORT, runnable            # noqa: E402
from zerodha_costs import round_trip                                 # noqa: E402

POS = 40_000
failures = []


def check(label, ok, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{'  — ' + detail if detail else ''}")
    if not ok:
        failures.append(label)


print("=" * 78)
print("1. SCORING — the four outcomes, on hand-built bars")
print("=" * 78)
sig = Signal("D1", "T", "s", LONG, 100.0, 2.0, 1.0, "r")      # tgt 102, stop 99
cost = round_trip(POS)["total"]
for label, bar, want_o, want_p in [
    ("target only -> WIN",       Bar("D1", 100, 102.5, 99.5, 102), WIN,   POS*0.02 - cost),
    ("stop only -> LOSS",        Bar("D1", 100, 101.0, 98.5, 99),  LOSS, -POS*0.01 - cost),
    ("both -> AMBIGUOUS",        Bar("D1", 100, 102.5, 98.5, 101), AMBIGUOUS, -POS*0.01 - cost),
    ("neither -> NEITHER@close", Bar("D1", 100, 101.5, 99.5, 101), NEITHER, POS*0.01 - cost),
]:
    o, p = score(sig, bar, POS)
    check(label, o == want_o and abs(p - want_p) < 0.01, f"{o}, P&L {p:,.2f}")

short = Signal("D1", "T", "s", SHORT, 100.0, 2.0, 1.0, "r")   # tgt 98, stop 101
o, p = score(short, Bar("D1", 100, 100.5, 97.5, 98), POS)
check("SHORT mirrors correctly", o == WIN and abs(p - (POS*0.02 - cost)) < 0.01, f"{o}")

o, _ = score(sig, Bar("D1", 100, 102.5, 98.5, 101), POS)
_, p_amb = score(sig, Bar("D1", 100, 102.5, 98.5, 101), POS)
check("AMBIGUOUS books the WORST case, never the win", p_amb < 0, f"P&L {p_amb:,.2f}")

print()
print("=" * 78)
print("2. NO LOOKAHEAD — a strategy must not see the bar it is scored against")
print("=" * 78)
seen = {}
import strategies                                                    # noqa: E402
orig = strategies.REGISTRY["gap_fade"].fn


def spy(symbol, history, today_open, p):
    seen["n_history"] = len(history)
    seen["last_date"] = history[-1].date
    return orig(symbol, history, today_open, p)


strategies.REGISTRY["gap_fade"].fn = spy
uni = universe(n_symbols=1, n=60, seed=1)
run("gap_fade", uni, POS)
strategies.REGISTRY["gap_fade"].fn = orig
bars = list(uni.values())[0]
check("history stops strictly before the traded day",
      seen.get("last_date") == bars[-2].date,
      f"last history bar {seen.get('last_date')}, traded day {bars[-1].date}")

print()
print("=" * 78)
print("3. THE NULL TEST — random walks, 12 symbols x 750 days, no real structure")
print("=" * 78)
print("   Every rule keys on trend, gaps or volatility clustering. The generator")
print("   has none. Anything that SURVIVES here is a bug, not an edge.\n")
uni = universe(n_symbols=12, n=750, seed=7)
results = leaderboard(uni, POS)

print()
survivors = [r["strategy"] for r in results
             if r["decisive"] >= 30
             and r["ci"][0] > (breakeven_for(r["rows"], POS) or 1)]
check("no strategy beats break-even on random data",
      not survivors, f"survivors: {survivors or 'none'}")

profitable = [r["strategy"] for r in results if r["pnl"] > 0]
check("no strategy is net profitable after costs on random data",
      not profitable, f"profitable: {profitable or 'none'}")

sampled = [r for r in results if r["decisive"] >= 30]
check("engine produced a usable sample to judge",
      len(sampled) >= 3, f"{len(sampled)} strategies reached n>=30")

print()
print("=" * 78)
print("4. COSTS ARE ACTUALLY DEDUCTED — measured, not assumed")
print("=" * 78)
for name in ("gap_fade", "inside_day"):
    priced = run(name, uni, POS)
    free = run(name, uni, POS, cost=0.0)
    n = priced["signals"]
    diff = free["pnl"] - priced["pnl"]
    check(f"{name}: charged exactly {n} x Rs {cost:.2f}",
          abs(diff - n * cost) < 0.01,
          f"free-minus-priced Rs {diff:,.2f} vs expected Rs {n*cost:,.2f}")

print()
print("=" * 78)
print("VERDICT")
print("=" * 78)
if failures:
    print(f"  {len(failures)} FAILURE(S): " + "; ".join(failures))
    print("  Do NOT trust any backtest number until these pass.")
    sys.exit(1)
print("  Engine finds no edge where none exists, never peeks at the scored bar,")
print("  books ambiguity at its worst, and charges every trade. Fit to use as a")
print("  FILTER on real data — still not evidence. Only phase 2 is that.")
