# Daily Run — Scan, Predict, Suggest, Track

## Objective
Each morning, blend the day's fixtures into value bets, send a Telegram card,
and log everything. Each evening, grade the day's bets.

## Morning (recommended ~10:00 local)

```bash
python run_daily.py            # or --dry-run first to preview without sending
```

Steps the agent runs:
1. Load Elo ratings (`data/elo_seed.json`).
2. Fetch today's fixtures + odds via the-odds-api (`tools/fixtures.py`).
3. Per match: de-vigged market probs + Elo probs -> ensemble blend.
4. Find value bets (edge >= 5%), rank, cap at the daily max.
5. Record matches + bets to SQLite.
6. Send the bet card to Telegram.

**On failure:**
- No `ODDS_API_KEY`: fixtures step raises; fix `.env` and rerun.
- No matches today (e.g. between tournament stages): card says "sitting out", still sends.
- Telegram unreachable: bets are already stored; resend later.

## Evening (after matches finish)

```bash
python run_daily.py --grade
```

1. Read recorded results (manual entry or `fetch_results.py`).
2. Grade pending bets, update P&L.
3. Send a results recap to Telegram.

### Recording results
Until `fetch_results.py` is wired, enter scores manually:
```python
from tools import tracker
tracker.record_result("2026-06-11", "Argentina", "Mexico", 2, 0)
tracker.grade_pending()
```

## Pre-tournament testing (before June 11)
No World Cup games until June 11. Test the full pipeline on any live soccer:
```bash
python tools/fixtures.py --sports        # find an active sport key
# set that key in config.ODDS_SPORT_WORLDCUP temporarily, then:
python run_daily.py --dry-run
```

## Expected output
- SQLite rows in `data/betsu.db` (matches + bets, later graded).
- A Telegram bet card each morning, a recap each evening.

## Tuning
- Edge threshold, daily cap, stake, ensemble weights: all in `config.py`.
- If value bets are too rare, lower `MIN_EDGE`; too noisy, raise it.
- Refresh Elo seeds from eloratings.net before kickoff for best accuracy.
