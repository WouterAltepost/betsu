# Daily Run — Scan, Predict, Suggest, Track

## Objective
Each run blends upcoming fixtures into value bets, posts a Telegram card with the
genuinely-new bets, and logs everything to the Google Sheets store. A grade run
settles finished bets.

In production the runs are triggered by **n8n** hitting the service's endpoints
(see `docs/deploy_runbook.md`); the CLI below is the same logic for manual use.

## Scan (scheduled: ~09:00 and ~20:00 Amsterdam)

Production: `POST /run/morning` with header `X-Run-Key: <RUN_API_KEY>`.

Manual equivalent:
```bash
python run_daily.py --window          # scan the next SCAN_WINDOW_HOURS (default 18)
python run_daily.py --window --dry-run # preview the card, send/store nothing
python run_daily.py --date=2026-06-11  # date mode (one UTC day), for backfill/testing
```

Steps the agent runs:
1. Load Elo ratings (`data/elo_seed.json`).
2. Fetch fixtures + odds via the-odds-api (`tools/fixtures.py`). In window mode it
   takes games that have **not kicked off** and start within the next
   `SCAN_WINDOW_HOURS`; each bet is dated by its own kickoff (UTC).
3. Per match: de-vigged market probs + Elo + Poisson → ensemble blend.
4. Find value bets (edge ≥ 5%); keep only selections **not already posted**
   (dedup); rank and cap at the daily max.
5. Record match probs + the new bets to the **Bets** tab; refresh **Summary**.
6. Post the card (the new bets) to Telegram.

Two scans/day cover an afternoon→~03:00 slate: a late game is posted from the
previous evening's run, before kickoff. Re-running posts nothing new.

**Behaviour notes:**
- No new bets (quiet slate, or everything already posted earlier): the run is
  silent — nothing is sent. (`--dry-run` always prints the card, including a
  "sitting out" message when empty.)
- No `ODDS_API_KEY`: fixtures step raises; fix `.env` / Railway vars and rerun.
- Telegram unreachable: bets are already stored; the next run re-posts only what's
  still new.

## Grade (scheduled: ~10:00 Amsterdam)

Production: `POST /run/grade` with header `X-Run-Key: <RUN_API_KEY>`.

Manual equivalent:
```bash
python run_daily.py --grade
```

1. Read final scores from the **Results** tab.
2. Settle pending bets (1X2, OU2.5, BTTS), updating `result` + `pnl_units` in
   place; refresh **Summary**.
3. Send a results recap to Telegram.

### Recording results
The sheet is the hub: type `home_score` / `away_score` into the **Results** tab
(keyed by `match_date, home_team, away_team`), then run grade. Or, from code:
```python
from tools import tracker
tracker.record_result("2026-06-11", "Argentina", "Mexico", 2, 0)
tracker.grade_pending()
```
(A later briefing can wire football-data.org auto-results.)

## Pre-tournament testing (before June 11)
No World Cup games yet. Test the pipeline on any live soccer:
```bash
python tools/fixtures.py --sports          # find an active sport key
# set that key in config.ODDS_SPORT_WORLDCUP temporarily, then:
python run_daily.py --window --dry-run
```

## Expected output
- Rows in the Google Sheet: **Matches** + **Bets** (later graded), **Results**,
  **Summary**. The dashboard (`GET /`) renders them.
- A Telegram bet card per scan, a recap per grade.

## Tuning
- Edge threshold, daily cap, stake, ensemble weights, `SCAN_WINDOW_HOURS`: all in
  `config.py`.
- If value bets are too rare, lower `MIN_EDGE`; too noisy, raise it.
- Refresh Elo seeds from eloratings.net before kickoff for best accuracy.
