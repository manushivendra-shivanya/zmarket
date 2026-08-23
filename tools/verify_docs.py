#!/usr/bin/env python3
"""
Recompute every number the markdown asserts, and fail if the prose has drifted
from the model.

WHY THIS EXISTS. On 2026-08-23 a full read of this repo found the round-trip
cost stated as 0.1062% in PLAN.md and docs/COST-MODEL.md while the code -- and
docs/DECISIONS.md's own correction entry -- said 0.1071%. The rate fix landed in
zerodha_costs.py and the hand-typed tables were never regenerated. Nothing
caught it for three days because nothing was checking.

The root cause is not the wrong digit. It is that the docs restate numbers the
code owns, by hand. This file makes that drift LOUD instead of silent.

    python3 tools/verify_docs.py          # exits 1 on any drift

Each check names a document, a regex that pulls the asserted figure out of the
prose, and the model expression that should produce it. When a rate legitimately
changes, run the tools, update the docs, and this goes green again -- it does
NOT need editing unless a doc's wording changes.

WHAT IT DOES NOT DO: it cannot tell you a RATE is right. Every rate marked [?]
in zerodha_costs.py is still an assumption; only tools/kite_charges.py against
the live API settles those. This checks internal consistency, nothing more.
"""
import os
import pathlib
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zerodha_costs import RATES, round_trip, breakeven_winrate  # noqa: E402
from stats import wilson_interval                               # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
# Comparison is PRECISION-AWARE, not tolerance-based. A doc figure is correct
# iff it equals the model value rounded to the number of decimals the doc itself
# prints. "0.1062" claims four decimals, so it must equal round(model, 4) --
# and 0.1071 != 0.1062, which is the drift that started this file. A blanket
# absolute tolerance hides exactly that: 0.0009 looks negligible next to a
# tolerance sized for figures like 76.8.


def cost_pct(pos=10_000, product="MIS"):
    return round_trip(pos, product)["pct"]


def be(target_pct, pos=10_000):
    return breakeven_winrate(cost_pct(pos), target_pct) * 100


def be_asym(target_pct, stop_pct, pos):
    """Asymmetric break-even -- the R:R lever. NOT (c/T+1)/2, which is the
    symmetric case only and cannot produce the 23.3% figure the docs quote."""
    c = round_trip(pos)["total"]
    win = pos * target_pct / 100 - c
    loss = pos * stop_pct / 100 + c
    return loss / (win + loss) * 100


def rr_win(pos, target_pct=2.6):
    return pos * target_pct / 100 - round_trip(pos)["total"]


def rr_loss(pos, stop_pct=0.65):
    return pos * stop_pct / 100 + round_trip(pos)["total"]


def rr_freq(pos, win_rate=0.45, goal=1_000):
    """Trades/day to clear `goal` at the 4:1 setup and the stated accuracy."""
    ev = win_rate * rr_win(pos) - (1 - win_rate) * rr_loss(pos)
    return goal / ev


# The position size the R:R tools assume. NOTE: this is Rs 10,000 own capital at
# 4x -- the ENTIRE daily capital in a single trade -- which contradicts PLAN.md
# S1's Rs 2,000-4,000 per trade. Flagged for an owner ruling on 2026-08-23; this
# constant tracks what the tools currently do, not what has been decided.
RR_POSITION = 40_000

# (document, human label, regex with ONE capture group, expected value)
CHECKS = [
    # ---- the headline cost figure ----
    ("PLAN.md", "S2 round-trip cost",
     r"\*\*Round trip = ([\d.]+)% of position value\.\*\*", cost_pct()),
    ("PLAN.md", "S4 phase-1 cost deduction",
     r"minus ([\d.]+)%", cost_pct()),
    ("PLAN.md", "S4 phase-2 cost restatement",
     r"Costs are still ([\d.]+)%", cost_pct()),

    # ---- PLAN.md S2 symmetric break-even table ----
    ("PLAN.md", "S2 break-even @0.20%",
     r"\| 0\.20% \| \*\*([\d.]+)%\*\*", be(0.20)),
    ("PLAN.md", "S2 break-even @0.50%",
     r"\| 0\.50% \| ([\d.]+)% \|", be(0.50)),
    ("PLAN.md", "S2 break-even @1.00%",
     r"\| 1\.00% \| ([\d.]+)% \|", be(1.00)),
    ("PLAN.md", "S2 break-even @2.00%",
     r"\| 2\.00% \| ([\d.]+)% \|", be(2.00)),

    # ---- PLAN.md S2 asymmetric R:R table ----
    ("PLAN.md", "S2 R:R 1:1",
     r"\| 2\.6% / 2\.6% \| 1:1 \| ([\d.]+)%", be_asym(2.6, 2.6, RR_POSITION)),
    ("PLAN.md", "S2 R:R 2:1",
     r"\| 2\.6% / 1\.30% \| 2:1 \| ([\d.]+)%", be_asym(2.6, 1.30, RR_POSITION)),
    ("PLAN.md", "S2 R:R 4:1",
     r"\| 2\.6% / 0\.65% \| 4:1 \| \*\*([\d.]+)%\*\*", be_asym(2.6, 0.65, RR_POSITION)),

    # ---- COST-MODEL S2 round-trip table ----
    ("docs/COST-MODEL.md", "S2 total @Rs5,000",
     r"\| ₹5,000 \|.*?\*\*₹([\d.]+)\*\*", round_trip(5_000)["total"]),
    ("docs/COST-MODEL.md", "S2 total @Rs10,000",
     r"\| ₹10,000 \|.*?\*\*₹([\d.]+)\*\*", round_trip(10_000)["total"]),
    ("docs/COST-MODEL.md", "S2 total @Rs50,000",
     r"\| ₹50,000 \|.*?\*\*₹([\d.]+)\*\*", round_trip(50_000)["total"]),
    ("docs/COST-MODEL.md", "S2 pct @Rs100,000",
     r"\| ₹100,000 \|.*?\| ([\d.]+)% \|", round_trip(100_000)["pct"]),
    ("docs/COST-MODEL.md", "S2 pct @Rs500,000",
     r"\| ₹500,000 \|.*?\| ([\d.]+)% \|", round_trip(500_000)["pct"]),
    ("docs/COST-MODEL.md", "S2 prose restatement",
     r"a fixed ([\d.]+)% tax on every round trip", cost_pct()),

    # ---- COST-MODEL S3 break-even table ----
    ("docs/COST-MODEL.md", "S3 cost basis",
     r"At c = ([\d.]+)%:", cost_pct()),
    ("docs/COST-MODEL.md", "S3 break-even @0.20%",
     r"\| 0\.20% \| ₹0\.80 \| \*\*([\d.]+)%\*\*", be(0.20)),
    ("docs/COST-MODEL.md", "S3 break-even @0.50%",
     r"\| 0\.50% \| ₹2\.00 \| ([\d.]+)%", be(0.50)),
    ("docs/COST-MODEL.md", "S3 break-even @1.00%",
     r"\| \*\*1\.00%\*\* \| \*\*₹4\.00\*\* \| \*\*([\d.]+)%\*\*", be(1.00)),
    ("docs/COST-MODEL.md", "S3 break-even @3.00%",
     r"\| 3\.00% \| ₹12\.00 \| ([\d.]+)%", be(3.00)),

    # ---- COST-MODEL S4 scenario table ----
    ("docs/COST-MODEL.md", "S4 cost @Rs4,000 position",
     r"\| ₹2,000 × 2 \| ₹4,000 \| ₹200 \| 20 \| ([\d.]+) \|",
     round_trip(4_000)["total"]),
    ("docs/COST-MODEL.md", "S4 cost @Rs16,000 position",
     r"\| ₹4,000 × 4 \| ₹16,000 \| ₹200 \| 80 \| ([\d.]+) \|",
     round_trip(16_000)["total"]),

    # ---- DECISIONS.md: the corrected figure, and the DP-charge argument ----
    # ---- PLAN.md S8: the open sizing question's own table ----
    # Added 2026-08-23 with the entry that forbids hand-typed figures. It would
    # be a poor first act to exempt it.
    ("PLAN.md", "S8 sizing table, Rs40,000 win",
     r"\| ₹40,000 — what the tools assume \| \+₹([\d,]+) \|", rr_win(40_000)),
    ("PLAN.md", "S8 sizing table, Rs40,000 loss",
     r"\| ₹40,000 — what the tools assume \| \+₹[\d,]+ \| −₹([\d,]+) \|", rr_loss(40_000)),
    ("PLAN.md", "S8 sizing table, Rs40,000 trades/day",
     r"\| ₹40,000 — what the tools assume \|.*?\| \*\*([\d.]+)\*\* \|", rr_freq(40_000)),
    ("PLAN.md", "S8 sizing table, Rs16,000 win",
     r"\| ₹16,000 — §1 maximum \| \+₹([\d,]+) \|", rr_win(16_000)),
    ("PLAN.md", "S8 sizing table, Rs16,000 trades/day",
     r"\| ₹16,000 — §1 maximum \|.*?\| \*\*([\d.]+)\*\* \|", rr_freq(16_000)),
    ("PLAN.md", "S8 sizing table, Rs8,000 trades/day",
     r"\| ₹8,000 — §1 typical \|.*?\| \*\*([\d.]+)\*\* \|", rr_freq(8_000)),
    ("PLAN.md", "S8 daily cap vs 4:1 stop",
     r"the −₹1,000 cap in §3 trips after \*\*([\d.]+) losing", 1_000 / rr_loss(40_000)),

    ("docs/DECISIONS.md", "rate-correction entry, post-fix cost",
     r"intraday round trip moved [\d.]+% → \*\*([\d.]+)%\*\*", cost_pct()),
    ("docs/DECISIONS.md", "DP entry, CNC cost @Rs3,000",
     r"\| ₹3,000 \| 0\.107% \| \*\*([\d.]+)%\*\*", round_trip(3_000, "CNC")["pct"]),
    ("docs/DECISIONS.md", "DP entry, CNC cost @Rs25,000",
     r"\| ₹25,000 \| 0\.107% \| ([\d.]+)%", round_trip(25_000, "CNC")["pct"]),
    ("docs/DECISIONS.md", "R:R entry, 4:1 break-even",
     r"\| 2\.6% / 0\.65% \| 4:1 \| \+₹997 \| −₹303 \| \*\*([\d.]+)%\*\*",
     be_asym(2.6, 0.65, RR_POSITION)),

    # ---- PHASE-1-SPEC: the thresholds the gate is written against ----
    ("docs/PHASE-1-SPEC.md", "S1 break-even at 4:1",
     r"Break-even at 4:1 is ([\d.]+)%", be_asym(2.6, 0.65, RR_POSITION)),
    ("docs/PHASE-1-SPEC.md", "S1 break-even at 1:1",
     r"at 1:1 it is\s+([\d.]+)%", be_asym(2.6, 2.6, RR_POSITION)),
    ("docs/PHASE-1-SPEC.md", "S3.2 Wilson floor for 12/20",
     r"a 95% interval of roughly \*\*([\d.]+)–[\d.]+%\*\*",
     wilson_interval(12, 20)[0] * 100),
    ("docs/PHASE-1-SPEC.md", "S3.2 Wilson ceiling for 12/20",
     r"a 95% interval of roughly \*\*[\d.]+–([\d.]+)%\*\*",
     wilson_interval(12, 20)[1] * 100),
    ("docs/PHASE-1-SPEC.md", "S4 default position size",
     r"defaults to \*\*₹([\d,]+)\*\*", RR_POSITION),
]

# Rates live in exactly one place. A second copy is how the stale NSE turnover
# charge survived a correction once already.
RATE_LITERALS = {
    "0.0000297": "pre-Oct-2024 NSE turnover charge — the exact stale rate "
                 "DECISIONS.md records as fixed",
    "0.00297":   "pre-Oct-2024 NSE turnover charge (percentage form)",
    "15.34":     "DP charge — must come from RATES['cnc_dp_charge']",
    "0.00025":   "STT — must come from RATES['mis_stt_pct']",
}


def num(s):
    return float(s.replace(",", ""))


def decimals(literal: str) -> int:
    """How many decimal places the doc chose to print."""
    cleaned = literal.replace(",", "")
    return len(cleaned.split(".")[1]) if "." in cleaned else 0


def agrees(literal: str, expected: float) -> bool:
    """True iff the doc figure equals the model value at the doc's own precision."""
    d = decimals(literal)
    return round(num(literal), d) == round(expected, d)


def check_docs():
    failures = []
    cache = {}
    for doc, label, pattern, expected in CHECKS:
        path = ROOT / doc
        if doc not in cache:
            if not path.exists():
                failures.append(f"{doc}: MISSING")
                cache[doc] = ""
                continue
            cache[doc] = path.read_text(encoding="utf-8")
        m = re.search(pattern, cache[doc], re.DOTALL)
        if not m:
            failures.append(f"{doc} · {label}: pattern not found "
                            f"(doc wording changed? expected ~{expected:.4g})")
            continue
        literal = m.group(1)
        if not agrees(literal, expected):
            d = decimals(literal)
            failures.append(f"{doc} · {label}: doc says {literal}, "
                            f"model says {expected:.{d}f}  (exact {expected:.6g})")
        else:
            print(f"  ok   {doc:<22} {label:<38} {literal}")
    return failures


def check_no_duplicate_rates():
    """No tool may hardcode a rate that RATES already owns.

    Parsed with `ast`, not grep: these literals are legitimately DISCUSSED in
    docstrings ("it still held the pre-Oct-2024 0.00297%") and a text search
    cannot tell that apart from code that computes with them. Only numeric
    literals in real expressions count.
    """
    import ast
    failures = []
    for py in sorted((ROOT / "tools").glob("*.py")):
        if py.name in ("zerodha_costs.py", "verify_docs.py"):
            continue
        tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        found = {n.value for n in ast.walk(tree)
                 if isinstance(n, ast.Constant) and isinstance(n.value, (int, float))
                 and not isinstance(n.value, bool)}
        for literal, why in RATE_LITERALS.items():
            if float(literal) in found:
                failures.append(f"tools/{py.name}: hardcodes {literal} — {why}")
    if not failures:
        print(f"  ok   {'tools/*.py':<22} {'no duplicated rate literals':<38} —")
    return failures


if __name__ == "__main__":
    print("=" * 78)
    print("DOC/MODEL CONSISTENCY")
    print("=" * 78)
    print(f"Model basis: round trip {cost_pct():.4f}% "
          f"(MIS, Rs 10,000, exch {RATES['exch_txn_pct']*100:.5f}%)\n")

    problems = check_docs() + check_no_duplicate_rates()

    print()
    if problems:
        print("=" * 78)
        print(f"DRIFT — {len(problems)} problem(s)")
        print("=" * 78)
        for p in problems:
            print(f"  FAIL {p}")
        print("\n  Regenerate the affected table from the tool that owns it.")
        sys.exit(1)
    print("=" * 78)
    print("All checked figures agree with the model.")
    print("=" * 78)
    print("  Consistency only. Every rate marked [?] in zerodha_costs.py is")
    print("  still ASSUMED — run tools/kite_charges.py against the live API")
    print("  before phase 2 to settle them.")
