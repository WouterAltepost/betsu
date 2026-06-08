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
import re
import sys
import unicodedata

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


# Fuzzy-match floor for the seed lookup. Deliberately high: a MIS-match here is
# worse than a miss — it hands a team the WRONG Elo rating (silently corrupting
# the Poisson lambdas, the blend, and any bet off it), whereas a miss is caught
# by run_daily's is_seeded guard, which drops the Elo layer. token_sort_ratio
# scores some distinct 2026 qualifiers dangerously high (Australia vs Austria =
# 87.5; Iran/Iraq, Slovakia/Slovenia are the same class), so 85 would let a
# non-exact feed spelling of one resolve to the other. Accent/punctuation
# variants and known feed spellings are handled by normalisation + ALIASES
# below, so genuine variants resolve BEFORE fuzzy is reached; 90 then keeps the
# confusable country pairs apart. Mirrors tools/results_fetch.py's _THRESHOLD.
MATCH_THRESHOLD = 90

# When the top two fuzzy candidates are within this many points of each other,
# the match is ambiguous (two plausible seeds) — fall back to default and let
# the is_seeded guard drop the layer rather than guess wrong.
AMBIGUITY_MARGIN = 5

# Known feed spellings -> canonical seed key. The-odds-api and similar feeds
# spell some teams differently enough that token-sort fuzzy matching misses
# them entirely (e.g. "USA" vs "United States", "Korea Republic" vs
# "South Korea"). These are resolved before the fuzzy fallback so a host
# nation or qualifier never silently drops to the default rating — and, for the
# confusable pairs, so a known variant resolves explicitly instead of riding on
# a borderline fuzzy score. Keys are matched after normalisation (see
# _normalize), so accents/punctuation/case in the key don't matter.
# tools/results_fetch.py imports this map (as elo.ALIASES) for its own
# reconciliation, so the two stay in sync; keep keys lowercase for that caller.
ALIASES = {
    # United States (host nation)
    "usa": "United States",
    "united states of america": "United States",
    # Côte d'Ivoire
    "cote d'ivoire": "Ivory Coast",
    "côte d'ivoire": "Ivory Coast",
    # Cape Verde
    "cabo verde": "Cape Verde",
    "cape verde islands": "Cape Verde",
    # Czechia
    "czech republic": "Czechia",
    # South Korea
    "korea republic": "South Korea",
    "republic of korea": "South Korea",
    "korea, republic of": "South Korea",
    # Türkiye
    "turkiye": "Turkey",
    "türkiye": "Turkey",
    # Iran
    "ir iran": "Iran",
    "iran islamic republic": "Iran",
    "islamic republic of iran": "Iran",
    # Bosnia and Herzegovina
    "bosnia & herzegovina": "Bosnia and Herzegovina",
    "bosnia-herzegovina": "Bosnia and Herzegovina",
    "bosnia and herzegovina": "Bosnia and Herzegovina",
    # DR Congo
    "dr congo": "DR Congo",
    "congo dr": "DR Congo",
    "democratic republic of the congo": "DR Congo",
    "congo democratic republic": "DR Congo",
    # Republic of Ireland
    "ireland": "Republic of Ireland",
}


def _strip_accents(s):
    """Drop combining accents so 'Curaçao' == 'Curacao', 'Türkiye' == 'Turkiye'."""
    return "".join(c for c in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(c))


def _normalize(name):
    """Canonical comparison key: lowercase, accent-folded, punctuation and
    repeated whitespace collapsed to single spaces. So "Côte d'Ivoire",
    "Cote d'Ivoire" and "cote d ivoire" all compare equal. Mirrors the
    canonicalisation in tools/results_fetch.py so the two can't drift."""
    s = _strip_accents((name or "").strip().lower())
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return s.strip()


# Alias map keyed by normalized form, so accents/punctuation/case in the raw
# alias keys above are irrelevant at lookup time.
_ALIAS_NORM = {_normalize(k): v for k, v in ALIASES.items()}


def lookup_rating(name, ratings):
    """
    Resolve a team name to (rating, matched_key). Resolution order, tightest
    first: exact key, then normalized alias, then normalized exact key, then a
    fuzzy fallback gated by MATCH_THRESHOLD and an ambiguity check. matched_key
    is None when no confident seed was found and we fell back to DEFAULT_RATING
    — callers (is_seeded) use that to flag the match and drop the Elo layer.
    """
    # 1. Exact key — unchanged fast path for canonical seed names.
    if name in ratings:
        return ratings[name], name

    q = _normalize(name)
    if not q:
        return DEFAULT_RATING, None

    # 2. Known feed spelling -> canonical seed key, by normalized form.
    alias = _ALIAS_NORM.get(q)
    if alias and alias in ratings:
        return ratings[alias], alias

    # 3. Normalized exact match against the seed keys (absorbs accent- and
    #    punctuation-only differences, e.g. "Curaçao" -> "Curacao").
    norm_to_key = {_normalize(k): k for k in ratings}
    if q in norm_to_key:
        key = norm_to_key[q]
        return ratings[key], key

    # 4. Fuzzy fallback over normalized keys, with an ambiguity guard: only
    #    accept a clear winner that also clears the confusable-pair threshold.
    candidates = process.extract(q, list(norm_to_key.keys()),
                                 scorer=fuzz.token_sort_ratio, limit=2)
    if candidates and candidates[0][1] >= MATCH_THRESHOLD:
        if len(candidates) > 1 and candidates[0][1] - candidates[1][1] < AMBIGUITY_MARGIN:
            return DEFAULT_RATING, None  # two seeds too close — don't guess
        key = norm_to_key[candidates[0][0]]
        return ratings[key], key
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
