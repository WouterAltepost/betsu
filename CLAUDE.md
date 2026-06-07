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
- `tracker.py` — SQLite store: matches, bets, results, grading, ROI summary
- `message.py` — format the Telegram bet card and results recap
- `telegram_send.py` — send to the configured chat
- `poisson.py`, `llm_context.py` — phase 1 (not yet built)

**Workflows** (`workflows/`, plain-language SOPs): `daily_run.md`

**Agent** (`run_daily.py`): orchestrates the morning and grade runs.

## Running it

```bash
pip install -r requirements.txt
python tools/tracker.py init           # one-time: create the SQLite store
python run_daily.py --dry-run          # build today's card, print it, send nothing
python run_daily.py                     # build, store, and send to Telegram
python run_daily.py --grade             # settle pending bets, send results recap
python tools/elo.py "Brazil" "Spain"   # sanity-check the Elo model
python tools/fixtures.py --sports       # list odds-api soccer sport keys
```

## Configuration

All secrets in `.env` (gitignored): `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`,
`ODDS_API_KEY`, `ANTHROPIC_API_KEY`. All tunables in `config.py`.

## Data sources

- Fixtures + odds: the-odds-api.com (free tier). Sport key `soccer_fifa_world_cup`.
- Elo seeds: `data/elo_seed.json` — APPROXIMATE starting values, refresh from
  eloratings.net before the tournament. The model refines them as results land.
- Results: manual entry or football-data.org (free tier) for grading.

## Status / roadmap

- **MVP (now):** market + Elo ensemble, 1X2 value bets, Telegram card, SQLite tracking. Built and tested.
- **Phase 1 (group stage):** add Poisson (Over/Under, BTTS) and the LLM context layer; tune weights on real results.
- **Phase 2 (knockouts):** keep what calibrates well, drop dead weight. Optional Flask/Railway deploy + scheduler for hands-off daily runs.

## Notes

- World Cup matches are neutral-venue; only host nations (USA, Canada, Mexico)
  get a home-advantage bump when listed as home.
- Group stage has 4+ games most days — lots of volume to calibrate on fast.
- No public model reliably beats the closing line. Judge betsu on calibration
  and ROI over the tournament, not on any single day.
