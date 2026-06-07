# Briefing: deploy betsu (Sheets-backed store, n8n-scheduled)

**For:** Claude Code. **Author:** planning pass in Cowork.
**This supersedes any earlier volume + in-process-scheduler plan.** No Railway
volume, no APScheduler, no SQLite.

## The shape

- **Google Sheets is the single source of truth.** Drop SQLite entirely.
- **Railway** runs one stateless Flask service (gunicorn): it serves the
  dashboard AND exposes protected run endpoints. No persistent disk.
- **n8n** owns all scheduling. It calls the run endpoints on a schedule.
- The value/ensemble/Elo/Poisson/Telegram logic does NOT change.

Read first: `run_daily.py`, `tools/tracker.py`, `tools/sheets.py`,
`tools/fixtures.py`, `tools/value.py`, `dashboard.py`, `config.py`. Keep the WAT
separation. Commit any uncommitted work before starting.

## Work items

### 1. Move the data layer onto Sheets (keep the interface)

Reimplement `tools/tracker.py` so its existing public functions keep the same
names and signatures but read/write Google Sheets instead of SQLite:
`record_match`, `record_bet`, `record_result`, `grade_pending`, `summary`,
`fetch_bets`, `fetch_results`. Because the interface is unchanged,
`run_daily.py` and `dashboard.py` keep working with minimal edits.

- Fold the Sheets auth/open helpers from the current `tools/sheets.py` into the
  new tracker (auth via `gspread`). Then remove the old mirror-only `sheets.py`
  (its job no longer exists; Sheets is now primary, not a mirror).
- Tabs and columns (create tabs on first use if missing):
  - **Bets**: `match_date, commence_time, home_team, away_team, market,
    selection, selection_label, model_prob, implied_prob, odds, edge,
    stake_units, kelly_units, staked_real, result, pnl_units, created_at`.
  - **Results**: `match_date, home_team, away_team, home_score, away_score,
    outcome`.
  - **Summary**: written by `summary()` for at-a-glance viewing in Sheets
    (the dashboard can also compute it live from Bets).
- **Dedup:** treat `(match_date, home_team, away_team, market, selection)` as the
  unique key. On write, skip rows whose key already exists. Re-running a scan is
  therefore safe and only appends genuinely new selections.
- **Efficiency:** batch the per-run bet writes into a single `append_rows` call
  rather than one API call per bet. Sheets rate limit is ~60 writes/min; at our
  volume one batched append per run is plenty.
- **Grading:** `grade_pending` reads pending Bets rows + Results rows, computes
  win/loss/pnl in Python (reuse the existing `_bet_won` logic for 1X2 / OU2.5 /
  BTTS), and updates those Bets rows in place.

### 2. Window-based scan (fixes kickoff timing)

The slate spans afternoon to ~03:00 Amsterdam, so a single daily run misses
early or late games. Change match selection from "today's UTC date" to a time
window:

- Add an option to `fixtures.get_matches` to return upcoming events whose
  `commence_time` is between now and now + `SCAN_WINDOW_HOURS` (default 18) and
  that have not kicked off yet. Keep the existing date filter for manual/CLI use.
- The run computes value bets for those games, skips any already posted (dedup
  from item 1), records + posts only the new ones, and sends the Telegram card
  for the new bets. Run this twice a day (see n8n below) so a 03:00 game is
  posted from the previous evening's run, well before kickoff.
- One odds fetch per run (3 credits). Two runs/day is ~6 credits/day, safe for
  the whole tournament against the ~489 remaining.

### 3. Flask app: run endpoints + dashboard auth

Use the existing Flask app (in `dashboard.py`; rename to `app.py` if cleaner):

- `POST /run/morning` -> runs the windowed scan (item 2). Protected: require
  `RUN_API_KEY` (already in `.env.example`) via an `X-Run-Key` header or
  `?key=`. Return a small JSON summary (counts, bets posted).
- `POST /run/grade` -> runs `grade_pending` + sends the recap. Same auth.
- `GET /` dashboard. Protect with HTTP Basic Auth gated on `DASHBOARD_USER` /
  `DASHBOARD_PASSWORD` (open if unset, for local dev).
- `GET /healthz` -> 200, for n8n/Railway health checks.
- Runs are synchronous inside the request (a few seconds). Set gunicorn
  `--timeout 120`. No background worker, no scheduler in-process.

### 4. Dashboard reads Sheets

With the tracker now Sheets-backed, `dashboard.py` keeps using
`tracker.fetch_bets()` / `summary()` and therefore reads Sheets automatically.
Optionally cache the Sheets read for a few seconds to keep page loads snappy.

### 5. Credentials + production server

- Service-account creds via env: accept `GOOGLE_CREDENTIALS_JSON` (full JSON
  string) and authorize with `gspread.service_account_from_dict(...)`. Keep the
  file path as a local-dev fallback. The deployed service has no key file.
- Add `gunicorn` to `requirements.txt`; drop nothing else needed.
- `Procfile`: `web: gunicorn app:app --workers 2 --timeout 120 --bind 0.0.0.0:$PORT`
  (multiple workers are fine now since there is no in-process scheduler).

### 6. Clean up

Remove SQLite specifics (`DB_PATH`, the `data/*.db` store, the SQLite schema).
Leave the `.gitignore` rules harmless. Remove the old `sheets.py` mirror once the
tracker absorbs it.

## n8n (user sets up, CC documents)

- Two **Schedule** triggers per day (e.g. ~09:00 and ~20:00 Amsterdam) ->
  HTTP Request node POST `https://<service>/run/morning` with header
  `X-Run-Key: <RUN_API_KEY>`.
- One **Schedule** trigger (e.g. ~10:00 Amsterdam) -> POST `/run/grade` to settle
  the previous day's games. Grading needs final scores in the Results tab; the
  user can type scores straight into the sheet (it is now the hub), or a later
  briefing wires football-data.org auto-results.
- Activate the n8n schedule only for the tournament window (June 11 to July 19,
  2026) so no odds credits are spent off-season. This replaces any in-app date
  guard.

## Railway (user actions, CC writes the checklist)

- New project from the GitHub repo `WouterAltepost/betsu`. **No volume.**
- Set the start command via the Procfile.
- Set environment variables (below). Deploy, open the URL (basic-auth prompt).

## Environment variables

| Var | Note |
|---|---|
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | existing secrets |
| `ODDS_API_KEY`, `ANTHROPIC_API_KEY` | existing secrets |
| `GOOGLE_SHEETS_ID` | the tracker sheet id |
| `GOOGLE_CREDENTIALS_JSON` | full service-account JSON, pasted |
| `RUN_API_KEY` | shared secret n8n sends on the run endpoints |
| `DASHBOARD_USER`, `DASHBOARD_PASSWORD` | dashboard login |
| `SCAN_WINDOW_HOURS` | default 18 |
| `PORT` | Railway provides it |

## Acceptance criteria

- No SQLite anywhere; `grep` for `sqlite` returns only removed/irrelevant hits.
- `POST /run/morning` with the right key fetches once, posts only upcoming
  not-yet-sent games, writes them to the Bets tab, and sends the Telegram card.
  A second immediate call posts nothing new (dedup works).
- Typing a final score into the Results tab then `POST /run/grade` settles the
  matching bets (1X2, OU2.5, BTTS) and updates `result` + `pnl_units`.
- Dashboard renders from Sheets and returns 401 without basic-auth creds.
- `GET /healthz` returns 200. App boots with no key file when
  `GOOGLE_CREDENTIALS_JSON` is set.
- Wrong/missing `RUN_API_KEY` on a run endpoint returns 401.

## Out of scope (future briefings)

football-data.org auto-results, `llm_context.py` nudge layer, any Postgres or
caching beyond a small in-memory dashboard cache.
