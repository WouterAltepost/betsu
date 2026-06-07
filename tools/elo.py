"""
elo.py — Elo predictor for international football.

Converts a rating difference into 1X2 probabilities. The draw is modelled
explicitly (Elo natively gives only win/not-win), using a closed-form split
that widens the draw band when teams are evenly matched.

Functions:
    load_ratings()                  -> dict[str, float]
    get_rating(name, ratings)       -> float  (fuzzy lookup, falls back to default)
    predict(home, away, ratings, neutral=True) -> {"1":p, "X":p, "2":p}
    update(...)                     -> new ratings after a result (for self-learning)

CLI:
    python tools/elo.py "Argentina" "Mexico"            # neutral venue
    python tools/elo.py "United States" "Wales" --home  # host nation at home
"""

import json
import os
import sys

from rapidfuzz import fuzz, process

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATA_DIR, ELO_HOME_ADVANTAGE, ELO_K, HOST_NATIONS

SEED_PATH = os.path.join(DATA_DIR, "elo_seed.json")
DEFAULT_RATING = 1700.0

# How much of the "not-draw" probability mass to carve out as draw, scaled by
# how evenly matched the teams are. Calibrated to ~26% draw for equal teams,
# which matches historical international football base rates.
DRAW_BASE = 0.28


def load_ratings(path=SEED_PATH):
    with open(path) as f:
        raw = json.load(f)
    return {k: float(v) for k, v in raw.items() if not k.startswith("_")}


MATCH_THRESHOLD = 85

# Known feed spellings -> canonical seed key. The-odds-api and similar feeds
# spell some teams differently enough that token-sort fuzzy matching misses
# them entirely (e.g. "USA" vs "United States", "Korea Republic" vs
# "South Korea"). These are resolved before the fuzzy fallback so a host
# nation or qualifier never silently drops to the default rating.
ALIASES = {
    "usa": "United States",
    "united states of america": "United States",
    "cote d'ivoire": "Ivory Coast",
    "côte d'ivoire": "Ivory Coast",
    "cabo verde": "Cape Verde",
    "czech republic": "Czechia",
    "korea republic": "South Korea",
    "republic of korea": "South Korea",
    "turkiye": "Turkey",
    "türkiye": "Turkey",
    "ir iran": "Iran",
    "iran islamic republic": "Iran",
    "bosnia & herzegovina": "Bosnia and Herzegovina",
    "dr congo": "DR Congo",
    "congo dr": "DR Congo",
    "democratic republic of the congo": "DR Congo",
}


def lookup_rating(name, ratings):
    """
    Resolve a team name to (rating, matched_key) via exact match, then a known
    alias, then fuzzy match. matched_key is None when no seed was found and we
    fell back to DEFAULT_RATING — callers use that to flag the match.
    """
    if name in ratings:
        return ratings[name], name
    alias = ALIASES.get(name.strip().lower())
    if alias and alias in ratings:
        return ratings[alias], alias
    match = process.extractOne(name, ratings.keys(), scorer=fuzz.token_sort_ratio)
    if match and match[1] >= MATCH_THRESHOLD:
        return ratings[match[0]], match[0]
    return DEFAULT_RATING, None


def get_rating(name, ratings):
    """Fuzzy-match a team name to the ratings table; default if no good match."""
    return lookup_rating(name, ratings)[0]


def is_seeded(name, ratings):
    """True if `name` resolves to a real seed (not the default fallback).

    The Elo layer carries 30% weight, so an unseeded team sitting at the
    default 1700 skews the blend toward longshots and fabricates value edges.
    The orchestrator uses this to drop the Elo layer for such matches.
    """
    return lookup_rating(name, ratings)[1] is not None


def _expected_win(diff):
    """Standard Elo expected score from a rating difference."""
    return 1.0 / (1.0 + 10 ** (-diff / 400.0))


def predict(home, away, ratings, neutral=True):
    """
    Return {"1", "X", "2"} probabilities.
    `home` is the first-listed team. If neutral, no home advantage is applied
    unless the first team is a host nation playing at home (caller decides).
    """
    rh = get_rating(home, ratings)
    ra = get_rating(away, ratings)

    adv = 0 if neutral else ELO_HOME_ADVANTAGE
    diff = (rh + adv) - ra

    # Probability the first team is "better" on the day (win-or-share).
    e_home = _expected_win(diff)

    # Carve out a draw band that shrinks as the mismatch grows.
    # closeness in [0,1]: 1 when teams are equal, ->0 as the gap widens.
    closeness = 1.0 / (1.0 + (abs(diff) / 400.0))
    p_draw = DRAW_BASE * closeness

    remaining = 1.0 - p_draw
    p_home = remaining * e_home
    p_away = remaining * (1.0 - e_home)

    return {"1": round(p_home, 4), "X": round(p_draw, 4), "2": round(p_away, 4)}


def update(rating_home, rating_away, outcome, neutral=True, k=ELO_K):
    """
    Return (new_home, new_away) after a result so the model self-learns.
    outcome: "1" home win, "X" draw, "2" away win.
    """
    adv = 0 if neutral else ELO_HOME_ADVANTAGE
    e_home = _expected_win((rating_home + adv) - rating_away)
    score_home = {"1": 1.0, "X": 0.5, "2": 0.0}[outcome]
    delta = k * (score_home - e_home)
    return rating_home + delta, rating_away - delta


def is_host_home(team, venue_country):
    return team in HOST_NATIONS and team == venue_country


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    neutral = "--home" not in sys.argv
    ratings = load_ratings()
    if len(args) >= 2:
        home, away = args[0], args[1]
        probs = predict(home, away, ratings, neutral=neutral)
        print(f"{home} (Elo {get_rating(home, ratings):.0f}) vs "
              f"{away} (Elo {get_rating(away, ratings):.0f})  neutral={neutral}")
        print(f"  Home 1: {probs['1']*100:5.1f}%")
        print(f"  Draw X: {probs['X']*100:5.1f}%")
        print(f"  Away 2: {probs['2']*100:5.1f}%")
    else:
        print("usage: python tools/elo.py <home> <away> [--home]")
