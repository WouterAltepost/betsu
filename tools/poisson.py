"""
poisson.py — Dixon-Coles goal model for betsu.

We don't have a historical-scorelines database to fit per-team attack/defense
strengths, so we derive each side's expected goals (lambdas) from the Elo gap:

    supremacy = elo_diff / POISSON_SUP_DIVISOR        # expected goal difference
    lambda_home = (BASE_TOTAL + supremacy) / 2
    lambda_away = (BASE_TOTAL - supremacy) / 2         # floored so blowouts stay sane

From the two lambdas we build the full scoreline grid P(i, j) under independent
Poisson, then apply the Dixon-Coles low-score correction tau(i, j) which boosts
0-0 and 1-1 and trims 1-0 and 0-1 (the dependence real football shows at low
scores). Summing regions of the normalised grid gives every market:

    1X2          home win / draw / away win   (blended into the ensemble)
    Over/Under   total goals vs OU_LINE (2.5)
    BTTS         both teams score yes / no

This is self-contained and reuses the refreshed Elo seeds. The natural upgrade
later is to swap the Elo-derived lambdas for a fitted attack/defense model once
a results feed exists; the market math below would not change.

Functions:
    expected_goals(home, away, ratings, neutral=True) -> (lam_home, lam_away)
    score_matrix(lam_home, lam_away)                  -> list[list[float]] (normalised)
    predict(home, away, ratings, neutral=True)        -> {"1","X","2"}
    markets(home, away, ratings, neutral=True)        -> full market dict

CLI:
    python tools/poisson.py "Spain" "Qatar"
    python tools/poisson.py "United States" "Canada" --home
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (ELO_HOME_ADVANTAGE, OU_LINE, POISSON_BASE_TOTAL_GOALS,
                    POISSON_DC_RHO, POISSON_GOAL_FLOOR, POISSON_MAX_GOALS,
                    POISSON_SUP_DIVISOR, VARIANCE_SCALING_ENABLED,
                    VARIANCE_ELO_THRESHOLD, VARIANCE_SCALE_FACTOR)
from tools import elo as elo_mod


def expected_goals(home, away, ratings, neutral=True):
    """Map the Elo gap to (lambda_home, lambda_away) expected goals.

    Args:
        home, away: Team names
        ratings: Elo ratings dict
        neutral: Whether to apply home advantage (False for non-neutral venues)

    Returns:
        (lambda_home, lambda_away, elo_diff) — the third is used for variance scaling
    """
    rh = elo_mod.get_rating(home, ratings)
    ra = elo_mod.get_rating(away, ratings)
    adv = 0 if neutral else ELO_HOME_ADVANTAGE
    diff = (rh + adv) - ra

    supremacy = diff / POISSON_SUP_DIVISOR
    lam_home = (POISSON_BASE_TOTAL_GOALS + supremacy) / 2.0
    lam_away = (POISSON_BASE_TOTAL_GOALS - supremacy) / 2.0
    return max(lam_home, POISSON_GOAL_FLOOR), max(lam_away, POISSON_GOAL_FLOOR), diff


def _poisson_pmf(k, lam):
    return math.exp(-lam) * lam ** k / math.factorial(k)


def _tau(i, j, lam, mu, rho):
    """Dixon-Coles low-score adjustment."""
    if i == 0 and j == 0:
        return 1.0 - lam * mu * rho
    if i == 0 and j == 1:
        return 1.0 + lam * rho
    if i == 1 and j == 0:
        return 1.0 + mu * rho
    if i == 1 and j == 1:
        return 1.0 - rho
    return 1.0


def score_matrix(lam_home, lam_away, max_goals=POISSON_MAX_GOALS, rho=POISSON_DC_RHO,
                 elo_diff=0.0):
    """Normalised P(home=i, away=j) grid with the Dixon-Coles correction.

    Args:
        lam_home, lam_away: Expected goals (lambdas)
        max_goals: Grid size (0..max_goals each side)
        rho: Dixon-Coles correlation (default POISSON_DC_RHO)
        elo_diff: Elo rating difference (home - away), used for variance scaling
    """
    home_pmf = [_poisson_pmf(i, lam_home) for i in range(max_goals + 1)]
    away_pmf = [_poisson_pmf(j, lam_away) for j in range(max_goals + 1)]

    grid = [[0.0] * (max_goals + 1) for _ in range(max_goals + 1)]
    total = 0.0
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            p = home_pmf[i] * away_pmf[j] * _tau(i, j, lam_home, lam_away, rho)
            p = max(p, 0.0)  # guard tiny negatives from the correction
            grid[i][j] = p
            total += p

    if total > 0:
        for i in range(max_goals + 1):
            for j in range(max_goals + 1):
                grid[i][j] /= total

    # Apply variance scaling for extreme scores (blowout games)
    if VARIANCE_SCALING_ENABLED and abs(elo_diff) > VARIANCE_ELO_THRESHOLD:
        grid = _apply_variance_scaling(grid, elo_diff, max_goals)

    return grid


def _apply_variance_scaling(grid, elo_diff, max_goals):
    """
    Increase tail probability weight for extreme scores when one team is much stronger.

    When home team Elo >> away team, they're more likely to win big (5-0, 6-0)
    than to win narrowly. Redistribute a small amount of probability mass from
    mid-range outcomes (2-3 goals) to extremes (0, 4+).

    Args:
        grid: Current probability matrix (normalized)
        elo_diff: Home Elo - Away Elo
        max_goals: Grid size

    Returns:
        Modified grid with increased tail probabilities
    """
    variance_scale = 1.0 + abs(elo_diff) * VARIANCE_SCALE_FACTOR / 100.0
    # Limit the scaling to avoid excessive distortion
    variance_scale = min(variance_scale, 1.3)

    # Identify mid-range and extreme cells
    redistribution_amount = 0.01  # Move 1% of probability mass
    total_redistribution = 0.0

    # Collect probability from mid-range (2-3 goals for both sides)
    for i in range(2, 4):
        for j in range(2, 4):
            if i < len(grid) and j < len(grid[i]):
                amount = grid[i][j] * redistribution_amount
                grid[i][j] -= amount
                total_redistribution += amount

    if total_redistribution > 0:
        # Distribute to extremes (0 goals, 4+ goals)
        # Weight distribution by elo_diff direction
        if elo_diff > 0:  # Home favored; boost home blowout wins and away shutouts
            # Home big wins (4+)
            for i in range(4, max_goals + 1):
                if i < len(grid):
                    grid[i][0] = min(1.0, grid[i][0] + total_redistribution * 0.4 / max_goals)
                    grid[i][1] = min(1.0, grid[i][1] + total_redistribution * 0.1 / max_goals)
        else:  # Away favored
            # Away big wins (4+)
            for j in range(4, max_goals + 1):
                if j < len(grid[0]):
                    grid[0][j] = min(1.0, grid[0][j] + total_redistribution * 0.4 / max_goals)
                    grid[1][j] = min(1.0, grid[1][j] + total_redistribution * 0.1 / max_goals)

    # Renormalize
    total = sum(sum(row) for row in grid)
    if total > 0:
        for i in range(len(grid)):
            for j in range(len(grid[i])):
                grid[i][j] /= total

    return grid


def _markets_from_grid(grid, line=OU_LINE):
    n = len(grid)
    p_home = p_draw = p_away = 0.0
    p_over = p_under = 0.0
    p_btts_yes = 0.0
    for i in range(n):
        for j in range(n):
            p = grid[i][j]
            if i > j:
                p_home += p
            elif i == j:
                p_draw += p
            else:
                p_away += p
            if i + j > line:
                p_over += p
            else:
                p_under += p
            if i >= 1 and j >= 1:
                p_btts_yes += p
    return {
        "1x2": {"1": round(p_home, 4), "X": round(p_draw, 4), "2": round(p_away, 4)},
        "ou": {"Over": round(p_over, 4), "Under": round(p_under, 4)},
        "btts": {"Yes": round(p_btts_yes, 4), "No": round(1.0 - p_btts_yes, 4)},
    }


def predict(home, away, ratings, neutral=True):
    """1X2 probabilities for the ensemble blend."""
    lam_home, lam_away, elo_diff = expected_goals(home, away, ratings, neutral=neutral)
    grid = score_matrix(lam_home, lam_away, elo_diff=elo_diff)
    return _markets_from_grid(grid)["1x2"]


def markets(home, away, ratings, neutral=True):
    """Full market dict: 1x2, ou (at OU_LINE), btts, plus the lambdas used."""
    lam_home, lam_away, elo_diff = expected_goals(home, away, ratings, neutral=neutral)
    grid = score_matrix(lam_home, lam_away, elo_diff=elo_diff)
    out = _markets_from_grid(grid)
    out["lambdas"] = {"home": round(lam_home, 3), "away": round(lam_away, 3)}
    out["line"] = OU_LINE
    return out


def markets_from_lambdas(lam_home, lam_away):
    """Full market dict from explicit expected goals (no Elo, no variance scaling).

    Shared by the xG layer, which derives its own lambdas from team xG and so
    bypasses the Elo-gap mapping. Passing elo_diff=0.0 also means variance
    scaling never fires here (it gates on |elo_diff| > VARIANCE_ELO_THRESHOLD)."""
    lam_home = max(lam_home, POISSON_GOAL_FLOOR)
    lam_away = max(lam_away, POISSON_GOAL_FLOOR)
    grid = score_matrix(lam_home, lam_away, elo_diff=0.0)  # elo_diff=0 -> no variance
    out = _markets_from_grid(grid)
    out["lambdas"] = {"home": round(lam_home, 3), "away": round(lam_away, 3)}
    out["line"] = OU_LINE
    return out


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    neutral = "--home" not in sys.argv
    ratings = elo_mod.load_ratings()
    if len(args) >= 2:
        home, away = args[0], args[1]
        m = markets(home, away, ratings, neutral=neutral)
        lh, la = m["lambdas"]["home"], m["lambdas"]["away"]
        print(f"{home} vs {away}  neutral={neutral}")
        print(f"  expected goals: {home} {lh:.2f} — {la:.2f} {away}")
        x = m["1x2"]
        print(f"  1X2:   home {x['1']*100:5.1f}%  draw {x['X']*100:5.1f}%  "
              f"away {x['2']*100:5.1f}%")
        print(f"  O/U {m['line']}: over {m['ou']['Over']*100:5.1f}%  "
              f"under {m['ou']['Under']*100:5.1f}%")
        print(f"  BTTS:  yes  {m['btts']['Yes']*100:5.1f}%  "
              f"no   {m['btts']['No']*100:5.1f}%")
    else:
        print("usage: python tools/poisson.py <home> <away> [--home]")
