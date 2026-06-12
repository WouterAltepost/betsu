"""
value.py — turn blended probabilities + bookmaker odds into value bets.

A bet is value when our probability beats the odds-implied probability:
    edge = model_prob * decimal_odds - 1
We suggest selections with edge >= MIN_EDGE, capped at MAX_BETS_PER_DAY,
sorted by edge. A quarter-Kelly fraction is included as a real-money guide.

    find_value_bets(match_date, home, away, model_probs, odds_1x2) -> [bet, ...]
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MIN_EDGE, FLAT_STAKE_UNITS, KELLY_FRACTION

OUTCOMES = ("1", "X", "2")
LABEL = {"1": "Home", "X": "Draw", "2": "Away"}


def kelly_units(prob, odds, fraction=KELLY_FRACTION):
    """Fractional Kelly stake as a fraction of bankroll (guide only)."""
    b = odds - 1.0
    if b <= 0:
        return 0.0
    edge = prob * odds - 1.0
    full = edge / b
    return max(0.0, round(full * fraction, 3))


def find_value_bets(match_date, home, away, model_probs, odds_1x2):
    """
    Find 1X2 value bets by comparing model probabilities to bookmaker odds.

    Args:
        match_date: Match date (ISO string)
        home, away: Team names
        model_probs: {"1","X","2"} blended probabilities (should sum to 1)
        odds_1x2:    {"1","X","2"} decimal odds from the book (best available, or sharpest)

    Returns:
        A list of value bet dicts for this match (may be empty).
        Each bet includes model_prob, odds, edge, and Kelly stake guide.
    """
    bets = []
    for o in OUTCOMES:
        odds = odds_1x2.get(o)
        if not odds or odds <= 1.0:
            continue
        p = model_probs.get(o, 0.0)
        edge = p * odds - 1.0
        if edge >= MIN_EDGE:
            sel_team = home if o == "1" else away if o == "2" else "Draw"
            bets.append({
                "match_date": match_date,
                "home_team": home,
                "away_team": away,
                "market": "1X2",
                "selection": o,
                "selection_label": f"{LABEL[o]} ({sel_team})" if o != "X" else "Draw",
                "model_prob": round(p, 4),
                "implied_prob": round(1.0 / odds, 4),
                "odds": odds,
                "edge": round(edge, 4),
                "stake_units": FLAT_STAKE_UNITS,
                "kelly_units": kelly_units(p, odds),
            })
    return bets


def _two_way_value(match_date, home, away, market, probs, odds, labels):
    """Generic value finder for a two-outcome market (totals, btts).

    probs:  {sel: model_prob}     e.g. {"Over": .55, "Under": .45}
    odds:   {sel: decimal_odds}   best available per side
    labels: {sel: human label}    shown on the card
    """
    bets = []
    for sel, p in probs.items():
        price = odds.get(sel)
        if not price or price <= 1.0:
            continue
        edge = p * price - 1.0
        if edge >= MIN_EDGE:
            bets.append({
                "match_date": match_date,
                "home_team": home,
                "away_team": away,
                "market": market,
                "selection": sel,
                "selection_label": labels.get(sel, sel),
                "model_prob": round(p, 4),
                "implied_prob": round(1.0 / price, 4),
                "odds": price,
                "edge": round(edge, 4),
                "stake_units": FLAT_STAKE_UNITS,
                "kelly_units": kelly_units(p, price),
            })
    return bets


def find_value_totals(match_date, home, away, ou_probs, totals_odds, line):
    """Value bets on Over/Under `line` from Poisson probs vs book odds."""
    if not totals_odds:
        return []
    labels = {"Over": f"Over {line}", "Under": f"Under {line}"}
    return _two_way_value(match_date, home, away, f"OU{line}",
                          ou_probs, totals_odds, labels)


def find_value_btts(match_date, home, away, btts_probs, btts_odds):
    """Value bets on both-teams-to-score from Poisson probs vs book odds."""
    if not btts_odds:
        return []
    labels = {"Yes": "BTTS Yes", "No": "BTTS No"}
    return _two_way_value(match_date, home, away, "BTTS",
                          btts_probs, btts_odds, labels)


def rank_and_cap(all_bets, max_bets):
    """Sort all candidate bets by edge desc and keep the top N."""
    return sorted(all_bets, key=lambda b: b["edge"], reverse=True)[:max_bets]


if __name__ == "__main__":
    probs = {"1": 0.60, "X": 0.25, "2": 0.15}
    odds = {"1": 1.95, "X": 3.40, "2": 6.00}
    for b in find_value_bets("2026-06-11", "Argentina", "Mexico", probs, odds):
        print(f"{b['selection_label']:18} p={b['model_prob']*100:4.1f}%  "
              f"odds={b['odds']}  edge={b['edge']*100:+.1f}%  "
              f"kelly={b['kelly_units']}")
