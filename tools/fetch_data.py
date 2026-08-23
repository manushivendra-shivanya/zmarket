#!/usr/bin/env python3
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

print(f"\n{ok}/{len(WATCHLIST)} symbols saved.")
if ok:
    print("Next:")
    print("  python3 tools/selftest.py            # null test — must pass first")
    print("  python3 tools/backtest.py data/*.csv")
