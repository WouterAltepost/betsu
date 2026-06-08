# Briefing: BTTS value bets via the per-event odds endpoint

**For:** Claude Code. **Author:** planning pass in Cowork.
**Goal:** Unlock both-teams-to-score (BTTS) value bets. Poisson already computes
BTTS probabilities; we just need the book's BTTS price to value them against.
`btts` is NOT a featured market, so it can't come from the bulk `/odds` call
(that's what 422'd and caused the earlier 500). It only exists on the per-event
endpoint `GET /v4/sports/{sport}/events/{eventId}/odds?markets=btts`.

Read first: `tools/fixtures.py`, `run_daily.py`, `tools/value.py`,
`tools/tracker.py` (note the existing `context_*` cache helpers — copy that
pattern), `config.py`.

## Cost reality (this drives the design)

the-odds-api bills the per-event endpoint 1 credit per market per region **per
event request**. WC 2026 has 104 matches. Fetching BTTS for every event on every
scan (2/day, matches sit in the 18h window for ~2 scans) would be ~200+ credits
on top of the bulk calls — close to the whole remaining budget. So per-event
BTTS MUST be cached and gated. Design for ~1 fetch per match, not per scan.

## Work items

1. **Config** (`config.py` / `.env.example`):
   - `BTTS_ENABLED` (env, default `1`). One switch to kill BTTS fetching if the
     odds budget gets tight mid-tournament.
   - `BTTS_CACHE_HOURS` (default 12).
   - Add a `BttsOdds` (or reuse a generic) cache tab name constant.

2. **Bulk fetch keeps the event id** (`tools/fixtures.py`):
   - In `get_matches`, add `"event_id": ev["id"]` to each match dict. The bulk
     call stays `markets=h2h,totals` (unchanged, do not add btts here).

3. **Per-event BTTS fetch** (`tools/fixtures.py`):
   - New `fetch_event_btts(event_id, region=ODDS_REGION)` calling
     `{ODDS_API_BASE}/sports/{sport}/events/{event_id}/odds` with
     `markets=btts, oddsFormat=decimal`. Parse best Yes/No across books (reuse
     the `_best_btts` logic). Return `{"Yes": odds, "No": odds}` or `None`.
   - Be resilient: a 404/422/empty for an event returns `None`, never raises.

4. **Cache + gate in the scan** (`run_daily.py`, inside the per-match loop, only
   when the match is seeded and `BTTS_ENABLED`):
   - Key the cache by `event_id`. Add tracker helpers mirroring the Context
     cache: `fetch_btts_odds(event_id)` / `upsert_btts_odds(event_id, yes, no,
     fetched_at)`. On a cache hit within `BTTS_CACHE_HOURS`, use it; otherwise
     call `fetch_event_btts`, upsert, and use the result.
   - Pass the resulting odds to the existing
     `value_mod.find_value_btts(m_date, home, away, poisson_mkts["btts"], odds)`.
     That function already returns `[]` when odds are `None`, so no value is
     forced when BTTS isn't offered.
   - This bounds calls to roughly one per event per 12h. Log a one-line note per
     fetch so credit use is visible.

5. **Everything downstream already works.** `find_value_btts` produces bets with
   `market="BTTS"`, the tracker dedups and grades them (`_bet_won` handles BTTS),
   and the card/dashboard render them. No changes needed there.

## Acceptance criteria

- With `BTTS_ENABLED=0`, behaviour is identical to today (no per-event calls).
- With it on, a scan fetches BTTS once per event, reuses the cache on the next
  scan within the TTL (verify: no second per-event call), and surfaces a BTTS
  value bet when Poisson's BTTS prob beats the book price by >= `MIN_EDGE`.
- A per-event fetch that 404s/empties yields no BTTS bet and does not error.
- Grading a BTTS bet still settles correctly against a Results row.
- Bulk `/odds` call is unchanged (`h2h,totals`); `/run/morning` never 422s.

## Out of scope

Other additional markets (corners, cards, spreads), and any change to the
featured-market bulk fetch.
