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
"""Fetch daily bars for the watchlist. RUN THIS ON YOUR OWN MACHINE -- market
data is not reachable from the agent sandbox.

    cd /path/to/zmarket
    python3 -m pip install yfinance
    python3 tools/fetch_data.py

macOS ships no bare `pip`; use `python3 -m pip`. Run from the REPO ROOT --
the script writes into ./data and resolves its own imports either way.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)          # so `import watchlist` works from anywhere

try:
    import yfinance as yf
except ImportError:
    sys.exit("yfinance is not installed. Run:  python3 -m pip install yfinance")

from watchlist import WATCHLIST

outdir = os.path.join(ROOT, "data")
os.makedirs(outdir, exist_ok=True)

ok = 0
for sym, (exch, ticker) in WATCHLIST.items():
    try:
        df = yf.download(ticker, period="2y", interval="1d",
                         auto_adjust=False, progress=False)
    except Exception as e:
        print(f"  {sym:<12} FAILED: {e}")
        continue
    if df is None or df.empty:
        print(f"  {sym:<12} NO DATA for {ticker} -- check the ticker symbol")
        continue
    df = df.reset_index()
    # yfinance returns a MultiIndex on the columns for some versions; flatten it
    df.columns = [str(c[0] if isinstance(c, tuple) else c) for c in df.columns]
    path = os.path.join(outdir, sym.replace("&", "_") + ".csv")
    df.to_csv(path, index=False)
    print(f"  {sym:<12} {len(df):>5} bars -> {os.path.relpath(path, ROOT)}")
    ok += 1

print(f"\\n{ok}/{len(WATCHLIST)} symbols saved.")
if ok:
    print("Next:")
    print("  python3 tools/selftest.py            # null test — must pass first")
    print("  python3 tools/backtest.py data/*.csv")
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
