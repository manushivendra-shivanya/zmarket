#!/usr/bin/env python3
"""
Both sides capped: a profit TARGET and a STOP LOSS. Not symmetric.

This is the single biggest lever in the plan and the earlier models missed it.
Assuming win == loss forces the break-even win rate to ~52%. Capping the
downside tighter than the upside collapses it.

    break-even w = (S*p + c) / (p*(T + S))

    T = target %, S = stop %, p = position, c = round-trip cost

THE HONEST COUNTER-PRESSURE: a tighter stop is hit more often by ordinary noise.
Win rate FALLS as the stop tightens, so R:R and win rate trade against each
other. The product is what matters, and only measurement settles where the
optimum sits for a given universe -- that is phase 1's job.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zerodha_costs import round_trip

CAP, LEV, DAYS = 10_000, 4, 21
POS  = CAP * LEV
COST = round_trip(POS)["total"]


def outcome(target_pct, stop_pct):
    win  = POS * target_pct / 100 - COST
    loss = -(POS * stop_pct / 100 + COST)
    be   = abs(loss) / (win + abs(loss)) if win + abs(loss) else 1.0
    return win, loss, be


print("=" * 78)
print(f"BREAK-EVEN WIN RATE BY RISK:REWARD   (Rs {POS:,} position, cost Rs {COST:.2f})")
print("=" * 78)
print(f"{'Target':>8} {'Stop':>7} {'R:R':>6} {'Win':>8} {'Loss':>8} {'B/E win rate':>14}")
print("-" * 78)
for target, stop in ((2.6,2.6),(2.6,1.73),(2.6,1.3),(2.6,0.87),(2.6,0.65),
                     (2.0,1.0),(1.5,0.75),(1.5,0.5),(1.0,0.5),(1.0,0.33)):
    w, l, be = outcome(target, stop)
    print(f"{target:>7.2f}% {stop:>6.2f}% {target/stop:>5.1f}:1 "
          f"{w:>8,.0f} {l:>8,.0f} {be*100:>13.1f}%")
print("\n  Symmetric (1:1) needs 52%. At 2:1 it is ~36%. At 4:1 it is ~22%.")
print("  You can be WRONG most of the time and still make money -- if the")
print("  stop is honoured every single time without exception.")

print()
print("=" * 78)
print("EXPECTED Rs/DAY — one trade per day, by R:R and win rate")
print("=" * 78)
print(f"{'R:R':>7}", end="")
for wr in (0.30,0.35,0.40,0.45,0.50,0.55,0.60): print(f"{int(wr*100):>10}%", end="")
print("\n" + "-" * 78)
for target, stop in ((2.6,2.6),(2.6,1.3),(2.6,0.87),(2.6,0.65),(1.5,0.5)):
    w, l, _ = outcome(target, stop)
    print(f"{target/stop:>6.1f}:1", end="")
    for wr in (0.30,0.35,0.40,0.45,0.50,0.55,0.60):
        print(f"{wr*w + (1-wr)*l:>11,.0f}", end="")
    print()

print()
print("=" * 78)
print("WHAT REACHES Rs 1,000/DAY — AND WHY ONE TRADE A DAY CANNOT")
print("=" * 78)
w, l, _ = outcome(2.6, 0.65)
print(f"  A single 4:1 trade wins at most Rs {w:,.0f}. So Rs 1,000/day is")
print(f"  UNREACHABLE with one trade a day at a 2.6% target -- even at a 100%")
print(f"  win rate. It needs more trades, a bigger target, or more capital.\n")
print(f"{'R:R':>7} {'Win rate':>10} {'Rs/trade':>10} {'Trades/day for Rs 1,000':>25}")
print("-" * 78)
for target, stop in ((2.6,1.3),(2.6,0.87),(2.6,0.65)):
    w, l, _ = outcome(target, stop)
    for wr in (0.35, 0.45, 0.55):
        ev = wr*w + (1-wr)*l
        n = 1_000/ev if ev > 0 else float("inf")
        txt = f"{n:.1f}" if ev > 0 else "never"
        print(f"{target/stop:>6.1f}:1 {wr*100:>9.0f}% {ev:>10,.0f} {txt:>25}")
print("\n  At 4:1 and 45% accuracy: Rs 282/trade, so ~3.5 trades/day reaches")
print("  Rs 1,000. THAT is the coherent version of the target -- and it is a")
print("  frequency question, not a bigger-win question.")

print()
print("=" * 78)
print("THE CATCH — a stop only helps if it is never widened")
print("=" * 78)
w, l, _ = outcome(2.6, 0.65)
print(f"  4:1 setup: win +Rs {w:,.0f}, loss -Rs {abs(l):,.0f}, break-even 22%\n")
for skip in (0, 1, 2, 3):
    # one 'let it run' per month turns a stop-loss into a full 2.6% adverse move
    base = 0.45 * w + 0.55 * l
    full = -(POS * 2.6 / 100 + COST)
    month = base * (DAYS - skip) + full * skip
    print(f"  {skip} widened stop{'s' if skip != 1 else ' '} in a month: "
          f"Rs {month:>7,.0f}"
          f"{'   <-- the edge is gone' if month < 0 else ''}")
print("\n  Three widened stops cut a Rs 5,925 month to Rs 1,830 -- a 69% haircut")
print("  from three moments of discretion. This is why 'never widen a stop' is a")
print("  hard rule, not a preference. Zerodha's Cover Order (CO) enforces a stop")
print("  at entry, which is worth using precisely because it removes the choice.")
