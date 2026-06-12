"""
config.py — central configuration for the betsu World Cup predictor.

Everything tunable lives here so the rest of the code stays clean.
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")   # holds data/elo_seed.json
TMP_DIR = os.path.join(BASE_DIR, ".tmp")

# --- Ensemble weights -------------------------------------------------------
# Probabilities from each predictor are blended with these weights.
# Weights are renormalised over whichever predictors are available for a match,
# so a missing layer (e.g. no odds yet) does not break the blend.
ENSEMBLE_WEIGHTS = {
    "market": 0.40,   # de-vigged bookmaker odds — strongest single signal
    "elo":    0.30,   # World Football Elo model
    "poisson": 0.20,  # Dixon-Coles goal model (phase 1)
    "xg":     0.05,   # Expected Goals layer (phase 1, optional)
    # "llm" acts as an adjustment layer, not a base weight (see ensemble.py)
}

# --- Value betting ----------------------------------------------------------
# A bet is "value" when our blended probability implies a fair price below the
# bookmaker's offered price. Edge = model_prob * decimal_odds - 1.
MIN_EDGE = 0.05          # only suggest bets with >= 5% expected value
MAX_BETS_PER_DAY = 8     # cap each run's message to the best N new bets
# Two tracks (see docs/dashboard_redesign_briefing.md):
#   model/paper track — flat 1-unit stakes, the benchmark betsu is judged on
#                       (calibration + ROI vs the line over ALL suggestions).
#   real-money track  — the € stakes the user actually places, tracked on the
#                       dashboard; the morning card shows a € ¼-Kelly guide.
FLAT_STAKE_UNITS = 1.0   # model track: 1 unit per suggested bet (paper benchmark)
KELLY_FRACTION = 0.25    # quarter Kelly — fraction of bankroll for the sizing guide
# Bankroll behind the € quarter-Kelly stake guide on the morning card and the
# dashboard's suggested stake. A guide only — real stake is the user's choice.
BANKROLL_EUR = int(os.environ.get("BANKROLL_EUR", "1000"))

# --- Scan window ------------------------------------------------------------
# The scheduled run scans fixtures kicking off within the next SCAN_WINDOW_HOURS
# that have not started yet (a slate runs afternoon→~03:00 Amsterdam, so a single
# daily run would miss the early or late games). Two runs/day cover it, and dedup
# means a late game is posted from the prior evening's run, before kickoff.
SCAN_WINDOW_HOURS = int(os.environ.get("SCAN_WINDOW_HOURS", "18"))

# --- Elo model --------------------------------------------------------------
ELO_HOME_ADVANTAGE = 65   # rating points added to the home/designated team
ELO_K = 20                # update speed after each result
# World Cup is at neutral venues; home advantage only applies to the three
# host nations (USA, Canada, Mexico) when playing at home.
HOST_NATIONS = {"United States", "Canada", "Mexico"}

# --- Poisson model (Dixon-Coles) --------------------------------------------
# Goal expectations (lambdas) are derived from the Elo gap: the rating
# difference maps to an expected goal supremacy around a baseline total, then
# the Dixon-Coles correction adjusts the low-scoring scorelines. This unlocks
# 1X2 (blended), Over/Under 2.5, and BTTS without any new data source.
POISSON_BASE_TOTAL_GOALS = 2.6   # avg goals/game baseline (sum of both lambdas)
POISSON_SUP_DIVISOR = 250.0      # Elo points per 1.0 of goal supremacy
POISSON_GOAL_FLOOR = 0.2         # min lambda, so blowout gaps stay sane
POISSON_DC_RHO = -0.13           # Dixon-Coles low-score dependence (negative)
POISSON_MAX_GOALS = 10           # scoreline grid size (0..10 each side)
OU_LINE = 2.5                    # the Over/Under line we model + price

# --- Odds API ---------------------------------------------------------------
ODDS_API_BASE = "https://api.the-odds-api.com/v4"
ODDS_REGION = "eu"            # eu/uk/us — eu gives decimal odds & good coverage
ODDS_MARKETS = "h2h,totals"   # 1X2 + Over/Under 2.5.
# the-odds-api's bulk /odds endpoint only serves FEATURED markets
# (h2h, spreads, totals). "btts" is an ADDITIONAL market available only on the
# per-event /events/{id}/odds endpoint, so requesting it here 422s the whole
# call. Cost: the-odds-api bills 1 credit per market per region = 2 credits/call.
ODDS_SPORT_WORLDCUP = "soccer_fifa_world_cup"
# Pre-tournament we also test on friendlies / other live soccer.

# --- BTTS (both teams to score) via the per-event endpoint ------------------
# "btts" is an ADDITIONAL market, so it can't ride the bulk /odds call — it only
# exists on /events/{id}/odds, billed 1 credit per market per region PER EVENT.
# With 104 WC matches and 2 scans/day, fetching per scan would burn the budget,
# so per-event BTTS is cached per event id and gated. Design: ~1 fetch/match.
BTTS_ENABLED = os.environ.get("BTTS_ENABLED", "1").strip() in ("1", "true", "True")
# Reuse a cached BTTS price per event for this many hours (a match sits in the
# scan window for ~2 scans, so a 12h TTL means one fetch per event, not per scan).
BTTS_CACHE_HOURS = int(os.environ.get("BTTS_CACHE_HOURS", "12"))

# --- Google Sheets store (primary) ------------------------------------------
# Google Sheets is betsu's single source of truth — there is no local DB. The
# tracker reads/writes these tabs. Auth is a Google Cloud *service account*:
#   deploy — GOOGLE_CREDENTIALS_JSON  (full key JSON pasted into an env var)
#   local  — a credentials.json key file (GOOGLE_CREDENTIALS_PATH, default below)
# GOOGLE_SHEETS_ID selects the spreadsheet. See docs/google_sheets_setup.md.
SHEETS_CREDENTIALS_DEFAULT = os.path.join(BASE_DIR, "credentials.json")
SHEETS_TAB_BETS = "Bets"
SHEETS_TAB_RESULTS = "Results"
SHEETS_TAB_MATCHES = "Matches"
SHEETS_TAB_SUMMARY = "Summary"
SHEETS_TAB_CONTEXT = "Context"   # LLM nudge cache (see tools/llm_context.py)
SHEETS_TAB_BTTS = "BttsOdds"     # per-event BTTS price cache (see fixtures.py)
# Read-through cache TTL (seconds): keeps dashboard page loads snappy and stays
# under the Sheets read quota. Writes invalidate it immediately, so a run always
# reads its own fresh writes.
SHEETS_CACHE_TTL = int(os.environ.get("SHEETS_CACHE_TTL", "5"))

# --- LLM context nudge ------------------------------------------------------
# The fourth ensemble layer: a Claude-driven, web-search-grounded ADJUSTMENT to
# the blended 1X2 probabilities for real-world context the stats can't see
# (key injuries/suspensions, dead rubbers, extreme heat, rest/travel). It is a
# nudge, not a base model, and is off unless LLM_ENABLED=1 — runs without it are
# byte-for-byte unchanged. See tools/llm_context.py.
LLM_MODEL = "claude-sonnet-4-6"
LLM_ENABLED = os.environ.get("LLM_ENABLED", "0").strip() in ("1", "true", "True")
# Each nudge component is clamped in code to [-MAX_LLM_NUDGE, +MAX_LLM_NUDGE];
# the model's own magnitudes are never trusted.
MAX_LLM_NUDGE = 0.08
# Reuse a cached adjustment per (match_date, home, away) for this many hours so
# the second daily run is served from cache (context changes slowly).
LLM_CACHE_HOURS = 12
# Anthropic server-side web search tool. Grounds every acted-on factor in a
# recent, cited source; bump the version here if the API rev changes.
LLM_WEB_SEARCH_TOOL = "web_search_20260209"
LLM_MAX_WEB_SEARCHES = 5      # cap searches per fixture lookup (cost control)
LLM_TIMEOUT_SECONDS = 90      # hard ceiling on a single get_adjustment call

# --- football-data.org auto-results -----------------------------------------
# Before each grade run, finished World Cup scores are pulled from
# football-data.org and written to the Results tab (under our store's team
# names), so grading settles without anyone hand-typing scores. Manual entry
# stays the fallback and the override — see tools/results_fetch.py.
FOOTBALL_DATA_BASE = "https://api.football-data.org/v4"
FOOTBALL_DATA_COMPETITION = "WC"   # football-data's 2026 World Cup code
# Off only with AUTO_RESULTS_ENABLED=0 or no FOOTBALL_DATA_API_KEY: then grade
# reads whatever is already in the Results tab, exactly as before.
AUTO_RESULTS_ENABLED = os.environ.get("AUTO_RESULTS_ENABLED", "1").strip() in ("1", "true", "True")
# How many days back to ask football-data for finished fixtures each grade run.
RESULTS_LOOKBACK_DAYS = int(os.environ.get("RESULTS_LOOKBACK_DAYS", "3"))

# --- Telegram ---------------------------------------------------------------
TELEGRAM_API_BASE = "https://api.telegram.org"

# --- xG (Expected Goals) layer -----------------------------------------------
# Expected Goals measures shot quality and is more stable than raw goals. Real
# WC xG is pulled from FBref (Opta-sourced) via soccerdata, turned into 1X2 by
# reusing the Poisson grid (poisson.markets_from_lambdas), with FBref team names
# reconciled through the Elo resolver. The layer is fully fail-safe — any error,
# or too few played matches, yields None and the blend renormalises. Off by
# default; enable on Railway once the WC slate has enough played matches for xG.
XG_ENABLED = os.environ.get("XG_ENABLED", "0").strip() in ("1", "true", "True")
XG_SEASON = int(os.environ.get("XG_SEASON", "2026"))           # FBref season id for INT-World Cup
XG_MATCHES_BACK = int(os.environ.get("XG_MATCHES_BACK", "5"))  # average over each team's last N matches
XG_MIN_MATCHES = int(os.environ.get("XG_MIN_MATCHES", "2"))    # need >= this many played matches of xG
XG_CACHE_HOURS = int(os.environ.get("XG_CACHE_HOURS", "24"))   # rebuild the in-process xG table daily

# --- Variance modeling for extreme scores -----------------------------------
# Extends Dixon-Coles to better predict high-scoring games (4+, 5-0, etc.)
# Increases tail probability weight when one team is much stronger (large Elo gap)
VARIANCE_SCALING_ENABLED = os.environ.get("VARIANCE_SCALING_ENABLED", "0").strip() in ("1", "true", "True")
VARIANCE_ELO_THRESHOLD = int(os.environ.get("VARIANCE_ELO_THRESHOLD", "20"))  # apply if |elo_diff| > this
VARIANCE_SCALE_FACTOR = float(os.environ.get("VARIANCE_SCALE_FACTOR", "0.15"))  # multiplier for variance

# --- Sharp market line (Pinnacle) -------------------------------------------
# When enabled, the market layer of the blend is estimated from a single sharp
# book's de-vigged 1X2 (Pinnacle) instead of best-price-across-books — a sharp
# book is the textbook market estimate. The actual BET price stays best-price-
# across-books. Pinnacle already rides the eu-region the-odds-api payload we
# fetch, and billing is per market per region (independent of bookmaker count),
# so reading its line costs ZERO extra credits. Single switch, off by default.
SHARP_SOFT_MONITORING_ENABLED = os.environ.get("SHARP_SOFT_MONITORING_ENABLED", "0").strip() in ("1", "true", "True")
# the-odds-api's bookmaker key for the sharp book (confirmed present in the eu
# payload). Read out of the bulk /odds response — no separate request.
SHARP_BOOKMAKER_KEY = "pinnacle"
