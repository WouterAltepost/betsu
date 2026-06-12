# Accuracy fixes briefing (for Claude Code)

One session, one branch, one clean diff. This briefing supersedes the optimistic
claims in `IMPLEMENTATION_SUMMARY.md` / `QUICK_START_FEATURES.md`: the variance
layer crashes, and the xG and sharp/soft layers are non-functional stubs. None of
that work is committed yet (it is all uncommitted working-tree changes), so
production on Railway is untouched. Do not deploy any of it until the fixes below
land and the verification section passes.

Three deliverables:

1. Fix the variance-scaling crash and harden the ensemble so no single layer can
   ever take down a run again.
2. Make the sharp/soft layer real by reading Pinnacle's line from the existing
   the-odds-api payload (zero extra API credits). Delete the dead direct-Pinnacle
   code (Pinnacle shut public API access on 2025-07-23, no retail keys exist).
3. Make the xG layer real using `soccerdata` (FBref, `INT-World Cup`). The current
   Sofascore scrape always returns `None` and the team-ID map is fabricated.

Keep every layer flag-gated and fail-safe. A layer that errors must drop itself
and let the blend renormalise, never raise into `run_morning`.

---

## Pre-flight

- Branch off current `main`/`master`.
- Confirm the starting state: `tools/xg.py` and `tools/sharp_soft.py` are
  untracked; `config.py`, `run_daily.py`, `tools/ensemble.py`, `tools/poisson.py`,
  `tools/value.py` are modified but uncommitted. `tools/ensemble.py` and
  `tools/value.py` are already correct, leave them alone.
- `pip install -r requirements.txt` after you update it (Fix 3 adds a dependency).

---

## Fix 1 — variance crash + ensemble hardening

### 1a. The crash (must fix)

`tools/poisson.py:_apply_variance_scaling` calls `.get()` on a list. `grid` is a
`list[list[float]]`; lists have no `.get`. It raises `AttributeError` for every
home-favoured match with `|elo_diff| > VARIANCE_ELO_THRESHOLD` (most matches), and
because `poisson.markets()` is called unguarded in `run_morning`, it takes down the
whole run. Reproduce before and after:

```bash
python tools/poisson.py "Brazil" "Bolivia"     # crashes now; must print markets after
python tools/poisson.py "Bolivia" "Brazil"     # already works (away-favoured branch)
```

The bug is the home-favoured branch (around lines 155-160):

```python
# BROKEN — grid[i] is a list, not a dict
grid[i][0] = min(1.0, grid[i].get(0, 0) + total_redistribution * 0.4 / max_goals)
grid[i][1] = min(1.0, grid[i].get(1, 0) + total_redistribution * 0.1 / max_goals)
```

Replace with plain list indexing, mirroring the (correct) away-favoured branch:

```python
grid[i][0] = min(1.0, grid[i][0] + total_redistribution * 0.4 / max_goals)
grid[i][1] = min(1.0, grid[i][1] + total_redistribution * 0.1 / max_goals)
```

Add a guard so the index can never go out of range (`i` runs to `max_goals`, fine,
but be explicit): the `if i < len(grid)` check is already there; keep it.

### 1b. Default the layer OFF until it is validated

The redistribution heuristic is unproven and ad hoc (it moves a flat 1% of mass
from the 2-3 goal cells to the tails, scaled by a hand-picked factor). Fixing the
crash makes it run, not makes it right. Flip the default to off so a fixed-but-
unvalidated heuristic does not silently shape live bets:

```python
# config.py
VARIANCE_SCALING_ENABLED = os.environ.get("VARIANCE_SCALING_ENABLED", "0").strip() in ("1", "true", "True")
```

We turn it on deliberately later, after backtesting calibration with and without
it. Leave `VARIANCE_ELO_THRESHOLD` and `VARIANCE_SCALE_FACTOR` as they are.

### 1c. Harden the ensemble (defence in depth)

Even with the bug fixed, a future layer bug should degrade gracefully, not crash a
live run. In `run_daily.py:run_morning`, wrap the Poisson call so a failure drops
the Poisson layer (and the goal-based markets) for that match and continues:

```python
poisson_mkts = None
if not unseeded:
    preds["elo"] = elo_mod.predict(home, away, ratings, neutral=neutral)
    try:
        poisson_mkts = poisson_mod.markets(home, away, ratings, neutral=neutral)
        preds["poisson"] = poisson_mkts["1x2"]
    except Exception as e:
        poisson_mkts = None
        print(f"  [poisson: skipped — {type(e).__name__}]")
```

The xG and LLM blocks are already wrapped / fail-safe; leave their structure but
note the xG block is rewritten in Fix 3.

---

## Fix 2 — sharp odds from the existing the-odds-api payload

### Why the current approach is dead

`tools/sharp_soft.py:fetch_pinnacle_odds` always returns `None`, hits a Pinnacle
endpoint that no longer serves retail, and `get_sharp_odds` mislabels "highest
price per outcome across books" as "sharpest" (taking the max price on every
outcome and de-vigging it understates probabilities and fabricates edges). Pinnacle
killed public API access on 2025-07-23 (commercial partners only), so there is no
key to get.

### The correct, free approach

the-odds-api already returns Pinnacle as one bookmaker inside the `eu` region
payload we fetch in `fixtures.get_matches`. Billing is per market per region,
independent of bookmaker count, so reading Pinnacle's block costs **zero extra
credits**. Use Pinnacle's own de-vigged 1X2 as the market-probability layer (a
single sharp book is the textbook market estimate); keep best-price-across-books
(`m["odds"]`) for the actual bet price. This is a real calibration win, not a stub.

### Implementation

1. **Verify the bookmaker key once.** The key is expected to be `"pinnacle"`.
   Confirm against one live event before wiring (watch `x-requests-remaining`; one
   intentional call is fine, do not loop). If the slate is empty pre-kickoff, parse
   a saved sample response instead.

2. **Expose the sharp line in `fixtures.py`.** Add a helper that pulls a named
   bookmaker's h2h 1X2 best prices from a raw event, and compute its de-vig in
   `get_matches`. Add one field to each match dict; do not remove existing fields.

   ```python
   SHARP_BOOKMAKER_KEY = "pinnacle"  # config.py is fine too

   def _book_h2h_odds(event, book_key):
       """1X2 decimal odds from a single bookmaker, or {} if absent."""
       home, away = event["home_team"], event["away_team"]
       out = {}
       for bk in event.get("bookmakers", []):
           if bk.get("key") != book_key:
               continue
           for market in bk.get("markets", []):
               if market["key"] != "h2h":
                   continue
               for oc in market["outcomes"]:
                   name, price = oc["name"], oc["price"]
                   key = "1" if name == home else "2" if name == away else \
                         "X" if name.lower() == "draw" else None
                   if key:
                       out[key] = price
       return out
   ```

   In `get_matches`, after computing `odds = _best_odds(ev)`:

   ```python
   sharp_raw = _book_h2h_odds(ev, SHARP_BOOKMAKER_KEY)
   sharp_probs = _devig(sharp_raw) if {"1", "X", "2"} <= set(sharp_raw) else None
   ...
   matches.append({
       ...,
       "market_probs": _devig(odds),       # best-price devig (unchanged fallback)
       "sharp_market_probs": sharp_probs,   # Pinnacle devig, or None
       ...
   })
   ```

3. **Use it in `run_daily.py`.** Replace the whole `SHARP_SOFT_MONITORING_ENABLED`
   block in `run_morning` with a clean swap of the market layer source:

   ```python
   odds_for_blend = m["market_probs"]
   if SHARP_SOFT_MONITORING_ENABLED and m.get("sharp_market_probs"):
       odds_for_blend = m["sharp_market_probs"]
       print(f"  [sharp: using {fixtures_mod.SHARP_BOOKMAKER_KEY} line for {home} vs {away}]")
   preds = {"market": odds_for_blend}
   ```

   The actual bet price stays `m["odds"]` via `value_mod.find_value_bets(... m["odds"])`
   — unchanged. Note the subtlety in a comment: betting at best-price-across-books
   while estimating the market from a sharp book is intentional and correct.

4. **Rewrite `tools/sharp_soft.py` down to what is used, or delete it.** The
   per-bookmaker extraction now lives in `fixtures.py`, so `sharp_soft.py` is
   redundant. Prefer deleting it and removing its import. If you keep it for a
   future multi-book vig report, strip `fetch_pinnacle_odds`, the Pinnacle base URL,
   the API-key plumbing, and the "max price = sharpest" logic. Do not leave dead
   network code in the tree.

5. **Config cleanup.** Remove `PINNACLE_ENABLED`, `PINNACLE_API_KEY` usage, and
   `USE_SHARPEST_MARKET` if `sharp_soft.py` is deleted. Keep
   `SHARP_SOFT_MONITORING_ENABLED` (default off) as the single switch.

---

## Fix 3 — real xG via soccerdata (FBref)

### Decision and rationale

National-team xG is the hard case: Understat is club-only, Sofascore has no public
API and is Cloudflare-protected, and the current `tools/xg.py` Sofascore scrape
returns `None` with a fabricated team-ID map. Use **`soccerdata`**, which scrapes
FBref (Opta-sourced xG) and ships the men's World Cup as a first-class league. The
confirmed identifier is `INT-World Cup`. One `read_team_match_stats` call returns
every team's per-match xG and xGA, so the request count is tiny and cache-friendly.

```python
import soccerdata as sd
sd.FBref.available_leagues()
# [..., 'INT-European Championship', "INT-Women's World Cup", 'INT-World Cup', ...]
```

**Known tradeoffs, state them honestly in the PR:**

- **Dependency weight.** `soccerdata` pulls `pandas`/`lxml` and a `seleniumbase`
  chain. FBref reads use plain HTTP (no browser at runtime), but the install is
  heavier than betsu's current deps and grows the Railway image. Accepted for
  robustness; if image size becomes a problem we revisit a thin `pandas.read_html`
  fetch later.
- **Cold sample early in the group stage.** On 2026-06-12 teams have played 0-1 WC
  matches, so xG is thin or absent. That is fine: the layer requires a minimum
  sample (below) and returns `None` otherwise, so the blend renormalises over the
  other layers. xG becomes meaningful from matchday 2-3 onward. Do not try to bolt
  on qualifier/Nations League comps now (FBref xG coverage there is uneven across
  confederations) — that is a separate, later decision.
- **Scraping fragility.** soccerdata can break if FBref changes layout. The layer
  is fail-safe, so a break degrades to "xG absent", never a crash.

### Column-availability check (do this first, in a scratch script)

FBref's squad "Scores & Fixtures" table carries `xG`/`xGA` per match for
competitions Opta covers. Confirm it is populated for `INT-World Cup` season `2026`
this early before wiring anything:

```python
import soccerdata as sd
fb = sd.FBref(leagues="INT-World Cup", seasons=2026)
df = fb.read_team_match_stats(stat_type="schedule")   # all teams, one cached pull
print(df.columns.tolist())
print(df[["date", "opponent", "gf", "ga"]].head())    # adjust to real column names
# Confirm xG / xGA columns exist and have non-null values.
```

If `xG`/`xGA` are absent or empty this early, the layer correctly yields nothing
yet — document that and move on; the wiring still ships and activates later. If the
`schedule` table lacks xG, fall back to `read_team_season_stats(stat_type="standard"
or "shooting")` and read the `Expected` block (`xG`, and the opponent/`vs` table for
xGA). Pick whichever actually carries populated xG for WC 2026 and note your choice.

### Probability conversion — use Poisson, not the current heuristic

The current `get_xg_probability` anchors to a fixed 47/6/47 split (a 6% draw is
nonsense) and never sees real data anyway. Replace it with a proper xG→goals→1X2
conversion that reuses the tested Poisson grid.

1. Add a public helper to `tools/poisson.py` so both layers share one code path:

   ```python
   def markets_from_lambdas(lam_home, lam_away):
       """Full market dict from explicit expected goals (no Elo, no variance scaling)."""
       lam_home = max(lam_home, POISSON_GOAL_FLOOR)
       lam_away = max(lam_away, POISSON_GOAL_FLOOR)
       grid = score_matrix(lam_home, lam_away, elo_diff=0.0)  # elo_diff=0 -> no variance
       return _markets_from_grid(grid)
   ```

2. Derive lambdas from team xG the standard way:

   ```
   lam_home = (home_xg_for + away_xg_against) / 2
   lam_away = (away_xg_for + home_xg_against) / 2
   ```

### Rewrite `tools/xg.py`

Delete the fabricated `SOFASCORE_TEAM_IDS` map, the BeautifulSoup scrape, and the
4-call `fetch_team_xg` interface. New shape:

- `_load_xg_table(ratings)` -> `{canonical_team: {"xg_for": float, "xg_against": float, "matches": int}}`
  - Pull once via soccerdata (`INT-World Cup`, season from a config constant, e.g.
    `XG_SEASON = 2026`). Aggregate each team's last `XG_MATCHES_BACK` matches into
    average xG for and against.
  - **Reconcile FBref names through the existing resolver.** For each FBref team
    name, `canonical = elo.lookup_rating(fbref_name, ratings)[1]`. If `None`, skip
    that team (unmapped). This reuses the ALIASES + accent-fold + fuzzy≥90 +
    ambiguity guard. **Do not write your own matcher and do not lower the
    threshold** (Austria/Australia, Iran/Iraq collide below 90). When a real WC
    feed name falls back to default, add its exact FBref spelling to `elo.ALIASES`
    (expect at least: `"Korea Republic"`→`"South Korea"`, `"IR Iran"`→`"Iran"`,
    `"Türkiye"`/`"Turkiye"`→`"Turkey"`, `"United States"` should already resolve).
  - Cache the whole table in-process with a TTL of `XG_CACHE_HOURS`. On stateless
    Railway each cold run rebuilds it once (a couple of HTTP calls), which is fine.
    Point soccerdata's `data_dir` at `config.TMP_DIR` so its disk cache lands on a
    writable path.
- `get_xg_prediction(home, away, ratings)` -> `{"1","X","2"}` or `None`
  - Return `None` immediately if `not XG_ENABLED`.
  - Look up both teams in the table. If either is missing, or either has fewer than
    `XG_MIN_MATCHES` matches of data, return `None`.
  - Compute lambdas as above and return `poisson.markets_from_lambdas(...)["1x2"]`.
  - Wrap the whole body in try/except → on any error, log `[xg: skipped — ...]`
    and return `None`. The layer must never raise.
- Keep a `--test` CLI path that prints the resolved table size and one sample
  prediction.

### Rewire `run_daily.py`

Replace the entire existing `if XG_ENABLED:` block (the four `fetch_team_xg` calls
plus `get_xg_probability`) with one call:

```python
if XG_ENABLED:
    from tools import xg as xg_mod
    xg_prob = xg_mod.get_xg_prediction(home, away, ratings)
    if xg_prob:
        preds["xg"] = xg_prob
        print(f"  [xg: {xg_prob}]")
```

`get_xg_prediction` is already fully fail-safe internally, so no extra try/except
is needed here, but it does no harm if you keep one.

### Config (`config.py`)

```python
XG_ENABLED = os.environ.get("XG_ENABLED", "0").strip() in ("1", "true", "True")
XG_SEASON = int(os.environ.get("XG_SEASON", "2026"))
XG_MATCHES_BACK = int(os.environ.get("XG_MATCHES_BACK", "5"))
XG_MIN_MATCHES = int(os.environ.get("XG_MIN_MATCHES", "2"))   # need >= this many matches of data
XG_CACHE_HOURS = int(os.environ.get("XG_CACHE_HOURS", "24"))
```

Keep `ENSEMBLE_WEIGHTS["xg"] = 0.05`. Keep `XG_ENABLED` default off; enable it on
Railway only after the column-availability check confirms live WC xG is flowing.

### requirements.txt

Add `soccerdata`. Pin the version you install and test against (record it in the PR
so the Railway build is reproducible). Note the heavier transitive deps in the PR
description.

---

## Verification (all must pass before this is "done")

Run from the repo root. Nothing here should need a paid API call except the single
deliberate Pinnacle-key check in Fix 2.

```bash
# 1. Compiles
python -m py_compile config.py run_daily.py tools/poisson.py tools/xg.py tools/fixtures.py tools/ensemble.py tools/value.py

# 2. Variance crash is gone (both must print markets, neither may traceback)
python tools/poisson.py "Brazil" "Bolivia"
python tools/poisson.py "Bolivia" "Brazil"

# 3. Poisson lambda helper works
python -c "from tools import poisson as p; print(p.markets_from_lambdas(1.8, 0.7)['1x2'])"

# 4. xG module loads, resolves a team table, and is fail-safe with XG_ENABLED off
python tools/xg.py --test
XG_ENABLED=1 python tools/xg.py --test     # prints table size + a sample prediction or a clean 'absent'

# 5. Existing offline tests still pass
python -m pytest -q

# 6. Update and run the smoke suite — it must run to completion (no harness crash)
python test_new_features.py

# 7. Dry run, default flags (variance off, xG off, sharp off): must produce a card
python run_daily.py --window --dry-run

# 8. Dry run with the new layers on (uses budget for the odds call — run once):
XG_ENABLED=1 SHARP_SOFT_MONITORING_ENABLED=1 python run_daily.py --window --dry-run
#    Expect: '[sharp: using pinnacle line ...]' on matches Pinnacle prices, and
#    '[xg: ...]' on matches with enough xG data (may be none this early — that's OK).
```

Also fix `test_new_features.py` itself: it currently aborts the whole script at the
Poisson test because the call is unguarded. Wrap each feature check so one failure
reports and continues, and update the xG check to the new `get_xg_prediction`
interface.

Watch `x-requests-remaining` on any live odds call. Do not run `--window` (the
real, non-dry path) or repeated `--dry-run`s to "test" — one dry run on the live
slate is enough.

---

## Out of scope (do not do in this session)

- Turning variance scaling back on (needs a backtest first).
- Adding qualifier/Nations League comps to the xG source.
- Any Sheets schema change (xG/sharp state stays in code + in-process cache).
- Any change to `app.py`, the dashboard, or the mobile PWA.
- Committing `betsu-documentation.pdf`, `reference-image.png`, or the loose
  `IMPLEMENTATION_SUMMARY.md` / `QUICK_START_FEATURES.md` / `VERIFICATION_CHECKLIST.md`
  scratch files — leave them untracked or delete them; they overstate status.

## Commit guidance

One focused commit (or three small ones): `fix(poisson): variance scaling crash +
default off`, `feat(odds): sharp market layer from pinnacle line`, `feat(xg): real
FBref xG layer via soccerdata`. Do not commit secrets. Update `CLAUDE.md` only if a
flag name or data source changed materially (xG source is now FBref/soccerdata, not
Sofascore).
