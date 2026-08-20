#!/usr/bin/env python3
"""
Authoritative charges via Kite Connect's virtual contract note, and a
reconciliation against the offline model in zerodha_costs.py.

WHY THIS EXISTS. POST /charges/orders computes exact charges for a HYPOTHETICAL
order -- the docs say order_id "can be any random string to calculate charges
for an imaginary order". So there is no reason to ever trust a hardcoded rate
table. This calls the real thing and tells you where zerodha_costs.py has
drifted.

The offline model was already wrong once (NSE turnover charge stale at the
pre-Oct-2024 rate). Run this before phase 2 and after any Zerodha fee change.

Needs credentials. Without them, zerodha_costs.py still works for planning.
    pip install kiteconnect requests
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zerodha_costs import round_trip  # noqa: E402

ROOT = "https://api.kite.trade"
TOLERANCE_PCT = 2.0   # flag any line item off by more than this


def fetch_charges(api_key, access_token, orders):
    """POST /charges/orders. `orders` is a list of order dicts per the docs."""
    import requests
    r = requests.post(
        f"{ROOT}/charges/orders",
        headers={"X-Kite-Version": "3",
                 "Authorization": f"token {api_key}:{access_token}",
                 "Content-Type": "application/json"},
        data=json.dumps(orders), timeout=15,
    )
    r.raise_for_status()
    body = r.json()
    if body.get("status") != "success":
        raise RuntimeError(f"Kite returned: {body}")
    return body["data"]


def virtual_round_trip(api_key, access_token, symbol, price, qty, product="MIS",
                       exchange="NSE"):
    """Charges for a full round trip: one BUY + one SELL at the same price.

    NOTE: average_price must be non-zero (docs). order_id is arbitrary for an
    imaginary order, so the two ids below are just labels.
    """
    orders = [
        {"order_id": "rt-buy", "exchange": exchange, "tradingsymbol": symbol,
         "transaction_type": "BUY", "variety": "regular", "product": product,
         "order_type": "MARKET", "quantity": qty, "average_price": price},
        {"order_id": "rt-sell", "exchange": exchange, "tradingsymbol": symbol,
         "transaction_type": "SELL", "variety": "regular", "product": product,
         "order_type": "MARKET", "quantity": qty, "average_price": price},
    ]
    legs = fetch_charges(api_key, access_token, orders)
    total = sum(leg["charges"]["total"] for leg in legs)
    return total, legs


def reconcile(api_key, access_token, symbol="SBIN", price=800.0, qty=12,
              product="MIS", exchange="NSE"):
    """Compare the offline model against Kite's own computation. Returns True if
    they agree within TOLERANCE_PCT."""
    position = price * qty
    actual, legs = virtual_round_trip(api_key, access_token, symbol, price, qty,
                                      product, exchange)
    model = round_trip(position, product)["total"]
    drift = (model - actual) / actual * 100 if actual else float("inf")

    print(f"Reconciling {product} {symbol} {qty} @ Rs {price:,.2f} "
          f"(position Rs {position:,.0f})")
    print(f"  Kite /charges/orders : Rs {actual:>8.2f}  ({actual/position*100:.4f}%)")
    print(f"  zerodha_costs.py     : Rs {model:>8.2f}  ({model/position*100:.4f}%)")
    print(f"  drift                : {drift:>+8.2f}%")

    for leg in legs:
        c = leg["charges"]
        print(f"    {leg['transaction_type']:<4} brokerage {c['brokerage']:>7.3f} "
              f"| {c['transaction_tax_type']} {c['transaction_tax']:>8.3f} "
              f"| exch {c['exchange_turnover_charge']:>7.4f} "
              f"| stamp {c['stamp_duty']:>6.3f} | gst {c['gst']['total']:>6.3f}")

    ok = abs(drift) <= TOLERANCE_PCT
    print(f"\n  {'OK' if ok else 'DRIFT — update RATES in zerodha_costs.py'} "
          f"(tolerance {TOLERANCE_PCT}%)")
    return ok


if __name__ == "__main__":
    key = os.environ.get("KITE_API_KEY")
    tok = os.environ.get("KITE_ACCESS_TOKEN")
    if not (key and tok):
        print("KITE_API_KEY / KITE_ACCESS_TOKEN not set.")
        print("Run tools/auth.py first, or copy .env.example to .env.")
        print("\nThe offline model still works without credentials:")
        print("    python3 tools/zerodha_costs.py")
        sys.exit(2)

    all_ok = True
    for product, price, qty in (("MIS", 800.0, 12), ("CNC", 800.0, 12),
                                ("MIS", 400.0, 25)):
        all_ok &= reconcile(key, tok, price=price, qty=qty, product=product)
        print()
    sys.exit(0 if all_ok else 1)
