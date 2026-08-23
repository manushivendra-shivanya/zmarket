# Decisions

Dated, with reasoning. Newest first. A decision reversed keeps its original entry.

---

## 2026-08-23 · Numbers in prose are GENERATED and CHECKED, never typed

**Ruled:** no figure may live in a markdown table by hand. `tools/verify_docs.py`
recomputes every number the docs assert and **exits 1 on drift**. Rates live in
exactly one place — `RATES` in `tools/zerodha_costs.py` — and no other tool may
hardcode one.

**What prompted it.** A full read of this repo on 2026-08-23 found the round-trip
cost stated as **0.1062%** in `PLAN.md` (×3) and throughout `COST-MODEL.md` §2, §3
and §4 — while the code, and the rate-correction entry in *this file*, said
**0.1071%**. The NSE turnover fix (0.00297% → 0.00335%) landed in
`zerodha_costs.py` and the hand-typed tables were never regenerated. **18 stated
figures were wrong.** Nothing caught it because nothing was checking.

**The root cause is not the wrong digit.** It is that prose restates numbers the
code owns, and prose does not recompute itself. That is a structural defect, and
this repo had already been bitten by the same class of error once — which is what
the "rates come from the API" ruling was for. That ruling was right and
insufficient: it fixed where rates come *from*, not where they get *copied to*.

**Three things it now enforces:**

1. **Doc figures are checked at their own printed precision.** "0.1062" claims four
   decimals, so it must equal `round(model, 4)`. A blanket tolerance would have
   passed it — 0.0009 looks negligible next to figures like 76.8 — which is exactly
   how the drift hid.
2. **One rate table.** `tools/target_test.py` carried its own copy and had gone
   stale: it still held the **pre-Oct-2024 0.00297%** the correction entry above
   records as fixed, plus SEBI at ₹20/crore (it is ₹10) and no IPFT at all. It was
   a *runnable tool* handing out superseded numbers with no warning. Rewritten to
   import `round_trip`; the check is AST-based so the literal can still be
   discussed in a docstring.
3. **Superseded arguments get removed, not left lying.** `target_test.py` also
   still argued from a **live ₹2,000/month API fee** — killed by the free-tier
   ruling — and still printed *"more than India's GDP"*, which the target entry
   above had already corrected to **~82% of it**. Both gone. Overstating a case you
   are already winning is how a good argument gets dismissed.

**Also added:** `tools/stats.py` — the Wilson score interval that
`PHASE-1-SPEC.md` §3.2 and §3.3 are both written against and that **nothing in
this repo implemented.** The spec's own worked example (12/20 → "roughly 39–78%")
checks out: Wilson gives **38.7–78.1%**.

**Scope, stated plainly: this entry rules on repo hygiene, nothing else.** No rate
was changed, no rate was verified, and no trading decision was revisited. Every
rate marked `[?]` in `zerodha_costs.py` — the **₹15.34 DP charge above all**, which
carries the entire no-small-swings ruling — is still an assumption. Only
`tools/kite_charges.py` against a live key settles those. A green
`verify_docs.py` means the docs match the model; **it says nothing about whether
the model matches Zerodha.**

**NOT ruled here — and it needs one.** The same read found that
`risk_reward.py` and `daily_target.py` assume a **₹40,000 single position** (all
₹10,000 of daily capital at 4x), while `PLAN.md` §1 caps a trade at ₹2,000–4,000
own → ₹4,000–16,000. Every "+₹997 / −₹303 / ~3.5 trades a day" figure — including
the one quoted as settled in the R:R entry below — depends on the ₹40,000 reading.
At §1's sizing, ₹1,000/day needs **8.9–17.7 trades/day**, not 3.5. **This is an
open question, deliberately not decided here** — see `PLAN.md` §8, along with the
related point that the −₹1,000 daily cap trips after 3.3 losing trades and is
absent from the Monte Carlo.

---

## 2026-08-20 · There is a FREE tier — create Personal, defer Connect

**The fact.** The create-app form offers three types, and the ₹2,000/month figure
this repo used throughout was never verified and is wrong in both structure and
applicability:

| Type | Cost | Gives | Withholds |
|---|---|---|---|
| **Connect** | **500 credits / 30 days** — a credit model, **rate unknown** | Trading + historical chart data + live quotes & WebSockets | — |
| **Personal** | **Free** | Investing, trading, reports APIs | **No historical data, no live quotes, no WebSockets** |
| **Publisher** | Free | HTML/JS order buttons | No API access at all |

**Ruled: create Personal.** Reasons, in order:

1. **No Kite market data is needed yet.** Phase 1 is a signal logger and runs on
   free sources (NSE bhavcopy, yfinance). Paying for tick data before knowing
   whether a signal exists is backwards.
2. **"Reports APIs" should cover `/charges/orders`**, so `tools/kite_charges.py`
   can reconcile the offline cost model against Zerodha's own numbers **for ₹0** —
   closing the stale-rate problem that this repo already hit once. *(Unverified:
   "reports" may not include the charges endpoint.)*
3. **Order APIs are included**, so automation is not foreclosed.
4. **It costs nothing.** There is no downside to creating it now.

**Connect is deferred**, not rejected. Its entire advantage is live ticks and
historical data, and there is no strategy to feed them to. Upgrade when phase 1
produces a hit rate worth streaming for.

**Redirect URL: `http://127.0.0.1:8765/`** — exactly what `tools/auth.py` listens
on. Setting it correctly at creation avoids a re-registration later.

### What this corrects elsewhere in this repo

The ₹2,000/month figure appears in several earlier entries and in
`docs/COST-MODEL.md` §5. It was **assumed from general knowledge and never
checked**, and the free tier means it was not merely imprecise but the wrong
question. Specifically:

- **"₹40,000 is your break-even capital"** — that conclusion existed *only*
  because of an assumed monthly fee. **At ₹0 it does not hold**, and the
  fee-free tables in `COST-MODEL.md` §4 are the operative ones.
- **"The fee eats 33–302% of gross edge"** — now a **conditional**, not a live
  constraint. It stays in the file as the argument for *why* Connect is deferred.
- The SEBI static-IP entry is **unaffected** — that is a rule about orders, not
  about tier.

**Open:** the credit→rupee rate for Connect. Check the Billing tab before any
upgrade decision.

---

## 2026-08-20 · SEBI static-IP mandate — already in force, and it decides the architecture

**The fact.** developers.kite.trade carries this banner:

> *"Starting **April 1, 2026**, API orders not placed from a registered static IP
> will be **rejected** as per SEBI regulations. You can now register your static
> IP from your profile page."*

**Today is 2026-08-20. That deadline passed nearly five months ago — this is live,
not upcoming.** It reverses the blank-whitelist ruling made hours earlier on this
same page, which was based on the signup form's wording without reading the
banner above it.

**What it changes, and what it does not.** The notice is specific: *API **orders***
are rejected. It does not say market data is. So the split is:

| API use | Needs a registered static IP? |
|---|---|
| Quotes, historical data, instrument lists, WebSocket ticks | **Apparently not** — needs verification |
| **Placing, modifying or cancelling orders** | **Yes. Rejected without one.** |

**Why this strengthens rather than breaks the plan.** Execution was already ruled
manual (2 trades/day is two taps in the Kite app; automation earns nothing at this
frequency). That decision now also **defers the entire static-IP problem**:

- **Phase 1** — signal logger, data only. **Unaffected.** No static IP, no order API.
- **Phase 2** — live micro-size, manual entry. **Unaffected.** Orders go through the
  Kite app, not the API, so the mandate does not bite.
- **Phase 3+ / automated execution** — **blocked** until a static IP exists.

**The cost this would add if execution were ever automated.** The measured
connection is Airtel dynamic (`122.162.148.33`). A static IP is an ISP add-on at
roughly ₹500–1,500/month, or a cloud VM with a fixed address at ₹400–800/month —
and the VM route also reintroduces an always-on runtime to maintain. Either lands
straight back on the fixed-cost problem: on ₹10,000 of capital, ₹500/month is 5%
per month before any trade. **Do not buy one speculatively.**

**Registration is on the Kite profile page**, not per-app. As of this entry: 0 apps
created, Billing (0) — nothing has been charged.

**Open:** confirm whether *market data* calls are genuinely exempt. The whole
phase-1/phase-2 plan rests on that reading of the word "orders", and it has not
been tested against a live key.

---

## 2026-08-20 · Friends get their own Kite app — the terms say so explicitly

**Ruled:** each person runs their own signup, own API key, own account. The code
is shareable; the key, the app and order placement are not.

**Reasoning.** The developers.kite.trade signup carries this checkbox:

> *"I confirm that the above static IPs will be used exclusively by me and/or
> **my immediate family**."*

That settles a question this repo had only speculated about. It is not a SEBI
grey area to be interpreted — **friends are not immediate family**, and sharing
one app with them breaches the agreement directly. Earlier notes here framed it
as a regulatory judgement call; Zerodha's own terms are narrower than SEBI's
framework and are the binding constraint.

---

## 2026-08-20 · Leave the IP whitelist blank — **REVERSED same day, see below**

**Superseded by the SEBI static-IP entry above.** Kept per this file's rule that a
reversed decision keeps its original entry.

**Was ruled:** no IP whitelist on the Kite app.

**Reasoning.** The signup asks for **static** IPs. Measured on the actual
connection: `curl ifconfig.me` returns IPv6 (`2401:4900:…`, Jio, with privacy
extensions that rotate on their own) and `curl -4 ifconfig.me` returns
`122.162.148.33` — Airtel, a real public IPv4 rather than CGNAT, so it *would*
work. But Airtel home broadband is **dynamic**; it holds for days or weeks and
then moves on a lease renewal or router reboot.

A stale whitelist entry fails auth in a way that looks exactly like a code bug,
and static IPs cost ~₹500+/month — landing straight back on the fixed-cost
problem. Blank is correct here, not a compromise.

**Mitigation if a whitelist is ever set:** `KITE_WHITELISTED_IP` in `.env` makes
`tools/auth.py` warn on mismatch at login, so a rotated IP reads as an ISP event
instead of a debugging session.

---

## 2026-08-20 · Cap BOTH sides — asymmetric target and stop is the main lever

**Ruled:** every trade carries a profit target **and** a stop loss, with the stop
tighter than the target. Prefer Zerodha **Cover Orders**, which enforce a stop at
entry.

**Reasoning.** Every earlier model in this repo assumed win == loss, which forces
break-even to ~52%. Capping the downside tighter collapses it:

| Target / Stop | R:R | Win | Loss | Break-even |
|---|---|---|---|---|
| 2.6% / 2.6% | 1:1 | +₹997 | −₹1,083 | 52.1% |
| 2.6% / 1.30% | 2:1 | +₹997 | −₹563 | 36.1% |
| 2.6% / 0.87% | 3:1 | +₹997 | −₹391 | 28.2% |
| 2.6% / 0.65% | 4:1 | +₹997 | −₹303 | **23.3%** |

**At 4:1 you can be wrong three times in four and still profit.** The symmetric
assumption was pessimistic by ~30 percentage points and was simply the wrong
model.

**₹1,000/day is a FREQUENCY question.** A single 4:1 trade wins at most ₹997, so
one trade a day cannot reach ₹1,000 even at 100% accuracy. At 4:1 and 45%
accuracy each trade is worth ₹282, so **~3.5 trades/day** reaches the target —
which matches the original instinct of splitting ₹10,000 across three or four
trades.

**The counter-pressure, which only measurement resolves:** a tighter stop is hit
more often by ordinary noise, so win rate falls as R:R rises. The product is what
matters and phase 1 is what finds the optimum.

**The rule this makes non-negotiable:** three widened stops turn a ₹5,925 month
into ₹1,830 — a 69% haircut from three moments of discretion. "Never widen a
stop" is a hard rule, not a preference, and a Cover Order removes the choice.

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
