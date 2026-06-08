# Briefing: football-data.org auto-results (hands-off grading)

**For:** Claude Code. **Author:** planning pass in Cowork.
**Goal:** Before each grade run, automatically pull finished World Cup scores
from football-data.org and write them to the Results tab, so `grade_pending`
settles bets without anyone hand-typing scores. Manual entry must keep working
as the fallback and as an override.

Read first: `tools/tracker.py` (`record_result`, `fetch_bets`,
`fetch_results`, the `Results` tab), `run_daily.py` (`run_grade`),
`tools/elo.py` (the `ALIASES` map + `rapidfuzz` usage — reuse that approach for
name matching), `config.py`, `.env.example` (`FOOTBALL_DATA_API_KEY` exists).

## The one hard part: team-name reconciliation

Bets are recorded under the-odds-api's team names. football-data.org uses its
own names (e.g. "Korea Republic" vs "South Korea", "USA" vs "United States",
"Côte d'Ivoire" vs "Ivory Coast"). If a result is written under a name that
doesn't match the bet's name, grading silently won't settle it. So results must
be recorded under the SAME names the bets already use.

Approach: for each finished football-data match, find the matching fixture in
our store (pending bets / Matches tab) on the same UTC date (+/- 1 day to cover
midnight boundaries) by fuzzy-matching both team names (rapidfuzz, same
threshold as elo). Record the result under the STORE's names, not
football-data's. If no confident store match is found, skip it (don't invent
rows) and log it for visibility.

## Work items

1. **Config** (`config.py` / `.env.example`):
   - `FOOTBALL_DATA_BASE = "https://api.football-data.org/v4"`
   - `FOOTBALL_DATA_COMPETITION = "WC"` (verify this is the 2026 World Cup code
     via the API; football-data's free tier should include WC — if it does NOT,
     log a clear message and no-op, leaving manual entry intact).
   - `AUTO_RESULTS_ENABLED` (env, default `1`).
   - `RESULTS_LOOKBACK_DAYS` (default 3).

2. **New tool `tools/results_fetch.py`:**
   - `fetch_finished(date_from, date_to)` -> list of
     `{utc_date, home, away, home_score, away_score}` from
     `GET {BASE}/competitions/{WC}/matches?status=FINISHED&dateFrom=&dateTo=`
     with header `X-Auth-Token: FOOTBALL_DATA_API_KEY`. Pull `score.fullTime`.
   - `sync_results(store_fixtures)` -> for each finished match, fuzzy-reconcile
     to a store fixture (date +/-1, both names match) and call
     `tracker.record_result(...)` under the store's names. Return a count +
     a list of unmatched football-data fixtures (for the log).
   - Fully fail-safe: any network/parse/auth error logs and returns 0, so a
     football-data outage never blocks grading of already-known results.

3. **Wire into `run_grade`** (`run_daily.py`): when `AUTO_RESULTS_ENABLED` and
   the key is present, call `results_fetch.sync_results(...)` BEFORE
   `grade_pending()`, using the pending bets/Matches as the reconciliation
   source and a date range of the last `RESULTS_LOOKBACK_DAYS`. Then grade as
   normal. Include the synced/unmatched counts in the printed summary.

4. **Manual entry stays authoritative.** `record_result` already upserts by
   `(match_date, home, away)`. If a score was hand-typed, re-writing the same
   value is harmless; do not overwrite a hand-typed score with a conflicting
   auto value without logging the discrepancy.

## Acceptance criteria

- With `AUTO_RESULTS_ENABLED=0` or no key: grade behaves exactly as today
  (reads whatever is in Results).
- With it on: a finished WC match is fetched, reconciled to the stored fixture
  by fuzzy name match, written under the store's team names, and the matching
  pending bets settle on the same grade run.
- A football-data name variant (e.g. "Korea Republic") still resolves to the
  bet's name (e.g. "South Korea") and settles.
- A football-data outage or unknown competition code logs and no-ops; manual
  Results entries still grade.
- No fabricated Results rows for fixtures not in our store.

## Cost / rate

football-data free tier is ~10 requests/min; this is one request per grade run
(once a day). Negligible. Confirm the free tier actually serves competition
`WC` for 2026; if not, the tool no-ops and you keep typing scores into the
Results tab.

## Out of scope

Live/in-play scores, non-WC competitions, and changing the grading math.
