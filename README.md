# zmarket

Systematic intraday equity trading. Personal capital, personal account.

**Not a product. Not a service. Not offered to anyone.** Any reconsideration of
that is a 2028 question at the earliest, and only if the numbers earn it.

**Deliberately separate from `nutridiet-app`.** That repo carries health data,
DPDP obligations and RLS; nothing about the market belongs in it, and broker
credentials must never sit beside Supabase keys.

## Start here

| Doc | What it is |
|---|---|
| [`PLAN.md`](PLAN.md) | Scope, phases, hard rules, regulatory position |
| [`docs/COST-MODEL.md`](docs/COST-MODEL.md) | What a trade actually costs, and the break-even it implies |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | Dated rulings, with the reasoning |
| [`tools/zerodha_costs.py`](tools/zerodha_costs.py) | Cost calculator — run it, verify the rates |
| [`tools/scenario.py`](tools/scenario.py) | P&L model for a given position size and win rate |

```bash
python3 tools/zerodha_costs.py     # cost table + break-even win rates
python3 tools/scenario.py          # monthly P&L across win rates
```

No dependencies. Standard library only.

## The state of it, honestly

Nothing is built. No capital deployed. No signal validated. The cost model is
the only finished work, and its single conclusion is that **the strategy's
viability is decided by hit rate, and nobody has measured that yet.**

Phase 1 (the signal logger) is the next thing, and it costs nothing to run.
