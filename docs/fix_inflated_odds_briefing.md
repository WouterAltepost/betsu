# Briefing: inflated odds → fake giant edges → both-sides-of-a-match suggestions

**Date:** 2026-06-13
**Owner of code changes:** CC
**Status:** FIXED + verified (2026-06-13). All four layers (A edge ceiling, B
`_best_odds` coherence filter, C sharp-band, D both-sides guard) implemented;
diagnosis confirmed in stored data (zero credits); 10/10 offline checks pass;
live `--window --dry-run` shows sane favourites, no both-sides, edges ≤ +31%.
Today's 7 poisoned 1X2 rows voided (`result=void`). See "What was done" at the bottom.
**Severity:** high — the value layer *was* suggesting non-existent value (now fixed).

## Symptoms (from the 2026-06-13/14 card)

- The same match is suggested on **both sides**: Brazil vs Morocco shows
  `Home (Brazil)` *and* `Away (Morocco)`; Australia vs Turkey shows both; Haiti vs
  Scotland shows both.
- **Odds on clear favourites are far too long.** Switzerland (heavy favourite vs
  Qatar) priced 5.45; Brazil (vs Morocco) 5.95; Scotland (vs Haiti) 6.45. Real
  prices for those favourites are ~1.4–1.7.
- **Edges are absurd:** +250.8%, +283.6%, +338.8%. Real value vs a World Cup
  closing line is low-single to low-double-digit percent. A +300% edge is always
  a data fault, never a real opportunity.

## Root cause

The odds the value layer prices against are inflated outliers. The model is
roughly sane; the **price** is wrong.

Trace:

1. `value.find_value_bets` (tools/value.py:47-53) computes
   `edge = model_prob * odds - 1` with `odds = m["odds"][outcome]`.
2. `m["odds"]` comes from `fixtures._best_odds` (tools/fixtures.py:55-75), which
   takes the **single highest** decimal price for each outcome across *every*
   bookmaker in the eu payload, with no coherence check.
3. The-odds-api's free eu feed mixes many books; a stale line, an erroneous
   price, or a book that has the fixture's sides swapped will offer a favourite
   at a longshot price. Naive `max()` happily selects that outlier as the "best"
   price. So `odds["1"]` for Brazil becomes ~5.95 instead of ~1.6.
4. Pricing against that inflated number makes `model_prob * odds - 1` blow up,
   and because *both* sides of the match get inflated prices, **both** clear
   `MIN_EDGE` → both are suggested.

Verify with internal consistency (no new data needed): Qatar vs Switzerland #1 —
model 81%, shown odds 5.45, implied 18%, edge +338.8%. `0.81 * 5.45 - 1 = 3.41`.
Every number is consistent with each other; the only wrong input is the 5.45
price on a team that should be ~1.4.

### Why it surfaced now (contributing factor — confirm)

`SHARP_SOFT_MONITORING_ENABLED=1` (set in local `.env`). With it on, the model's
**market layer** is estimated from Pinnacle's de-vig (`run_daily.py:120-122`,
sane), while the **bet price and edge** still use best-price-across-books
(inflated). Before the sharp layer, the model's market layer was the *same*
inflated best-price de-vig as the price, so model and price moved together and
the fake edge partly cancelled. Splitting the model onto a sharp line while still
pricing against polluted best-price odds is what exposed the latent
`_best_odds` weakness. The underlying bug (no coherence check on best price) was
always there; the sharp change made it visible.

This is consistent with, but does not by itself prove, the bad-price theory —
see confirmation below.

## Confirm before/while fixing (cheap, do at least #1)

1. **Zero credits — read the Matches tab (or dashboard).** The morning run stored
   each layer's raw 1X2 plus the blend (`tracker.record_matches`,
   columns market/elo/poisson). For Brazil vs Morocco, compare the recorded
   **market** trio (this is Pinnacle's de-vig, since sharp is on) against the
   bet's `implied_prob`. Expectation if the diagnosis holds: recorded market
   prob for Brazil ≈ 0.5+ (Pinnacle ~1.7), while the bet's `implied_prob` ≈ 0.17
   (best-price 5.95). A large gap between those two **for the same outcome** is
   the bug, in our own stored data.
2. **Optional, 2 credits — one diagnostic odds pull** to see the per-bookmaker
   prices and identify which book(s) set the outlier. Only do this with the
   user's explicit OK (free-tier budget ~500/mo; watch `x-requests-remaining`).
   Not required to implement the fix.

## Fix (layered; smallest first)

### A. Immediate backstop — plausibility edge ceiling (deployable today)

Add to `config.py`:

```python
# Any edge above this is treated as a data fault (stale/incoherent odds), not
# real value, and the selection is dropped. Real value vs a WC line is small;
# a triple-digit edge is always bad data. Fail-safe ceiling on top of MIN_EDGE.
MAX_PLAUSIBLE_EDGE = float(os.environ.get("MAX_PLAUSIBLE_EDGE", "0.35"))
```

In `value.find_value_bets` and `_two_way_value`, change the gate from
`edge >= MIN_EDGE` to `MIN_EDGE <= edge <= MAX_PLAUSIBLE_EDGE`. This alone stops
the absurd suggestions from being posted/placed/graded while the real fix lands.
~3 lines, fully fail-safe, no behaviour change for legitimate bets.

### B. Core fix — only trust coherent bookmakers in `_best_odds`

The principled fix: a bookmaker's price is only usable if that bookmaker's own
1X2 line is internally coherent. Restructure `_best_odds` to iterate per
bookmaker, collect each book's full `{1,X,2}`, compute its overround
`sum(1/price)`, and keep the book only if the overround is in a sane band
(roughly `[1.00, 1.20]` — real books carry 1–20% vig). Then take the best
(highest) price per outcome across the **surviving** books. A side-swapped or
stale book fails its own overround check and is excluded, killing the outlier at
the source while preserving legitimate line-shopping across good books.

Sketch (CC to implement cleanly, keep the existing name→1/X/2 mapping):

```python
def _best_odds(event, min_overround=1.00, max_overround=1.20):
    home, away = event["home_team"], event["away_team"]
    best = {}
    for bk in event.get("bookmakers", []):
        line = {}                      # this book's own 1/X/2
        for market in bk.get("markets", []):
            if market["key"] != "h2h":
                continue
            for oc in market["outcomes"]:
                name, price = oc["name"], oc["price"]
                key = "1" if name == home else "2" if name == away \
                    else "X" if name.lower() == "draw" else None
                if key and price and price > 1.0:
                    line[key] = price
        if {"1", "X", "2"} <= set(line):
            overround = sum(1.0 / line[k] for k in ("1", "X", "2"))
            if not (min_overround <= overround <= max_overround):
                continue            # incoherent book (swapped/stale) → skip it
        for k, price in line.items():
            if k not in best or price > best[k]:
                best[k] = price
    return best
```

Put the band in `config.py` (`ODDS_MIN_OVERROUND` / `ODDS_MAX_OVERROUND`) so it's
tunable. Note: this changes `market_probs` (best-price de-vig) too, which is
correct — those were polluted as well.

### C. Sharp-band sanity (defensive, only when sharp present, near-free)

We already read Pinnacle for free. When `sharp_market_probs` exists, drop any
1X2 selection whose best-price implied prob is wildly below the sharp implied
(e.g. `best_implied < 0.6 * sharp_implied`, i.e. best odds far longer than the
sharp line). Catches a polluted price even if it slips through B.

### D. Both-sides coherence guard (belt-and-suspenders)

After value bets are found for a match, if two **mutually exclusive 1X2**
outcomes (any of 1/X/2) both qualify, the line is incoherent → keep only the
single highest-edge side for that match (or drop the match's 1X2 entirely).
Cheap, and a clear correctness invariant: you can never have genuine value on
two mutually exclusive outcomes of one properly de-vigged market.

## Recommended sequence

1. Ship **A** (edge ceiling) now to stop bad suggestions immediately.
2. Implement **B** (coherence filter) as the real fix; add **D** as the
   invariant guard.
3. Add **C** while sharp monitoring is on.
4. Re-run `--window --dry-run` and confirm the favourites now price ~1.4–1.7,
   edges collapse to sane single/low-double digits, and no match shows both
   sides.

## Data already written today

The inflated odds were stored on today's Bets rows, so the **units/paper** track
will mis-grade (overstated P&L on any winning favourite, since e.g. 5.95 is
recorded instead of ~1.6). After the fix, consider correcting or voiding
today's affected rows so the calibration benchmark isn't poisoned. The
real-money € track is unaffected unless the user actually staked off these.

## Verify before calling it done

- `python -m py_compile tools/fixtures.py tools/value.py config.py`.
- Extend `test_new_features.py` / `tests/` with: an event carrying one
  side-swapped/stale book → `_best_odds` excludes it and returns sane prices; a
  fabricated +300% edge → dropped by the ceiling; a both-sides case → guard keeps
  one side. Offline, no network, no credits.
- `python run_daily.py --window --dry-run` and eyeball the card: favourite odds
  sane, edges sane, no match on both sides.
```

## What was done (2026-06-13)

**Confirmed (zero credits).** Read the stored Matches + Bets tabs. Brazil v
Morocco: recorded market (Pinnacle de-vig) `mkt_1 = 0.571` for Brazil, but the
bet's `implied_prob = 0.168` (odds 5.95), edge +250.8%. Same pattern on Qatar v
Switzerland (mkt 0.80 vs implied 0.18, +338.8%) and Haiti v Scotland (+283.6%).
The same-outcome gap between Pinnacle and best-price is the bug, in our own data.

**Code (all four layers).**
- **A** — `MAX_PLAUSIBLE_EDGE = 0.35` in `config.py`; gate in
  `value.find_value_bets` and `_two_way_value` is now `MIN_EDGE <= edge <= MAX_PLAUSIBLE_EDGE`.
- **B** — `fixtures._best_odds` rewritten to iterate per bookmaker, compute each
  book's own 1X2 overround, and skip any book outside
  `[ODDS_MIN_OVERROUND, ODDS_MAX_OVERROUND]` = `[1.00, 1.20]` before taking the
  best surviving price. Side-swapped/stale books are excluded at the source.
- **C** — `find_value_bets` takes an optional `sharp_probs`; a selection whose
  best-price implied prob is `< SHARP_IMPLIED_MIN_RATIO (0.6) * sharp_implied` is
  dropped. Wired from `run_daily.py` (Pinnacle line) when sharp monitoring is on.
- **D** — `find_value_bets` keeps only the single highest-edge side when more than
  one mutually-exclusive 1X2 outcome qualifies.

**Tests.** Four new offline checks in `test_new_features.py` (coherence filter,
edge ceiling, both-sides guard, sharp band) — suite now 10/10, no network.

**Verified.** `--window --dry-run` on live odds: favourites no longer priced as
longshots, no match on both sides, max 1X2 edge +30.6% (a plausible Brazil draw,
under the ceiling); the +250–339% fakes are gone.

**Poisoned rows voided.** The 7 already-written 1X2 rows across the four matches
with incoherent h2h lines (Qatar/Switzerland, Brazil/Morocco, Haiti/Scotland,
Australia/Turkey) were set `result=void` — `grade_pending` skips non-pending rows
and `summary` excludes `void` from wins/losses/pending, so the units benchmark is
clean. The OU2.5/BTTS rows are priced off the separate totals/btts markets (never
touched by the `_best_odds` bug) and were left intact.
