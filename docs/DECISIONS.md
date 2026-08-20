# Decisions

Dated, with reasoning. Newest first. A decision reversed keeps its original entry.

---

## 2026-08-20 · The target is an output of phase 1, not an input

**Ruled:** stop planning around "10% of deployed capital per day". Express the
target as ₹/day against **fixed** capital (no compounding — the same ₹10,000 is
redeployed daily), and let the measured hit rate determine what is reachable.

**Reasoning.** At 4x margin, ₹1,000/day is a **2.6% move on a ₹40,000
position** — an ordinary intraday range, so the move was never the obstacle. The
obstacle is that ₹1,000/day *as an average* needs ~100% accuracy. Break-even is
52.1%; a correct call is +₹997 and a wrong one −₹1,083.

At a genuine 60% win rate the mean is **₹165/day ≈ ₹3,468/month ≈ 35% of capital
per month** — an excellent outcome. So ₹1,000 is a **good day, not a mean day.**

**Correction to an earlier argument in this repo's history:** the first version
compounded 10%/day and produced ₹269 lakh crore in a year. That assumed
reinvestment, which was never the plan. The linear version (210%/month simple)
is the fair test and is still ~40× Renaissance Medallion's record, but the
compounding framing overstated the case and two of its figures were wrong
(₹1.64 crore should have been ₹164 crore; "more than India's GDP" was ~82% of it).

---

## 2026-08-20 · Rates come from the API, never from a hardcoded table

**Ruled:** `POST /charges/orders` (the virtual contract note) is authoritative.
`tools/zerodha_costs.py` is an offline approximation for planning only, and
`tools/kite_charges.py` reconciles it against the API.

**Reasoning.** The endpoint computes exact charges for a hypothetical order —
`order_id` may be any random string. There is no reason to trust a table.

**This already caught a bug:** the NSE exchange turnover charge was hardcoded at
**0.00297%**, the pre-Oct-2024 rate. Zerodha's own doc example (SBIN CNC BUY,
1 @ ₹560 → `exchange_turnover_charge` 0.01876) implies **0.00335%**. Corrected;
intraday round trip moved 0.1063% → **0.1071%**.

Zerodha's doc examples are internally inconsistent on `stamp_duty` and CNC
`brokerage`, which is itself the argument for calling the API over reading any
table — including theirs.

---

## 2026-08-20 · Small swing/delivery trades are out

**Ruled:** no CNC position below ~₹25,000. Weekly/biweekly trades of ₹2–3,000
are dropped from the plan.

**Reasoning.** Delivery has zero brokerage but STT is **0.1% on both legs** (vs
0.025% sell-only intraday) and DP charges are a **flat ₹15.34 per scrip on
sell**. On ₹3,000 the flat fee alone is 0.51%:

| Position | Intraday | Delivery | DP as % of cost |
|---|---|---|---|
| ₹3,000 | 0.107% | **0.735%** | 70% |
| ₹10,000 | 0.107% | 0.377% | 41% |
| ₹25,000 | 0.107% | 0.285% | 22% |
| ₹50,000 | 0.107% | 0.254% | 12% |

A ₹3,000 swing needs a **0.73% move to break even** — seven times the intraday
hurdle. Below ~₹25,000 a delivery position is mostly paying a flat fee.

---

## 2026-08-20 · Never target below 0.5% per trade

**Reasoning.** Friction is a constant 0.107%, so the required win rate explodes
as the target shrinks: 0.20% → 76.8%, 0.25% → 71.4%, 0.50% → 60.7%, 1.00% →
55.4%. Small moves are the most expensive thing available, not the cheapest.

The original hypothesis — ₹1–2 moves on a ₹400 share — is the 0.20–0.50% band
and needs 61–77% accuracy. **Dropped in favour of 1–2% targets at 3–10
trades/day**, which needs 53–55% and works without automation.

---

## 2026-08-20 · Python for phase 1

**Reasoning.** Both `pykiteconnect` and `kiteconnectjs` are official and MIT.
Phase 1 is pure analysis, where Python earns it. Node/TypeScript is the better
choice later *if* live execution is automated; that decision is deferred, not
foreclosed.

---

## 2026-08-20 · No TOTP auto-login

**Ruled:** the daily browser login stays manual. `tools/auth.py` scripts
everything around it via a `127.0.0.1` redirect and caches the token for the day.

**Reasoning.** `access_token` expires each trading day and there is no refresh
token. Automating the login with a stored TOTP seed is a grey area against
Zerodha's terms and puts the 2FA secret on disk. At a few trades a day the
browser step costs seconds.

---

## 2026-08-20 · Separate repo from `nutridiet-app`

**Reasoning.** That repo carries health data, DPDP obligations and RLS. Broker
credentials must never sit beside Supabase keys, and its CI already runs on two
saturated self-hosted Macs. If this ever became a product (2028 at the earliest)
untangling it later would cost far more than a separate repo costs now.
