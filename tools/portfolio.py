#!/usr/bin/env python3
"""
The allocator: Rs 10,000 split across several scripts, margin on each slice,
MULTIPLE trades per script per day, each on a time-boxed intraday question.

WHY THIS REPLACES THE EARLIER SHAPE. tools/backtest.py takes one trade per symbol
per day, entered at the open and scored on a daily bar. That cannot express any
of what this models:

  * capital DIVIDED across ~6 scripts by conviction (Rs 1,500 here, Rs 800 there)
  * margin applied to each slice, leverage configurable INCLUDING 1x (no margin)
  * several trades per script per day, in 15/30-minute windows
  * a TIME-BOXED question -- "this position is open; can it make its target in
    the next N minutes?" -- with a hard exit when the box expires
  * capital RECYCLING: a slice that closes at 10:05 is available again at 10:06
  * the -Rs 1,000 daily cap as a portfolio-level circuit breaker

THE ARITHMETIC THAT SHAPES IT. Round-trip friction is 0.1071% of every rupee
traded, so cost scales with TURNOVER, not with capital. Recycling one slice ten
times a day costs ten round trips, not one. At 4x leverage and 18 trades/day the
friction bill is ~27% of capital per month before a single rupee of profit. High
frequency is not free diversification -- each re-entry is another toll.

DATA. This needs MINUTE bars. Kite's Personal tier has no market data at all, so
on real symbols this is blocked until either the paid Connect tier or another
intraday source exists. The engine is written against a bar interface so it runs
identically on synthetic and real minute data; only the source changes.
"""
import os
import sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zerodha_costs import round_trip                        # noqa: E402

LONG, SHORT = "LONG", "SHORT"
SESSION_MINUTES = 375           # 09:15 to 15:30
SQUARE_OFF_MIN = 365            # ~15:20, per PLAN.md S3 rule 6


@dataclass(frozen=True)
class MinuteBar:
    minute: int                 # minutes since 09:15
    open: float
    high: float
    low: float
    close: float


@dataclass
class Position:
    symbol: str
    direction: str
    entry: float
    qty: int
    opened: int                 # minute index
    target_pct: float
    stop_pct: float
    box_minutes: int            # the time box -- exit when it expires
    own: float                  # own capital committed (position / leverage)

    @property
    def value(self):
        return self.entry * self.qty


@dataclass
class Trade:
    symbol: str
    direction: str
    entry: float
    exit: float
    qty: int
    opened: int
    closed: int
    reason: str                 # TARGET | STOP | BOX | SQUAREOFF | AMBIGUOUS
    gross: float
    cost: float

    @property
    def net(self):
        return self.gross - self.cost

    @property
    def held(self):
        return self.closed - self.opened


@dataclass
class Allocation:
    """How Rs 10,000 is divided. Weights are CONVICTION, not equal splits."""
    capital: float = 10_000.0
    leverage: float = 4.0                      # 1.0 = no margin at all
    weights: dict = field(default_factory=dict)   # symbol -> fraction of capital
    max_concurrent: int = 6
    min_slice: float = 500.0

    def slice_for(self, symbol):
        """Own capital for one position in this symbol."""
        w = self.weights.get(symbol, 1.0 / max(len(self.weights), 1))
        return max(self.min_slice, self.capital * w)

    def position_value(self, symbol):
        return self.slice_for(symbol) * self.leverage


def equal_weights(symbols):
    return {s: 1.0 / len(symbols) for s in symbols}


def conviction_weights(raw):
    """Normalise arbitrary conviction scores to fractions summing to 1."""
    tot = sum(raw.values())
    return {k: v / tot for k, v in raw.items()}


class Session:
    """One trading day across the allocated symbols."""

    def __init__(self, alloc, daily_cap=-1_000.0, window=15, box=30,
                 target_pct=0.6, stop_pct=0.3):
        self.a = alloc
        self.daily_cap = daily_cap
        self.window = window          # how often entries are considered
        self.box = box                # time box per trade, in minutes
        self.target_pct = target_pct
        self.stop_pct = stop_pct
        self.open_pos = {}
        self.trades = []
        self.realised = 0.0
        self.own_committed = 0.0
        self.halted = False
        self.halt_minute = None

    # -- exits -------------------------------------------------------------
    def _levels(self, p):
        if p.direction == LONG:
            return p.entry * (1 + p.target_pct / 100), p.entry * (1 - p.stop_pct / 100)
        return p.entry * (1 - p.target_pct / 100), p.entry * (1 + p.stop_pct / 100)

    def _close(self, p, price, minute, reason):
        gross = (price - p.entry) * p.qty
        if p.direction == SHORT:
            gross = -gross
        cost = round_trip(p.value)["total"]
        t = Trade(p.symbol, p.direction, p.entry, price, p.qty, p.opened, minute,
                  reason, gross, cost)
        self.trades.append(t)
        self.realised += t.net
        self.own_committed -= p.own
        del self.open_pos[p.symbol]
        if self.realised <= self.daily_cap and not self.halted:
            self.halted = True                 # circuit breaker: no new entries
            self.halt_minute = minute
        return t

    def _check_exits(self, bars, minute):
        for sym in list(self.open_pos):
            p = self.open_pos[sym]
            bar = bars[sym][minute]
            tgt, stp = self._levels(p)
            hit_t = bar.high >= tgt if p.direction == LONG else bar.low <= tgt
            hit_s = bar.low <= stp if p.direction == LONG else bar.high >= stp
            if hit_t and hit_s:
                # Both inside one minute bar -- order unknowable. Book the stop.
                self._close(p, stp, minute, "AMBIGUOUS")
            elif hit_t:
                self._close(p, tgt, minute, "TARGET")
            elif hit_s:
                self._close(p, stp, minute, "STOP")
            elif minute - p.opened >= p.box_minutes:
                self._close(p, bar.close, minute, "BOX")
            elif minute >= SQUARE_OFF_MIN:
                self._close(p, bar.close, minute, "SQUAREOFF")

    # -- entries -----------------------------------------------------------
    def _available_own(self):
        return self.a.capital - self.own_committed

    def _try_entries(self, bars, minute, signals):
        if self.halted or minute >= SQUARE_OFF_MIN - self.box:
            return
        for sym, direction in signals:
            if sym in self.open_pos:
                continue                       # one position per script at a time
            if len(self.open_pos) >= self.a.max_concurrent:
                break
            own = self.a.slice_for(sym)
            if own > self._available_own():
                continue                       # capital already working elsewhere
            price = bars[sym][minute].close
            qty = int(self.a.position_value(sym) // price)
            if qty < 1:
                continue                       # slice too small for one share
            self.open_pos[sym] = Position(sym, direction, price, qty, minute,
                                          self.target_pct, self.stop_pct,
                                          self.box, own)
            self.own_committed += own

    def run(self, bars, signal_fn):
        """bars: {symbol: [MinuteBar]}. signal_fn(bars, minute) -> [(sym, dir)]."""
        n = min(len(b) for b in bars.values())
        for minute in range(1, n):
            self._check_exits(bars, minute)
            if minute % self.window == 0:
                self._try_entries(bars, minute, signal_fn(bars, minute))
        for sym in list(self.open_pos):         # force square-off
            self._close(self.open_pos[sym], bars[sym][n - 1].close, n - 1, "SQUAREOFF")
        return self.summary()

    def summary(self):
        t = self.trades
        by = {}
        for x in t:
            by[x.reason] = by.get(x.reason, 0) + 1
        turnover = sum(x.entry * x.qty for x in t) * 2
        return {
            "trades": len(t), "reasons": by,
            "gross": sum(x.gross for x in t),
            "cost": sum(x.cost for x in t),
            "net": self.realised,
            "turnover": turnover,
            "halted": self.halted, "halt_minute": self.halt_minute,
            "avg_hold": (sum(x.held for x in t) / len(t)) if t else 0,
            "peak_deployed": max((x.entry * x.qty for x in t), default=0),
        }
