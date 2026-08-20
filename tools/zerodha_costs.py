#!/usr/bin/env python3
"""
Zerodha charge model — OFFLINE APPROXIMATION.

>>> THE AUTHORITATIVE SOURCE IS THE API, NOT THIS FILE. <<<

Kite Connect exposes POST /charges/orders (the "virtual contract note"), which
computes exact charges for a hypothetical order -- order_id can be any random
string. Once you have credentials, use tools/kite_charges.py, which calls it and
RECONCILES this model against it. This file exists only so planning works with
no credentials and no subscription.

It has already been wrong once: the NSE exchange turnover charge was hardcoded
at the pre-Oct-2024 rate of 0.00297%. Zerodha's own doc example (SBIN CNC BUY,
1 @ Rs 560 -> exchange_turnover_charge 0.01876) implies 0.00335%. Corrected
2026-08-20. Assume the rest are drifting too, and reconcile before trusting.

Intraday = MIS. Delivery = CNC. Not F&O -- those have different tax types
(CTT vs STT) and this model does not cover them.
"""

RATES = {
    # --- intraday (MIS) ---
    "mis_brokerage_pct":  0.0003,     # 0.03% per executed order...
    "mis_brokerage_cap":  20.0,       # ...or Rs 20, whichever is LOWER, per leg
    "mis_stt_pct":        0.00025,    # 0.025%, SELL side only
    "mis_stamp_pct":      0.00003,    # 0.003%, BUY side only
    # --- delivery (CNC) ---
    "cnc_brokerage_pct":  0.0,        # zero brokerage on equity delivery
    "cnc_stt_pct":        0.001,      # 0.1% on BOTH legs -- verified against docs
    "cnc_stamp_pct":      0.00015,    # 0.015%, BUY side only
    "cnc_dp_charge":      15.34,      # FLAT, per scrip, on SELL. Dominates small trades.
    # --- common ---
    "exch_txn_pct":       0.0000335,  # NSE 0.00335% -- CORRECTED 2026-08-20
    "sebi_pct":           0.000001,   # Rs 10/crore
    "ipft_pct":           0.000001,   # NSE Rs 10/crore
    "gst_pct":            0.18,       # on brokerage + exchange + SEBI
}


def round_trip(position: float, product: str = "MIS", r=RATES) -> dict:
    """One buy + one sell of the same rupee value. product: 'MIS' or 'CNC'."""
    if product not in ("MIS", "CNC"):
        raise ValueError(f"product must be MIS or CNC, got {product!r}")
    turnover = 2 * position
    mis = product == "MIS"

    if mis:
        brokerage = 2 * min(position * r["mis_brokerage_pct"], r["mis_brokerage_cap"])
        stt   = position * r["mis_stt_pct"]
        stamp = position * r["mis_stamp_pct"]
        dp    = 0.0
    else:
        brokerage = 2 * position * r["cnc_brokerage_pct"]
        stt   = 2 * position * r["cnc_stt_pct"]
        stamp = position * r["cnc_stamp_pct"]
        dp    = r["cnc_dp_charge"]

    exch = turnover * r["exch_txn_pct"]
    sebi = turnover * r["sebi_pct"]
    ipft = turnover * r["ipft_pct"]
    gst  = r["gst_pct"] * (brokerage + exch + sebi)

    total = brokerage + stt + exch + sebi + ipft + stamp + dp + gst
    return {"position": position, "product": product, "brokerage": brokerage,
            "stt": stt, "exchange": exch, "sebi": sebi, "ipft": ipft,
            "stamp": stamp, "dp": dp, "gst": gst, "total": total,
            "pct": total / position * 100}


def breakeven_winrate(cost_pct: float, target_pct: float) -> float:
    """w*T - (1-w)*T - c = 0  ->  w = (c/T + 1) / 2. Symmetric win/loss."""
    return (cost_pct / target_pct + 1) / 2


if __name__ == "__main__":
    print("=" * 78)
    print("ROUND-TRIP COST — INTRADAY (MIS) vs DELIVERY (CNC)")
    print("=" * 78)
    print(f"{'Position':>10} {'MIS':>10} {'MIS %':>9} {'CNC':>10} {'CNC %':>9} {'CNC is':>9}")
    print("-" * 78)
    for pos in (3_000, 5_000, 10_000, 25_000, 50_000, 100_000, 250_000):
        m, c = round_trip(pos, "MIS"), round_trip(pos, "CNC")
        print(f"{pos:>10,} {m['total']:>10.2f} {m['pct']:>8.3f}% "
              f"{c['total']:>10.2f} {c['pct']:>8.3f}% {c['total']/m['total']:>8.1f}x")
    print("\n  MIS is FLAT at ~0.107% below Rs 66,667/order (the Rs 20 cap does not bind).")
    print("  CNC carries a FLAT Rs 15.34 DP charge on sell, so small swing trades are")
    print("  punishing: a Rs 3,000 hold costs ~0.73% round trip, ~7x the intraday rate.")

    print()
    print("=" * 78)
    print("BREAK-EVEN WIN RATE — intraday, Rs 10,000 position")
    print("=" * 78)
    base = round_trip(10_000, "MIS")["pct"]
    print(f"Cost basis {base:.4f}% per round trip\n")
    print(f"{'Target':>9} {'On Rs 400 share':>18} {'Win rate needed':>18}")
    print("-" * 78)
    for tgt in (0.10, 0.20, 0.25, 0.50, 0.75, 1.00, 1.50, 2.00, 3.00):
        w = breakeven_winrate(base, tgt) * 100
        flag = "  impossible" if w >= 100 else ("  very hard" if w >= 70 else "")
        print(f"{tgt:>8.2f}% {('Rs %.2f' % (400*tgt/100)):>18} {w:>17.1f}%{flag}")

    print()
    print("=" * 78)
    print("MINIMUM VIABLE SWING SIZE — where the flat DP charge stops dominating")
    print("=" * 78)
    for pos in (3_000, 10_000, 25_000, 50_000, 100_000):
        c = round_trip(pos, "CNC")
        share = c["dp"] / c["total"] * 100
        print(f"  Rs {pos:>7,}: DP is {share:>4.0f}% of total cost   "
              f"(round trip {c['pct']:.3f}%, needs a {c['pct']:.2f}% move to break even)")
    print("\n  Below ~Rs 25,000 a swing position is mostly paying a flat fee.")
