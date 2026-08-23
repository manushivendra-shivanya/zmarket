#!/usr/bin/env python3
"""
The strategy catalogue — a pluggable registry, not a single hardcoded rule.

WHY A REGISTRY. PHASE-1-SPEC.md S6 says the logger "measures whatever setup you
feed it" and deliberately declines to choose. That was right, and it left a hole:
you cannot log signals without a rule that generates them. This file is the
missing half -- several candidate rules behind ONE interface, so they can be
measured against each other on identical data with identical costs, and the
winner chosen by evidence instead of taste.

>>> LOOKAHEAD IS IMPOSSIBLE BY CONSTRUCTION. <<<
A strategy is handed `history` (bars strictly BEFORE the trading day) and
`today_open` -- nothing else. It never sees today's high, low or close, because
those are what it is about to be scored against. This is enforced by the
signature, not by discipline: the single most common way a backtest lies is by
letting the rule peek at the bar it is predicting, and the only reliable defence
is to make peeking unrepresentable.

DATA TIERS -- what a strategy needs in order to run at all:
    "daily"    - previous daily bars + today's open. FREE, works today.
    "intraday" - minute/tick bars. Needs the PAID Kite Connect tier. Declared
                 here so the catalogue is honest about what is not yet reachable,
                 and so the choice to pay for data is driven by a measured gap.

MODELS -- the structural claim each rule rests on. A rule with no model behind it
is a coincidence waiting to be discovered:
    "vol-expansion" - volatility clusters and mean-reverts; a quiet range is
                      followed by a loud one. The most robust of the four.
    "momentum"      - intraday order-flow imbalance persists.
    "mean-reversion"- overreaction gets provided liquidity and partially retraces.
    "liquidity"     - stops cluster at obvious levels, so those levels attract price.

Standard library only, per repo convention.
"""
import statistics
from dataclasses import dataclass, field
from typing import Callable, Optional

LONG, SHORT = "LONG", "SHORT"


@dataclass(frozen=True)
class Bar:
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0

    @property
    def range_pct(self) -> float:
        return (self.high - self.low) / self.low * 100 if self.low else 0.0


@dataclass(frozen=True)
class Signal:
    """A candidate entry, as PHASE-1-SPEC S2 defines one."""
    date: str
    symbol: str
    strategy: str
    direction: str          # LONG or SHORT
    entry: float
    target_pct: float       # always positive, in the favourable direction
    stop_pct: float         # always positive, against
    reason: str

    @property
    def rr(self) -> float:
        return self.target_pct / self.stop_pct if self.stop_pct else float("inf")


@dataclass
class StrategyMeta:
    name: str
    tier: str               # "daily" | "intraday"
    model: str
    describe: str
    params: dict
    fn: Callable = field(repr=False, default=None)


REGISTRY: dict = {}


def strategy(name, tier, model, describe, **params):
    """Register a rule. `params` are the defaults, overridable at call time."""
    def deco(fn):
        REGISTRY[name] = StrategyMeta(name, tier, model, describe, params, fn)
        return fn
    return deco


# --------------------------------------------------------------------------
# helpers -- all operate on history only
# --------------------------------------------------------------------------
def sma(bars, n):
    return statistics.fmean(b.close for b in bars[-n:]) if len(bars) >= n else None


def atr_pct(bars, n=14):
    """Average true range as a % of price. The volatility yardstick.

    PLAN.md S3 rule 1 bans rupee-per-share targets because Rs 5 is 2.5% of a
    Rs 200 stock and 1.25% of a Rs 400 one. The same argument goes one level
    further: a flat 1% is a routine wiggle on a volatile stock and a major move
    on a quiet one. Normalising the stop to ATR is what makes a target
    comparable ACROSS the universe rather than only across price.
    """
    if len(bars) < n + 1:
        return None
    trs = []
    for prev, cur in zip(bars[-(n + 1):-1], bars[-n:]):
        tr = max(cur.high - cur.low,
                 abs(cur.high - prev.close),
                 abs(cur.low - prev.close))
        trs.append(tr / prev.close * 100)
    return statistics.fmean(trs)


def gap_pct(history, today_open):
    return (today_open - history[-1].close) / history[-1].close * 100


def _sig(sym, name, when, direction, entry, tgt, stop, reason):
    return Signal(when, sym, name, direction, entry, round(tgt, 3),
                  round(stop, 3), reason)


# --------------------------------------------------------------------------
# TIER "daily" -- runnable TODAY on free data, entry at the open
# --------------------------------------------------------------------------
@strategy("gap_fade", "daily", "mean-reversion",
          "Large opening gap partially retraces. Fade it, at the open.",
          min_gap_pct=1.5, target_atr=0.6, stop_atr=0.5, atr_n=14, max_gap_pct=8.0)
def gap_fade(symbol, history, today_open, p):
    a = atr_pct(history, p["atr_n"])
    if a is None:
        return None
    g = gap_pct(history, today_open)
    # An enormous gap is usually news, and news does not mean-revert on cue.
    if not (p["min_gap_pct"] <= abs(g) <= p["max_gap_pct"]):
        return None
    direction = LONG if g < 0 else SHORT
    return _sig(symbol, "gap_fade", None, direction, today_open,
                a * p["target_atr"], a * p["stop_atr"],
                f"gap {g:+.2f}% vs ATR {a:.2f}% — fading")


@strategy("gap_and_go", "daily", "momentum",
          "A gap on conviction keeps going. Trade WITH it, at the open.",
          min_gap_pct=1.0, max_gap_pct=5.0, target_atr=0.8, stop_atr=0.4,
          atr_n=14, vol_mult=1.2, vol_n=20)
def gap_and_go(symbol, history, today_open, p):
    a = atr_pct(history, p["atr_n"])
    if a is None or len(history) < p["vol_n"]:
        return None
    g = gap_pct(history, today_open)
    if not (p["min_gap_pct"] <= abs(g) <= p["max_gap_pct"]):
        return None
    # Conviction proxy: yesterday traded above its own recent average volume.
    avg_v = statistics.fmean(b.volume for b in history[-p["vol_n"]:])
    if avg_v and history[-1].volume < avg_v * p["vol_mult"]:
        return None
    direction = LONG if g > 0 else SHORT
    return _sig(symbol, "gap_and_go", None, direction, today_open,
                a * p["target_atr"], a * p["stop_atr"],
                f"gap {g:+.2f}% on {history[-1].volume/avg_v:.1f}x volume")


@strategy("nr7_expansion", "daily", "vol-expansion",
          "Narrowest range in 7 days -> expansion. Direction from the trend.",
          lookback=7, target_atr=1.0, stop_atr=0.5, atr_n=14, trend_n=20)
def nr7_expansion(symbol, history, today_open, p):
    a = atr_pct(history, p["atr_n"])
    trend = sma(history, p["trend_n"])
    if a is None or trend is None or len(history) < p["lookback"]:
        return None
    recent = history[-p["lookback"]:]
    if recent[-1].range_pct > min(b.range_pct for b in recent):
        return None          # yesterday was not the narrowest
    direction = LONG if history[-1].close > trend else SHORT
    return _sig(symbol, "nr7_expansion", None, direction, today_open,
                a * p["target_atr"], a * p["stop_atr"],
                f"NR7 ({recent[-1].range_pct:.2f}%), trend {direction}")


@strategy("inside_day", "daily", "vol-expansion",
          "Yesterday's range inside the day before -> compression, then a break.",
          target_atr=0.9, stop_atr=0.5, atr_n=14, trend_n=20)
def inside_day(symbol, history, today_open, p):
    a = atr_pct(history, p["atr_n"])
    trend = sma(history, p["trend_n"])
    if a is None or trend is None or len(history) < 2:
        return None
    prev, last = history[-2], history[-1]
    if not (last.high <= prev.high and last.low >= prev.low):
        return None
    direction = LONG if last.close > trend else SHORT
    return _sig(symbol, "inside_day", None, direction, today_open,
                a * p["target_atr"], a * p["stop_atr"],
                f"inside day, trend {direction}")


@strategy("pullback_uptrend", "daily", "mean-reversion",
          "Buy a short pullback inside an established uptrend.",
          trend_n=20, pullback_days=2, target_atr=0.8, stop_atr=0.5, atr_n=14)
def pullback_uptrend(symbol, history, today_open, p):
    a = atr_pct(history, p["atr_n"])
    trend = sma(history, p["trend_n"])
    if a is None or trend is None or len(history) < p["pullback_days"] + 1:
        return None
    if history[-1].close <= trend:
        return None                                    # not an uptrend
    recent = history[-p["pullback_days"]:]
    if not all(b.close < history[-i - 2].close for i, b in enumerate(reversed(recent))):
        return None                                    # not consecutive down closes
    return _sig(symbol, "pullback_uptrend", None, LONG, today_open,
                a * p["target_atr"], a * p["stop_atr"],
                f"{p['pullback_days']}d pullback above SMA{p['trend_n']}")


@strategy("pdh_pdl_break", "daily", "liquidity",
          "Open beyond yesterday's high/low — the level where stops sit.",
          buffer_atr=0.1, target_atr=0.8, stop_atr=0.45, atr_n=14)
def pdh_pdl_break(symbol, history, today_open, p):
    a = atr_pct(history, p["atr_n"])
    if a is None:
        return None
    last = history[-1]
    buf = last.close * a * p["buffer_atr"] / 100
    if today_open > last.high + buf:
        direction, why = LONG, f"open above PDH {last.high:.2f}"
    elif today_open < last.low - buf:
        direction, why = SHORT, f"open below PDL {last.low:.2f}"
    else:
        return None
    return _sig(symbol, "pdh_pdl_break", None, direction, today_open,
                a * p["target_atr"], a * p["stop_atr"], why)


# --------------------------------------------------------------------------
# TIER "intraday" -- declared, NOT runnable until minute data exists
# --------------------------------------------------------------------------
@strategy("orb_15m", "intraday", "momentum",
          "Opening-range breakout. The intraday workhorse — NEEDS minute bars.",
          minutes=15, target_atr=1.0, stop_atr=0.5)
def orb_15m(symbol, history, today_open, p):
    raise NotImplementedError(
        "orb_15m needs the first %d minutes of today, which daily bars do not "
        "contain. Kite Personal has no market data; this is the concrete reason "
        "to consider the paid Connect tier -- and only once the daily-tier rules "
        "have been measured and found wanting." % p["minutes"])


@strategy("vwap_reversion", "intraday", "mean-reversion",
          "Fade extension from VWAP — NEEDS minute bars and volume.",
          sigma=2.0, target_atr=0.6, stop_atr=0.4)
def vwap_reversion(symbol, history, today_open, p):
    raise NotImplementedError(
        "vwap_reversion needs intraday volume-weighted price. Same tier "
        "constraint as orb_15m.")


def generate(name, symbol, history, today_open, date=None, **overrides):
    """Run one registered strategy. Returns a Signal or None."""
    meta = REGISTRY[name]
    params = {**meta.params, **overrides}
    sig = meta.fn(symbol, history, today_open, params)
    if sig and date:
        sig = Signal(date, sig.symbol, sig.strategy, sig.direction, sig.entry,
                     sig.target_pct, sig.stop_pct, sig.reason)
    return sig


def runnable(tier="daily"):
    return [n for n, m in REGISTRY.items() if m.tier == tier]


if __name__ == "__main__":
    print("=" * 78)
    print("STRATEGY CATALOGUE")
    print("=" * 78)
    for tier in ("daily", "intraday"):
        mark = "RUNNABLE TODAY on free daily bars" if tier == "daily" else \
               "BLOCKED — needs paid intraday data"
        print(f"\n  --- tier '{tier}' — {mark} ---")
        for n in runnable(tier):
            m = REGISTRY[n]
            print(f"    {n:<18} [{m.model:<14}] {m.describe}")
            print(f"    {'':<18}  params: "
                  + ", ".join(f"{k}={v}" for k, v in m.params.items()))
    print(f"\n  {len(runnable('daily'))} runnable, {len(runnable('intraday'))} blocked.")
    print("\n  Every rule sizes its target and stop in ATR, never in flat percent,")
    print("  so a 2:1 setup means the same thing on a quiet stock and a wild one.")
