#!/usr/bin/env python3
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
print("\nThen:  python3 tools/selftest.py && python3 tools/backtest.py data/*.csv")
