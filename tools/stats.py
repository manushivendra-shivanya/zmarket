#!/usr/bin/env python3
"""
Small-sample statistics for hit rates.

WHY THIS EXISTS: docs/PHASE-1-SPEC.md S3.2 and S3.3 both turn on an interval,
not a point estimate, and nothing in this repo implemented one. "12 wins out of
20" is not a 60% edge -- it is 38.7%-78.1% at 95%, an interval that straddles
every break-even threshold in the plan and therefore decides nothing.

Wilson score interval, NOT the normal approximation. The normal approximation is
badly wrong at small n and near 0 or 1, where it happily returns bounds outside
[0, 1). At the sample sizes phase 1 will actually reach (n = 30-100), that
difference is the whole point of computing an interval at all.
"""
import math

Z95 = 1.959963984540054      # two-sided 95%


def wilson_interval(wins: int, n: int, z: float = Z95) -> tuple:
    """95% Wilson score interval for a binomial proportion. Returns (lo, hi).

    n == 0 returns (0.0, 1.0) -- with no data every rate is possible, which is
    the honest answer and keeps callers from special-casing an empty log.
    """
    if wins < 0 or n < 0 or wins > n:
        raise ValueError(f"need 0 <= wins <= n, got wins={wins}, n={n}")
    if n == 0:
        return 0.0, 1.0
    p = wins / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = (z / denom) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, centre - half), min(1.0, centre + half)


def normal_interval(wins: int, n: int, z: float = Z95) -> tuple:
    """The WRONG one, kept only so the difference can be demonstrated. Do not
    use it for a decision -- see the table in __main__."""
    if n == 0:
        return 0.0, 1.0
    p = wins / n
    half = z * math.sqrt(p * (1 - p) / n)
    return p - half, p + half


if __name__ == "__main__":
    print("=" * 74)
    print("WHY A RAW PERCENTAGE IS NOT A HIT RATE")
    print("=" * 74)
    print(f"{'Sample':>10} {'Observed':>10} {'Wilson 95%':>20} {'Width':>8}")
    print("-" * 74)
    for wins, n in ((3, 5), (6, 10), (12, 20), (18, 30), (30, 50), (60, 100), (300, 500)):
        lo, hi = wilson_interval(wins, n)
        print(f"{f'{wins}/{n}':>10} {wins/n:>9.1%} "
              f"{f'{lo:.1%} .. {hi:.1%}':>20} {hi-lo:>7.1%}")
    print("\n  Every row above observes the SAME 60%. Only the last two say")
    print("  anything a decision can rest on. This is why PHASE-1-SPEC S3.2")
    print("  refuses to report a hit rate below n=30.")

    print()
    print("=" * 74)
    print("AND WHY WILSON, NOT THE NORMAL APPROXIMATION")
    print("=" * 74)
    print(f"{'Sample':>10} {'Wilson 95%':>22} {'Normal 95%':>24}")
    print("-" * 74)
    for wins, n in ((12, 20), (2, 10), (0, 20), (19, 20)):
        wlo, whi = wilson_interval(wins, n)
        nlo, nhi = normal_interval(wins, n)
        bad = "  <-- impossible bound" if nlo < 0 or nhi > 1 else ""
        print(f"{f'{wins}/{n}':>10} {f'{wlo:.1%} .. {whi:.1%}':>22} "
              f"{f'{nlo:.1%} .. {nhi:.1%}':>24}{bad}")
    print("\n  The normal approximation returns bounds outside [0,1] at the")
    print("  extremes, which is exactly where a small signal log will sit.")
