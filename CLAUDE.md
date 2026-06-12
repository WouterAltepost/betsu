# betsu — World Cup 2026 Bet Predictor

You're working inside the **WAT framework** (Workflows, Agents, Tools): probabilistic
reasoning is separated from deterministic execution so the system stays reliable.

## What this is

A predictor for the 2026 FIFA World Cup (June 11 to July 19). Each morning it
scans the day's fixtures, blends several models into one probability per match,
finds **value bets** against bookmaker odds, sends a bet card to Telegram, and
logs everything for calibration and ROI tracking.

This is the successor to an earlier project that aggregated tipster sites. The
flip: instead of tracking other people's bets, we build our own ensemble
predictor and grade it honestly.

**Goal:** not raw hit-rate (favorites win a lot and still lose money), but
calibration plus positive ROI versus the closing odds. Two tracks, kept distinct:
the **model track** (flat 1-unit paper stakes over *every* suggestion) is the
benchmark betsu is judged on; separately, the user records the bets they
**actually placed**, the € stake on each, and settles them, and that **real-money
€ P&L** is the dashboard headline. The model/units track is internal; user-facing
surfaces (dashboard, Telegram card) speak in euros on placed bets.

## The ensemble (the "predictor")

One blended probability per match, combining:
- **market** — de-vigged bookmaker odds (the-odds-api). Strongest single signal, and our benchmark. Optionally estimated from a single sharp book's line (Pinnacle, read free from the same payload) when `SHARP_SOFT_MONITORING_ENABLED` — the *bet* price stays best-price-across-books.
- **elo** — World Football Elo model, neutral-venue, self-updating after results.
- **poisson** — Dixon-Coles goal model (phase 1; unlocks Over/Under + BTTS).
- **xg** — FBref Expected Goals (Opta), turned into 1X2 via the Poisson grid (phase 1; `XG_ENABLED`, off until WC xG is published and validated).
- **llm** — Claude news/context nudge for injuries, dead rubbers, heat (phase 1; an adjustment, not a base model).

Weights live in `config.py:ENSEMBLE_WEIGHTS` and renormalise over whatever layers
are present, so a missing layer never breaks the blend. Tonight's MVP runs
market + elo; the other two plug in without touching the rest.

## Value betting

`edge = model_prob * decimal_odds - 1`. We suggest selections with edge >= `MIN_EDGE`
(default 5%), capped at `MAX_BETS_PER_DAY`, ranked by edge. The model track stakes
a flat 1 unit per suggestion (the paper benchmark); the user-facing card and
dashboard show a **€ quarter-Kelly guide** (off `BANKROLL_EUR`). The user then
records which bets they placed and the real € stake — see the dashboard + the
`Bets` tab's `placed` / `staked_real` / `manual_result` / `pnl_eur` columns.

## Layers

**Tools** (`tools/`, deterministic execution):
- `fixtures.py` — fetch today's fixtures + odds, best price per outcome, de-vig to market probs; plus `fetch_event_btts` for the per-event BTTS price (an additional market, fetched + cached per event), and a `sharp_market_probs` field — a single sharp book's (Pinnacle) de-vig read free from the same payload
- `elo.py` — Elo ratings + 1X2 probabilities + result-based updates
- `ensemble.py` — blend predictor probabilities (+ optional LLM nudge)
- `value.py` — value bets from blended probs vs odds, with Kelly guide
- `tracker.py` — Google Sheets store: matches, bets, results, grading, ROI summary.
  Holds both tracks: the units/paper benchmark and the user's real-money fields
  (`placed` / `staked_real` / `manual_result` / `pnl_eur`). `update_bet_user_fields`
  writes those; `effective_result` (manual override > auto grade) is read everywhere;
  `summary()` returns a `real` € block plus the units keys
- `poisson.py` — Dixon-Coles goal model (1X2 + Over/Under 2.5 + BTTS); `markets_from_lambdas` turns explicit expected goals into the same market dict (shared with the xG layer)
- `xg.py` — Expected Goals layer: pulls WC team xG from FBref via `soccerdata`, reconciles names through the Elo resolver, and converts xG→1X2 with the Poisson grid. Fail-safe and off by default (`XG_ENABLED`). NB: soccerdata's FBref reader drives a headless browser (Cloudflare), so enabling it on a server needs Chrome available
- `results_fetch.py` — pull finished WC scores from football-data.org, reconcile
  team names to the store, write to Results so grading settles hands-off
- `message.py` — format the Telegram bet card and results recap
- `telegram_send.py` — send to the configured chat
- `llm_context.py` — phase 1 (not yet built)

**Workflows** (`workflows/`, plain-language SOPs): `daily_run.md`

**Agent** (`run_daily.py`): orchestrates the scan and grade runs — the windowed
scan posts only genuinely-new bets (dedup), so it's safe to run repeatedly.

**Service** (`app.py`): stateless Flask app (gunicorn on Railway). Serves the
React performance dashboard (vendored static files in `static/dashboard/`, libs
vendored locally — no runtime CDN) plus a small dashboard-auth-gated JSON API
(`GET /api/bets`, `GET /api/summary`, `POST /api/bets/update`) that reads/writes
the placed-bet fields back to Sheets, and the protected `POST /run/morning` /
`POST /run/grade` endpoints that n8n calls on a schedule. The dashboard/API are
isolated and fail-safe, so they never affect the run endpoints. It also serves an
installable mobile PWA at `/m` (vendored static files in `static/mobile/`, same
auth, same `/api/*` write contract — Sheets stays the single source of truth; no
service worker by decision). See `docs/deploy_runbook.md`,
`docs/dashboard_redesign_briefing.md`, and `docs/mobile_pwa_briefing.md` /
`docs/mobile_runbook.md`.

## Running it

```bash
pip install -r requirements.txt
python tools/tracker.py status         # check the Google Sheets store is configured
python tools/tracker.py init           # one-time: ensure the sheet tabs exist
python run_daily.py --window --dry-run # build the card for the next SCAN_WINDOW_HOURS, send nothing
python run_daily.py --window           # scan, store new bets, send to Telegram
python run_daily.py --grade            # settle pending bets, send results recap
python app.py                          # run the dashboard + endpoints locally (http://127.0.0.1:5000)
python tools/elo.py "Brazil" "Spain"   # sanity-check the Elo model
python tools/fixtures.py --sports      # list odds-api soccer sport keys
python tools/results_fetch.py          # list finished WC scores football-data has (last 3d)
python tools/results_fetch.py --sync   # reconcile + write finished scores to Results
```

## Configuration

All secrets in `.env` (gitignored): `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`,
`ODDS_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_SHEETS_ID`, and the Google
service-account creds (`GOOGLE_CREDENTIALS_PATH` locally / `GOOGLE_CREDENTIALS_JSON`
on Railway). The Flask service also reads `RUN_API_KEY` and optional
`DASHBOARD_USER` / `DASHBOARD_PASSWORD`. All tunables in `config.py`; see
`.env.example` and `docs/google_sheets_setup.md`.

## Data sources

- Fixtures + odds: the-odds-api.com (free tier). Sport key `soccer_fifa_world_cup`.
  The `eu` payload includes Pinnacle, so the optional sharp market layer costs no extra credits.
- xG: FBref (Opta-sourced) via the `soccerdata` library, league `INT-World Cup`.
  Off by default and only meaningful once WC matches are played; national-team xG is published late.
- Elo seeds: `data/elo_seed.json` — APPROXIMATE starting values, refresh from
  eloratings.net before the tournament. The model refines them as results land.
- Store: Google Sheets (Bets / Results / Matches / Summary tabs) — the single
  source of truth; see `docs/google_sheets_setup.md`.
- Results: auto-pulled each grade run from football-data.org (`results_fetch.py`,
  needs `FOOTBALL_DATA_API_KEY`), reconciled to our team names and written to the
  Sheets **Results** tab. Manual entry (typing scores, or `tracker.record_result`)
  stays the fallback and the override — a hand-typed score is never overwritten.

## Status / roadmap

- **MVP (done):** market + Elo + Poisson ensemble; 1X2 / O-U 2.5 / BTTS value bets; Telegram card; Flask dashboard. Built and tested.
- **Deploy (done):** stateless Flask service on Railway, Google Sheets store, n8n-scheduled run endpoints (windowed scan + dedup). See `docs/deploy_briefing.md` and `docs/deploy_runbook.md`.
- **Phase 1 (group stage):** add the LLM context nudge; tune ensemble weights on real results.
- **Phase 1 (done):** football-data.org auto-results — hands-off grading, fuzzy name reconciliation, manual entry preserved as override.
- **Phase 2 (knockouts):** keep what calibrates well, drop dead weight.

## Notes

- World Cup matches are neutral-venue; only host nations (USA, Canada, Mexico)
  get a home-advantage bump when listed as home.
- Group stage has 4+ games most days — lots of volume to calibrate on fast.
- No public model reliably beats the closing line. Judge betsu on calibration
  and ROI over the tournament, not on any single day.
