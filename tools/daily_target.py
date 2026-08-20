#!/usr/bin/env python3
"""
Rs 10,000 capital, redeployed daily, NOT compounded. What does Rs 1,000/day need?

The honest reframing: with 4x intraday margin, Rs 10,000 controls Rs 40,000. So
"10% of capital" is only a 2.5% move on the POSITION. Stated that way the target
stops sounding absurd -- and the real constraint turns out to be variance, not
the size of the move.
"""
import random
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zerodha_costs import round_trip

CAP = 10_000
DAYS = 21

print("=" * 76)
print("WHAT MOVE DOES Rs 1,000/DAY ACTUALLY NEED?")
print("=" * 76)
print(f"{'Lev':>4} {'Position':>10} {'Cost':>8} {'Move for Rs1,000 net':>22}")
print("-" * 76)
for lev in (1, 2, 3, 4):
    pos = CAP * lev
    cost = round_trip(pos)["total"]
    move = (1_000 + cost) / pos * 100
    print(f"{lev:>3}x {pos:>10,} {cost:>8.2f} {move:>21.2f}%")
print("\n  At 4x it is ONE correct 2.6% call per day. That is a normal intraday")
print("  range on plenty of liquid stocks. The move is not the hard part.")

print()
print("=" * 76)
print("THE HARD PART — the loss is the same size as the win")
print("=" * 76)
lev, target = 4, 0.026
pos = CAP * lev
cost = round_trip(pos)["total"]
win, loss = pos * target - cost, -(pos * target + cost)
print(f"4x, Rs {pos:,} position, {target*100:.1f}% target:")
print(f"  correct  -> +Rs {win:,.0f}")
print(f"  wrong    -> -Rs {abs(loss):,.0f}")
print(f"  break-even win rate: {abs(loss)/(win+abs(loss))*100:.1f}%\n")
print(f"{'Win rate':>9} {'Rs/day avg':>12} {'Rs/month':>12} {'% of capital/mo':>17}")
print("-" * 76)
for wr in (0.50, 0.55, 0.58, 0.60, 0.65, 0.70):
    d = wr * win + (1 - wr) * loss
    print(f"{wr*100:>8.0f}% {d:>12,.0f} {d*DAYS:>12,.0f} {d*DAYS/CAP*100:>16.0f}%")
print("\n  Rs 1,000/day average needs a ~100% win rate. But 60% still yields")
print("  ~Rs 165/day = ~35%/month on capital, because leverage amplifies")
print("  return ON CAPITAL even when return per trade is ordinary.")

print()
print("=" * 76)
print("WHY THAT 33%/MONTH IS NOT FREE — variance, 20,000 simulated months")
print("=" * 76)
random.seed(7)   # fixed so this is reproducible
print(f"{'Win rate':>9} {'Median mo':>11} {'Worst 5%':>11} {'P(losing mo)':>14} {'P(ruin)':>9}")
print("-" * 76)
for wr in (0.55, 0.58, 0.60, 0.65):
    months, ruins = [], 0
    for _ in range(20_000):
        equity, total = CAP, 0.0
        busted = False
        for _ in range(DAYS):
            total += win if random.random() < wr else loss
            if CAP + total <= 0:          # capital gone
                busted = True
                break
        months.append(total)
        ruins += busted
    months.sort()
    med = months[len(months)//2]
    p5  = months[int(len(months)*0.05)]
    neg = sum(1 for m in months if m < 0) / len(months) * 100
    print(f"{wr*100:>8.0f}% {med:>11,.0f} {p5:>11,.0f} {neg:>13.0f}% {ruins/200:>8.2f}%")
print("\n  Even with a GENUINE 60% edge, roughly a quarter of months lose money,")
print("  and the worst 5% of months lose several thousand rupees. A losing month")
print("  is not evidence the system is broken -- which is exactly why the daily")
print("  loss cap and a pre-committed sample size matter more than the target.")
