"""What does 10%/day actually require? And what does swing cost vs intraday?"""

def intraday_rt(pos):
    """Round trip, equity intraday (MIS). 0.1062% flat below Rs 66,667."""
    brok = 2*min(pos*0.0003, 20); stt = pos*0.00025
    exch = 2*pos*0.0000297; sebi = 2*pos*0.000002; stamp = pos*0.00003
    return brok+stt+exch+sebi+stamp+0.18*(brok+exch+sebi)

def delivery_rt(pos):
    """Round trip, equity DELIVERY (CNC) — for swing/weekly holds.
    Brokerage is Rs 0 at Zerodha, BUT: STT is 0.1% on BOTH legs (vs 0.025%
    sell-only intraday), and DP charges are a FLAT Rs 15.34 per scrip on sell."""
    brok = 0.0; stt = 2*pos*0.001
    exch = 2*pos*0.0000297; sebi = 2*pos*0.000002
    stamp = pos*0.00015; dp = 15.34
    return brok+stt+exch+sebi+stamp+dp+0.18*(brok+exch+sebi)

print("="*80); print("INTRADAY vs SWING — cost of one round trip"); print("="*80)
print(f"{'Position':>10} {'Intraday':>12} {'as %':>9} {'Delivery':>12} {'as %':>9} {'Swing is':>10}")
print("-"*80)
for pos in (3_000, 5_000, 10_000, 25_000, 50_000, 100_000):
    i, d = intraday_rt(pos), delivery_rt(pos)
    print(f"{pos:>10,} {i:>12.2f} {i/pos*100:>8.3f}% {d:>12.2f} {d/pos*100:>8.3f}% "
          f"{d/i:>9.1f}x")
print("\n  Flat Rs 15.34 DP charge dominates small delivery trades. A Rs 3,000 swing")
print("  costs 0.73% round trip -- SEVEN TIMES the intraday rate.")

print()
print("="*80); print("THE 10%/DAY TARGET — what win rate does it need?"); print("="*80)
CAP = 10_000
print(f"Capital Rs {CAP:,}. Target Rs 1,000/day net (10%).\n")
print(f"{'Trades/day':>11} {'Pos size':>10} {'Cost/day':>10} {'Gross needed':>13} "
      f"{'@1% tgt':>9} {'@2% tgt':>9}")
print("-"*80)
for n, lev in ((10,3),(20,3),(50,3),(80,3)):
    pos = CAP*lev/3           # 3 concurrent slots, each own-capital/3 x lev
    cost = intraday_rt(pos)*n
    gross = 1_000 + cost
    per = gross/n/pos         # required average net edge per trade, as fraction
    def wr(t): return (per/t + 1)/2*100
    w1, w2 = wr(0.01), wr(0.02)
    f1 = f"{w1:>8.1f}%" if w1 <= 100 else "impossible"
    f2 = f"{w2:>8.1f}%" if w2 <= 100 else "impossible"
    print(f"{n:>11} {pos:>10,.0f} {cost:>10,.0f} {gross:>13,.0f} {f1:>9} {f2:>9}")

print()
print("="*80); print("COMPOUNDING CHECK — the reason the target needs a second look")
print("="*80)
v = 10_000.0
for d in (1, 5, 21, 63, 126, 252):
    v = 10_000 * (1.10 ** d)
    label = {1:"1 day",5:"1 week",21:"1 month",63:"3 months",126:"6 months",252:"1 year"}[d]
    print(f"  10%/day compounded, {label:>9}: Rs {v:>28,.0f}")
print("\n  Rs 10,000 -> more than India's GDP inside a year. The target is not")
print("  'ambitious', it is self-refuting: any edge that real would hit its own")
print("  capacity limit in weeks, and whoever found it would not trade Rs 10,000.")

print()
print("="*80); print("WHAT THE SAME MACHINERY GIVES AT SANE TARGETS"); print("="*80)
print(f"{'Net/month':>12} {'On Rs 10k':>11} {'Per day':>10} {'Verdict':>34}")
print("-"*80)
for pct, verdict in ((0.5,"below the Rs 2,000 API fee"),(2,"still below the fee"),
                     (5,"clears the fee, good result"),(10,"excellent, top-decile"),
                     (20,"break-even ONLY at Rs 10k capital"),
                     (210,"what 10%/day actually is")):
    m = CAP*pct/100
    print(f"{pct:>11.1f}% {m:>11,.0f} {m/21:>10,.0f}   {verdict:>34}")
print(f"\n  The Rs 2,000/mo API fee is 20% of Rs 10,000. That alone forces you into")
print(f"  the impossible-return regime. Same fee on Rs 2,00,000 is 1%/month.")
