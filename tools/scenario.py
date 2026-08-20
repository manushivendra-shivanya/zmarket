from zerodha_costs import round_trip

DAYS = 21

# PLATFORM FEE. Rs 0 - nothing is subscribed (PLAN.md S5). This is NOT the
# Rs 2,000-4,000 per-trade capital below; the two are unrelated and confusing
# them cost a round of analysis on 2026-08-20. Set non-zero only to re-test the
# no-subscription decision.
PLATFORM_FEE_MONTH = 0

def trade(own, lev, price, move):
    pos    = own * lev
    shares = int(pos // price)
    actual = shares * price
    cost   = round_trip(actual)["total"] if shares else 0
    gross  = shares * move
    return shares, actual, cost, gross - cost, -(gross + cost)

print("="*84)
print("Rs 2,000-4,000 OWN capital per trade, margin ON TOP")
print("="*84)
print(f"{'Own':>6} {'Lev':>4} {'Position':>9} {'Price':>6} {'Sh':>4} {'Cost':>6} "
      f"{'WIN':>7} {'LOSS':>7} {'B/E':>7}")
print("-"*84)
setups = []
for own in (2_000, 4_000):
    for lev in (2, 4):
        for price in (200, 400):
            sh, act, cost, w, l = trade(own, lev, price, 5)
            be = abs(l)/(w+abs(l))*100 if (w+abs(l)) else 0
            setups.append((own, lev, price, w, l, be))
            print(f"{own:>6,} {lev:>3}x {act:>9,} {price:>6} {sh:>4} {cost:>6.2f} "
                  f"{w:>7,.0f} {l:>7,.0f} {be:>6.1f}%")

print()
print("="*84)
print("MONTHLY P&L — 42 trades (2/day x 21 days)")
print("="*84)
print(f"{'Setup':>18}", end="")
for wr in (0.55,0.60,0.65,0.70,0.80): print(f"{int(wr*100):>11}%", end="")
print("\n" + "-"*84)
for own,lev,price,w,l,be in setups:
    print(f"{f'Rs{own:,} {lev}x @{price}':>18}", end="")
    for wr in (0.55,0.60,0.65,0.70,0.80):
        print(f"{wr*42*w + (1-wr)*42*l:>12,.0f}", end="")
    print()

print()
print("="*84)
print("SENSITIVITY — same, if a monthly platform fee were paid")
print("="*84)
print(f"{'Setup':>18}", end="")
for wr in (0.55,0.60,0.65,0.70,0.80): print(f"{int(wr*100):>11}%", end="")
print("\n" + "-"*84)
for own,lev,price,w,l,be in setups:
    print(f"{f'Rs{own:,} {lev}x @{price}':>18}", end="")
    for wr in (0.55,0.60,0.65,0.70,0.80):
        v = wr*42*w + (1-wr)*42*l - 2_000
        print(f"{v:>12,.0f}", end="")
    print()

print()
print("="*84)
print("WHY THE FEE IS ZERO — a Rs 2,000/mo fee vs gross edge at 70% win rate")
print("="*84)
for own,lev,price,w,l,be in setups:
    gross = 0.70*42*w + 0.30*42*l
    if gross > 0:
        print(f"  Rs{own:,} {lev}x @Rs{price}: gross Rs {gross:>6,.0f}/mo  ->  "
              f"fee eats {min(2_000/gross*100,999):>5.0f}%  ->  net Rs {gross-2_000:>+7,.0f}")
    else:
        print(f"  Rs{own:,} {lev}x @Rs{price}: gross Rs {gross:>6,.0f}/mo  ->  never profitable")
