#!/usr/bin/env python3
"""Fetch bars for the watchlist. RUN THIS ON YOUR OWN MACHINE -- market data is
not reachable from the agent sandbox.

    cd /path/to/zmarket
    python3 -m pip install yfinance

    python3 tools/fetch_data.py              # daily, 2 years
    python3 tools/fetch_data.py --intraday   # 15-minute, ~60 days

macOS ships no bare `pip`; use `python3 -m pip`.

WHY --intraday MATTERS. The portfolio model (15/30-minute windows, time-boxed
targets, several trades per script per day) CANNOT be tested on daily bars.
Kite's Personal tier serves no market data at all, which looked like a reason to
pay for the Connect tier. It may not be: Yahoo serves intraday bars free, with
limited history -- roughly 60 days at 15m and 7 days at 1m, per Yahoo's own
limits. Sixty days of 15-minute bars is enough to test whether the window/box
design survives friction, which is the question that decides whether paid data is
worth buying at all.

VERIFY THE LIMITS YOURSELF by running this -- the row count it prints is the
truth, not the docstring. If a symbol returns far fewer bars than expected, the
window is shorter than assumed and the sample is correspondingly weaker.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

try:
    import yfinance as yf
except ImportError:
    sys.exit("yfinance is not installed. Run:  python3 -m pip install yfinance")

from watchlist import WATCHLIST

INTRADAY = "--intraday" in sys.argv
period, interval, sub = ("60d", "15m", "intraday") if INTRADAY else ("2y", "1d", "daily")

outdir = os.path.join(ROOT, "data", sub)
os.makedirs(outdir, exist_ok=True)
print(f"Fetching {interval} bars over {period} into data/{sub}/\n")

ok = 0
for sym, (exch, ticker) in WATCHLIST.items():
    try:
        df = yf.download(ticker, period=period, interval=interval,
                         auto_adjust=False, progress=False)
    except Exception as e:
        print(f"  {sym:<12} FAILED: {e}")
        continue
    if df is None or df.empty:
        print(f"  {sym:<12} NO DATA for {ticker} -- check the ticker symbol")
        continue
    df = df.reset_index()
    # newer yfinance returns a MultiIndex on columns; flatten it
    df.columns = [str(c[0] if isinstance(c, tuple) else c) for c in df.columns]
    # the timestamp column is 'Date' for daily and 'Datetime' for intraday
    if "Datetime" in df.columns:
        df = df.rename(columns={"Datetime": "Date"})
    path = os.path.join(outdir, sym.replace("&", "_") + ".csv")
    df.to_csv(path, index=False)
    print(f"  {sym:<12} {len(df):>6} bars -> {os.path.relpath(path, ROOT)}")
    ok += 1

print(f"\n{ok}/{len(WATCHLIST)} symbols saved.")
if ok and not INTRADAY:
    print("Next:")
    print("  python3 tools/selftest.py                     # null test, must pass")
    print("  python3 tools/backtest.py data/daily/*.csv")
elif ok:
    print("Next:")
    print("  python3 tools/selftest.py")
    print("  python3 tools/backtest_intraday.py data/intraday/*.csv")
    print("\nCheck the bar counts above. ~60 days x 25 bars/day is ~1,500 per")
    print("symbol. Far fewer means Yahoo served a shorter window than assumed.")
