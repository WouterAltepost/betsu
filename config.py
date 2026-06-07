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
    "market": 0.50,   # de-vigged bookmaker odds — strongest single signal
    "elo":    0.30,   # World Football Elo model
    "poisson": 0.20,  # Dixon-Coles goal model (phase 1)
    # "llm" acts as an adjustment layer, not a base weight (see ensemble.py)
}

# --- Value betting ----------------------------------------------------------
# A bet is "value" when our blended probability implies a fair price below the
# bookmaker's offered price. Edge = model_prob * decimal_odds - 1.
MIN_EDGE = 0.05          # only suggest bets with >= 5% expected value
MAX_BETS_PER_DAY = 8     # cap each run's message to the best N new bets
FLAT_STAKE_UNITS = 1.0   # paper staking: 1 unit per suggested bet
KELLY_FRACTION = 0.25    # shown as a guide for real-money sizing (quarter Kelly)

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
ODDS_MARKETS = "h2h,totals,btts"   # 1X2 + Over/Under + both-teams-to-score.
# Cost note: the-odds-api bills 1 credit per market per region, so this is
# 3 credits/call (one call/day). totals/btts coverage varies by book; the
# fetch degrades gracefully to whatever markets a match actually offers.
ODDS_SPORT_WORLDCUP = "soccer_fifa_world_cup"
# Pre-tournament we also test on friendlies / other live soccer.

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

# --- Telegram ---------------------------------------------------------------
TELEGRAM_API_BASE = "https://api.telegram.org"
