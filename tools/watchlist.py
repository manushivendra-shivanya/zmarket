#!/usr/bin/env python3
"""
The owner's actual watchlist, and how to get bars for it.

Taken from the Kite watchlist screenshot, 2026-08-23. Exchange as shown there.

WHY THIS FILE EXISTS SEPARATELY. PLAN.md S8 lists "define the universe" as an
open question -- liquidity floor, price band, ADV minimum -- and it is still
open. This is NOT that. This is the ten symbols actually being watched, which is
a starting point for measurement, not a screened universe. Ten hand-picked names
carry whatever bias picked them; a screened universe does not. Do not confuse the
two when reading results.
"""

# symbol -> (exchange, yfinance ticker)
WATCHLIST = {
    "HINDUNILVR": ("NSE", "HINDUNILVR.NS"),
    "TCS":        ("NSE", "TCS.NS"),
    "SUZLON":     ("NSE", "SUZLON.NS"),
    "GLENMARK":   ("NSE", "GLENMARK.NS"),
    "ITC":        ("BSE", "ITC.NS"),        # watched on BSE; NSE series is deeper
    "SBIN":       ("BSE", "SBIN.NS"),
    "M&MFIN":     ("BSE", "M&MFIN.NS"),
    "TMPV":       ("BSE", "TMPV.NS"),       # Tata Motors Passenger Vehicles
    "DLF":        ("BSE", "DLF.NS"),
    "ULTRACEMCO": ("BSE", "ULTRACEMCO.NS"),
}

# Approximate last traded prices from the same screenshot, for sanity-checking a
# downloaded series lines up with reality. NOT used in any calculation.
REFERENCE_PRICES = {
    "HINDUNILVR": 2015.00, "TCS": 2302.00, "SUZLON": 46.71, "GLENMARK": 2317.90,
    "ITC": 269.80, "SBIN": 1045.40, "M&MFIN": 380.20, "TMPV": 317.70,
    "DLF": 678.40, "ULTRACEMCO": 11551.00,
}

FETCH_SCRIPT = '''#!/usr/bin/env python3
"""Run this ON YOUR MACHINE -- market data is not reachable from the agent
sandbox. Needs: pip install yfinance"""
import os
import yfinance as yf
from watchlist import WATCHLIST

os.makedirs("data", exist_ok=True)
for sym, (exch, ticker) in WATCHLIST.items():
    df = yf.download(ticker, period="2y", interval="1d",
                     auto_adjust=False, progress=False)
    if df.empty:
        print(f"  {sym}: NO DATA for {ticker} -- check the ticker")
        continue
    df = df.reset_index()
    df.columns = [str(c[0] if isinstance(c, tuple) else c) for c in df.columns]
    out = f"data/{sym.replace('&','_')}.csv"
    df.to_csv(out, index=False)
    print(f"  {sym}: {len(df)} bars -> {out}")
print("\\nThen:  python3 tools/selftest.py && python3 tools/backtest.py data/*.csv")
'''

if __name__ == "__main__":
    import sys
    if "--write-fetcher" in sys.argv:
        with open("tools/fetch_data.py", "w") as fh:
            fh.write(FETCH_SCRIPT)
        print("wrote tools/fetch_data.py")
    else:
        print("WATCHLIST — 10 symbols, from the Kite screenshot 2026-08-23\n")
        print(f"{'symbol':<12} {'exch':<5} {'yf ticker':<16} {'ref price':>11}")
        print("-" * 48)
        for s, (e, t) in WATCHLIST.items():
            print(f"{s:<12} {e:<5} {t:<16} {REFERENCE_PRICES[s]:>11,.2f}")
        print("\n  These are WATCHED names, not a screened universe (PLAN.md S8).")
        print("  Ten hand-picked symbols carry whatever bias picked them.")
        print("\n  python3 tools/watchlist.py --write-fetcher   # then run it locally")
