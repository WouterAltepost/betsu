"""
config.py — central configuration for the betsu World Cup predictor.

Everything tunable lives here so the rest of the code stays clean.
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
TMP_DIR = os.path.join(BASE_DIR, ".tmp")
DB_PATH = os.path.join(DATA_DIR, "betsu.db")

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
MAX_BETS_PER_DAY = 8     # cap the daily message to the best N
FLAT_STAKE_UNITS = 1.0   # paper staking: 1 unit per suggested bet
KELLY_FRACTION = 0.25    # shown as a guide for real-money sizing (quarter Kelly)

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

# --- LLM --------------------------------------------------------------------
LLM_MODEL = "claude-sonnet-4-6"

# --- Telegram ---------------------------------------------------------------
TELEGRAM_API_BASE = "https://api.telegram.org"
