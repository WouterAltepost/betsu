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
calibration plus positive ROI versus the closing odds. Paper-traded by default;
real money only when the user decides a bet makes sense.

## The ensemble (the "predictor")

One blended probability per match, combining:
- **market** — de-vigged bookmaker odds (the-odds-api). Strongest single signal, and our benchmark.
- **elo** — World Football Elo model, neutral-venue, self-updating after results.
- **poisson** — Dixon-Coles goal model (phase 1; unlocks Over/Under + BTTS).
- **llm** — Claude news/context nudge for injuries, dead rubbers, heat (phase 1; an adjustment, not a base model).

Weights live in `config.py:ENSEMBLE_WEIGHTS` and renormalise over whatever layers
are present, so a missing layer never breaks the blend. Tonight's MVP runs
market + elo; the other two plug in without touching the rest.

## Value betting

`edge = model_prob * decimal_odds - 1`. We suggest selections with edge >= `MIN_EDGE`
(default 5%), capped at `MAX_BETS_PER_DAY`, ranked by edge. Flat 1-unit paper
stake; a quarter-Kelly figure is shown as a real-money sizing guide.

## Layers

**Tools** (`tools/`, deterministic execution):
- `fixtures.py` — fetch today's fixtures + odds, best price per outcome, de-vig to market probs
- `elo.py` — Elo ratings + 1X2 probabilities + result-based updates
- `ensemble.py` — blend predictor probabilities (+ optional LLM nudge)
- `value.py` — value bets from blended probs vs odds, with Kelly guide
- `tracker.py` — Google Sheets store: matches, bets, results, grading, ROI summary
- `poisson.py` — Dixon-Coles goal model (1X2 + Over/Under 2.5 + BTTS)
- `message.py` — format the Telegram bet card and results recap
- `telegram_send.py` — send to the configured chat
- `llm_context.py` — phase 1 (not yet built)

**Workflows** (`workflows/`, plain-language SOPs): `daily_run.md`

**Agent** (`run_daily.py`): orchestrates the scan and grade runs — the windowed
scan posts only genuinely-new bets (dedup), so it's safe to run repeatedly.

**Service** (`app.py`): stateless Flask app (gunicorn on Railway). Serves the
performance dashboard and the protected `POST /run/morning` / `POST /run/grade`
endpoints that n8n calls on a schedule. See `docs/deploy_runbook.md`.

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
- Elo seeds: `data/elo_seed.json` — APPROXIMATE starting values, refresh from
  eloratings.net before the tournament. The model refines them as results land.
- Store: Google Sheets (Bets / Results / Matches / Summary tabs) — the single
  source of truth; see `docs/google_sheets_setup.md`.
- Results: typed into the Sheets **Results** tab (or `tracker.record_result`);
  football-data.org auto-results is a later add.

## Status / roadmap

- **MVP (done):** market + Elo + Poisson ensemble; 1X2 / O-U 2.5 / BTTS value bets; Telegram card; Flask dashboard. Built and tested.
- **Deploy (done):** stateless Flask service on Railway, Google Sheets store, n8n-scheduled run endpoints (windowed scan + dedup). See `docs/deploy_briefing.md` and `docs/deploy_runbook.md`.
- **Phase 1 (group stage):** add the LLM context nudge; tune ensemble weights on real results.
- **Phase 2 (knockouts):** keep what calibrates well, drop dead weight; optional football-data.org auto-results.

## Notes

- World Cup matches are neutral-venue; only host nations (USA, Canada, Mexico)
  get a home-advantage bump when listed as home.
- Group stage has 4+ games most days — lots of volume to calibrate on fast.
- No public model reliably beats the closing line. Judge betsu on calibration
  and ROI over the tournament, not on any single day.
