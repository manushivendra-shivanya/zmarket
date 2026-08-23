#!/usr/bin/env python3
"""
What does "10% a day" actually require, and what does swing cost vs intraday?

>>> RATES ARE NOT DEFINED HERE. <<<
Everything comes from zerodha_costs.RATES via round_trip(). This file used to
carry its own copy of the rate table, and that copy went stale: it still held
the pre-Oct-2024 NSE turnover charge (0.00297%) months after DECISIONS.md
recorded that exact rate being corrected to 0.00335%. Two rate tables in one
repo means one of them is always wrong and nobody knows which. There is now one.

Rewritten 2026-08-23. Three things in the old version were superseded and are
gone:
  * its own rate table (above);
  * a closing section arguing from a LIVE Rs 2,000/month API fee -- the Personal
    tier is free and nothing is subscribed (PLAN.md S5), so that fee is a
    what-if, not a cost. tools/scenario.py holds the what-if, correctly labelled;
  * "Rs 10,000 -> more than India's GDP inside a year", which DECISIONS.md had
    already corrected to ~82% of it. Overstating a case you are already winning
    is how a good argument gets dismissed.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zerodha_costs import round_trip, breakeven_winrate  # noqa: E402

CAP = 10_000
DAYS = 21
INDIA_GDP = 330e12          # ~Rs 330 lakh crore nominal, FY26 ballpark. Order of
                            # magnitude only -- it is a yardstick, not an input.

print("=" * 80)
print("INTRADAY vs SWING — cost of one round trip")
print("=" * 80)
print(f"{'Position':>10} {'Intraday':>12} {'as %':>9} {'Delivery':>12} {'as %':>9} "
      f"{'Swing is':>10}")
print("-" * 80)
for pos in (3_000, 5_000, 10_000, 25_000, 50_000, 100_000):
    i = round_trip(pos, "MIS")["total"]
    d = round_trip(pos, "CNC")["total"]
    print(f"{pos:>10,} {i:>12.2f} {i/pos*100:>8.3f}% {d:>12.2f} {d/pos*100:>8.3f}% "
          f"{d/i:>9.1f}x")
rt3 = round_trip(3_000, "CNC")
print(f"\n  The flat Rs {rt3['dp']:.2f} DP charge dominates small delivery trades: it is")
print(f"  {rt3['dp']/rt3['total']*100:.0f}% of the cost of a Rs 3,000 round trip, which needs a")
print(f"  {rt3['pct']:.2f}% move just to break even -- ~{rt3['pct']/round_trip(3_000)['pct']:.0f}x the intraday hurdle.")
print("  This is the whole argument for the no-CNC-below-Rs-25,000 rule.")

print()
print("=" * 80)
print("THE 10%/DAY TARGET — what win rate does it need?")
print("=" * 80)
print(f"Capital Rs {CAP:,}, redeployed daily. Target Rs 1,000/day NET (10%).")
print("Three concurrent slots, each slot own-capital/3 at the stated leverage.\n")
print(f"{'Trades/day':>11} {'Pos size':>10} {'Cost/day':>10} {'Gross needed':>13} "
      f"{'@1% tgt':>10} {'@2% tgt':>10}")
print("-" * 80)
for n, lev in ((10, 3), (20, 3), (50, 3), (80, 3)):
    pos = CAP * lev / 3
    rt = round_trip(pos)
    cost = rt["total"] * n
    gross = 1_000 + cost
    # Required NET profit per trade, as a % of position. With a symmetric target
    # T and win rate w, net per trade is T*(2w-1) - c. Setting that equal to the
    # required edge e and solving gives w = ((e + c)/T + 1)/2 -- which is exactly
    # breakeven_winrate with the cost term carrying the edge as well.
    edge = 1_000 / n / pos * 100
    out = []
    for tgt in (1.0, 2.0):
        w = breakeven_winrate(edge + rt["pct"], tgt) * 100
        out.append(f"{w:>9.1f}%" if w <= 100 else "impossible")
    print(f"{n:>11} {pos:>10,.0f} {cost:>10,.0f} {gross:>13,.0f} {out[0]:>10} {out[1]:>10}")
print("\n  Read the last two columns as the win rate that clears Rs 1,000/day NET")
print("  at that trade count, symmetric win/loss. More trades spreads the target")
print("  thinner per trade -- but each one pays the same 0.107% toll.")

print()
print("=" * 80)
print("COMPOUNDING CHECK — why the target needed a second look")
print("=" * 80)
for d, label in ((1, "1 day"), (5, "1 week"), (21, "1 month"), (63, "3 months"),
                 (126, "6 months"), (252, "1 year")):
    v = CAP * (1.10 ** d)
    print(f"  10%/day compounded, {label:>9}: Rs {v:>28,.0f}")
v = CAP * (1.10 ** 252)
print(f"\n  Rs 10,000 -> Rs {v/1e12:,.0f} lakh crore in a year, roughly "
      f"{v/INDIA_GDP*100:.0f}% of India's GDP.")
print("  Stated precisely, because the precise version is damning enough: any")
print("  edge that real would hit its own capacity limit in weeks, and whoever")
print("  found it would not be trading Rs 10,000.")
print("\n  BUT compounding was never the plan -- the same Rs 10,000 is redeployed,")
print("  not reinvested. The fair test is the LINEAR version below, and it is")
print("  still ~40x Renaissance Medallion's record. See DECISIONS.md.")

print()
print("=" * 80)
print("WHAT THE SAME MACHINERY GIVES AT SANE TARGETS  (no platform fee — none is paid)")
print("=" * 80)
print(f"{'Net/month':>12} {'On Rs 10k':>11} {'Per day':>10} {'Verdict':>40}")
print("-" * 80)
for pct, verdict in ((0.5, "noise; a single bad day erases it"),
                     (2, "real but thin"),
                     (5, "a good, defensible result"),
                     (10, "excellent, top-decile"),
                     (20, "exceptional — and rarely sustained"),
                     (210, "what 10%/day actually is, linearly")):
    m = CAP * pct / 100
    print(f"{pct:>11.1f}% {m:>11,.0f} {m/DAYS:>10,.0f}   {verdict:>40}")
print("\n  With the Personal tier at Rs 0, every row above is net. The old version")
print("  of this table judged each row against a Rs 2,000/month fee that is not")
print("  being paid -- which made 5%/month look like a loss when it is a good year.")
