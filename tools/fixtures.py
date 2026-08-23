#!/usr/bin/env python3
"""
Synthetic daily bars, and the NULL TEST they exist for.

THE POINT. A backtest engine that reports an edge on random data is broken, and
you cannot tell that by reading its output on real data -- real data has
structure, so a plausible-looking result proves nothing about the machinery.
Random walks have NO edge by construction. Any strategy that "wins" on them is
measuring a bug: lookahead, a sign error, ambiguous bars folded into wins, or
costs quietly omitted.

So: before trusting a single number this repo produces about a real stock, the
engine must come back EMPTY-HANDED here. That is the whole test.

Nothing in this file models a real market. It is a calibration weight, not data.
"""
import math
import random

from strategies import Bar


def random_walk(symbol="TEST", n=750, start=500.0, daily_vol_pct=1.5, drift_pct=0.0,
                seed=0):
    """Geometric random walk with a plausible intraday range around each close.

    Deliberately structureless: no trend persistence, no volatility clustering,
    no gap autocorrelation. Every strategy in the catalogue keys on one of those,
    so all of them SHOULD find nothing.
    """
    rng = random.Random(seed)
    bars, close = [], start
    # The day's move is split into an OVERNIGHT leg and an INTRADAY leg, drawn
    # independently, and the close is derived from the OPEN.
    #
    # This is not a detail. An earlier version of this generator derived close
    # from the PREVIOUS close, independently of the open -- which mechanically
    # undoes any gap by the end of the day and baked a -0.375 correlation
    # between the overnight gap and the intraday move into "random" data.
    # gap_fade duly scored a 94% hit rate on noise. The null test caught it.
    # Keep close anchored to open, or this file stops being a null.
    on_vol = daily_vol_pct / 100 * 0.45
    id_vol = math.sqrt(max((daily_vol_pct / 100) ** 2 - on_vol ** 2, 1e-12))
    for i in range(n):
        prev_close = close
        op = max(1.0, prev_close * math.exp(rng.gauss(0, on_vol)))
        close = max(1.0, op * math.exp(rng.gauss(drift_pct / 100, id_vol)))
        span = abs(rng.gauss(0, id_vol * 0.8))
        hi = max(op, close) * math.exp(span)
        lo = min(op, close) * math.exp(-span)
        vol = max(1.0, rng.gauss(1_000_000, 250_000))
        bars.append(Bar(f"D{i:04d}", round(op, 2), round(hi, 2), round(lo, 2),
                        round(close, 2), round(vol)))
    return symbol, bars


def universe(n_symbols=12, n=750, seed=0, **kw):
    out = {}
    for k in range(n_symbols):
        sym, bars = random_walk(f"RW{k:02d}", n=n, seed=seed * 1000 + k,
                                start=200 + k * 90, **kw)
        out[sym] = bars
    return out
