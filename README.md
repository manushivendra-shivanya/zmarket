# zmarket

Systematic intraday equity trading. Personal capital, personal account.

**Not a product. Not a service. Not offered to anyone.** Any reconsideration of
that is a 2027 question at the earliest, and only if the numbers earn it.



## Start here

| Doc | What it is |
|---|---|
| [`PLAN.md`](PLAN.md) | Scope, phases, hard rules, regulatory position |
| [`docs/COST-MODEL.md`](docs/COST-MODEL.md) | What a trade actually costs, and the break-even it implies |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | Dated rulings, with the reasoning |
| [`docs/PHASE-1-SPEC.md`](docs/PHASE-1-SPEC.md) | The signal logger — spec, not built |
| [`tools/zerodha_costs.py`](tools/zerodha_costs.py) | Cost calculator — **the only place rates live** |
| [`tools/verify_docs.py`](tools/verify_docs.py) | Checks every figure in the docs against the model. Exits 1 on drift |
| [`tools/scenario.py`](tools/scenario.py) | P&L model for a given position size and win rate |
| [`tools/stats.py`](tools/stats.py) | Wilson score interval — hit rates with an error bar |

```bash
python3 tools/zerodha_costs.py     # cost table + break-even win rates
python3 tools/verify_docs.py       # run after ANY rate or doc change
python3 tools/scenario.py          # monthly P&L across win rates
python3 tools/stats.py             # why 12/20 is not a 60% edge
```

No dependencies. Standard library only.

## The state of it, honestly

Nothing is built. No capital deployed. No signal validated. The cost model is
the only finished work, and its single conclusion is that **the strategy's
viability is decided by hit rate, and nobody has measured that yet.**

A consistency pass on 2026-08-23 found **18 figures in the docs still on the
pre-correction 0.1062% cost basis** while the code said 0.1071%. All regenerated,
and `tools/verify_docs.py` now fails if it happens again. Note what that check
does *not* do: it proves the docs match the model, **not** that the model matches
Zerodha. Every rate marked `[?]` in `zerodha_costs.py` is still assumed.

**One contradiction is open and needs a ruling** — the R:R tools assume a ₹40,000
single position while `PLAN.md` §1 caps a trade at ₹4,000–16,000, and the
"~3.5 trades/day" conclusion depends on the former. See `PLAN.md` §8.

Phase 1 (the signal logger) is the next thing, and it costs nothing to run — spec in
[`docs/PHASE-1-SPEC.md`](docs/PHASE-1-SPEC.md), **not yet built**.

**Platform:** Kite Connect **Personal** tier — free. Trading and reports APIs, no
market data. API key and secret are set up; they live in a gitignored `.env` and are
never committed.
