#!/usr/bin/env python
"""
test_new_features.py — smoke test for the accuracy-improvement features.

Each check is isolated: one failure reports and the script CONTINUES, so the
whole suite always runs to completion (no early abort). Exits non-zero iff any
check failed. Everything here is offline — no API calls, no FBref scrape.

Checks:
  1. config.py exposes the current flags (variance OFF by default, sharp key, xG)
  2. xg.py — get_xg_prediction loads and is fail-safe (layer off -> None)
  3. sharp layer — fixtures._book_h2h_odds extracts a single book's 1X2
  4. poisson.py — markets() + markets_from_lambdas(); variance branch can't crash
  5. ensemble.py — blend accepts and renormalises the xG layer
  6. run_daily.py imports cleanly (no dangling sharp_soft / Pinnacle refs)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

RESULTS = []


def check(name, fn):
    """Run one isolated check; record pass/fail and keep going."""
    print(f"\n[{name}]")
    try:
        fn()
        print(f"  ✓ passed")
        RESULTS.append((name, True))
    except Exception as e:
        import traceback
        print(f"  ✗ FAILED: {e}")
        traceback.print_exc()
        RESULTS.append((name, False))


def t_config():
    from config import (
        XG_ENABLED, XG_SEASON, XG_MATCHES_BACK, XG_MIN_MATCHES, XG_CACHE_HOURS,
        VARIANCE_SCALING_ENABLED, VARIANCE_ELO_THRESHOLD, VARIANCE_SCALE_FACTOR,
        SHARP_SOFT_MONITORING_ENABLED, SHARP_BOOKMAKER_KEY, ENSEMBLE_WEIGHTS,
    )
    assert "xg" in ENSEMBLE_WEIGHTS, "xG weight missing from ENSEMBLE_WEIGHTS"
    assert VARIANCE_SCALING_ENABLED is False, "variance scaling must DEFAULT OFF"
    assert SHARP_BOOKMAKER_KEY, "SHARP_BOOKMAKER_KEY must be set"
    print(f"  VARIANCE_SCALING_ENABLED={VARIANCE_SCALING_ENABLED} (off)  "
          f"SHARP_BOOKMAKER_KEY={SHARP_BOOKMAKER_KEY!r}  XG_ENABLED={XG_ENABLED}")
    print(f"  ENSEMBLE_WEIGHTS keys={list(ENSEMBLE_WEIGHTS.keys())}, "
          f"xg weight={ENSEMBLE_WEIGHTS['xg']}")


def t_xg():
    from tools import xg as xg_mod
    from tools import elo as elo_mod
    assert hasattr(xg_mod, "get_xg_prediction"), "get_xg_prediction not found"
    ratings = elo_mod.load_ratings()
    # Fail-safe contract: must return None or a valid 1X2, never raise. With the
    # layer off (default) it is a no-op None.
    out = xg_mod.get_xg_prediction("Brazil", "Spain", ratings)
    assert out is None or set(out) == {"1", "X", "2"}, f"unexpected output: {out}"
    print(f"  get_xg_prediction('Brazil','Spain') -> {out}")


def t_sharp():
    from tools import fixtures as fx
    assert hasattr(fx, "_book_h2h_odds"), "_book_h2h_odds not found"
    assert fx.SHARP_BOOKMAKER_KEY, "SHARP_BOOKMAKER_KEY not exposed on fixtures"
    # Synthetic event with two books; pull the named (sharp) book's own 1X2.
    event = {
        "home_team": "Brazil", "away_team": "Spain",
        "bookmakers": [
            {"key": "somesoftbook", "markets": [{"key": "h2h", "outcomes": [
                {"name": "Brazil", "price": 2.00}, {"name": "Spain", "price": 3.50},
                {"name": "Draw", "price": 3.40}]}]},
            {"key": fx.SHARP_BOOKMAKER_KEY, "markets": [{"key": "h2h", "outcomes": [
                {"name": "Brazil", "price": 2.05}, {"name": "Spain", "price": 3.60},
                {"name": "Draw", "price": 3.45}]}]},
        ],
    }
    sharp = fx._book_h2h_odds(event, fx.SHARP_BOOKMAKER_KEY)
    assert sharp == {"1": 2.05, "2": 3.60, "X": 3.45}, f"got {sharp}"
    assert fx._book_h2h_odds(event, "absent_book") == {}, "absent book must give {}"
    print(f"  _book_h2h_odds({fx.SHARP_BOOKMAKER_KEY!r}) -> {sharp}")


def t_poisson():
    from tools import poisson as poisson_mod
    from tools import elo as elo_mod
    ratings = elo_mod.load_ratings()

    # expected_goals returns the 3-tuple (lambdas + elo_diff)
    lh, la, elo_diff = poisson_mod.expected_goals("Brazil", "Mexico", ratings, neutral=True)
    assert isinstance(elo_diff, (int, float)), "elo_diff not numeric"

    # Full market dict for a home-favoured match (the branch that used to crash)
    mkts = poisson_mod.markets("Brazil", "Mexico", ratings, neutral=True)
    for k in ("1x2", "ou", "btts"):
        assert k in mkts, f"{k} missing from markets()"
    assert 0.99 < sum(mkts["1x2"].values()) < 1.01, "1X2 not normalised"

    # Shared xG helper
    lam = poisson_mod.markets_from_lambdas(1.6, 0.9)["1x2"]
    assert 0.99 < sum(lam.values()) < 1.01, "markets_from_lambdas not normalised"

    # Directly exercise the previously-crashing home-favoured variance branch
    # (elo_diff > 0), independent of the now-default-off flag — must not crash
    # and must stay normalised.
    grid = poisson_mod.score_matrix(1.9, 0.6)
    scaled = poisson_mod._apply_variance_scaling(
        grid, elo_diff=300.0, max_goals=poisson_mod.POISSON_MAX_GOALS)
    assert 0.99 < sum(sum(r) for r in scaled) < 1.01, "variance grid not normalised"
    print(f"  markets 1x2={mkts['1x2']}  from_lambdas={lam}  variance-branch OK")


def t_ensemble():
    from tools import ensemble as ensemble_mod
    predictions = {
        "market": {"1": 0.55, "X": 0.27, "2": 0.18},
        "elo": {"1": 0.60, "X": 0.25, "2": 0.15},
        "poisson": {"1": 0.58, "X": 0.26, "2": 0.16},
        "xg": {"1": 0.57, "X": 0.26, "2": 0.17},
    }
    blended = ensemble_mod.blend(predictions)
    assert set(blended) == {"1", "X", "2"} and 0.99 < sum(blended.values()) < 1.01
    no_xg = ensemble_mod.blend({k: v for k, v in predictions.items() if k != "xg"})
    assert 0.99 < sum(no_xg.values()) < 1.01, "renormalised blend (no xG) broke"
    print(f"  blend with xG={blended}  without xG={no_xg}")


def t_run_daily():
    import run_daily
    assert hasattr(run_daily, "run_morning") and hasattr(run_daily, "run_grade")
    print("  run_daily imports; run_morning/run_grade present")


# Guarded under __main__ so pytest can import this file during collection
# without executing the suite (which calls sys.exit and would abort the run).
if __name__ == "__main__":
    print("=" * 60)
    print("BETSU ACCURACY IMPROVEMENTS — SMOKE TEST")
    print("=" * 60)

    for _name, _fn in [
        ("config", t_config),
        ("xg", t_xg),
        ("sharp", t_sharp),
        ("poisson", t_poisson),
        ("ensemble", t_ensemble),
        ("run_daily import", t_run_daily),
    ]:
        check(_name, _fn)

    _passed = sum(1 for _, ok in RESULTS if ok)
    _total = len(RESULTS)
    print("\n" + "=" * 60)
    print(f"{_passed}/{_total} checks passed"
          + ("" if _passed == _total else "  — "
             + ", ".join(n for n, ok in RESULTS if not ok) + " FAILED"))
    print("=" * 60)
    print("\nFeature flags (set in .env / Railway to enable):")
    print("  - XG_ENABLED=1                     (FBref xG via soccerdata)")
    print("  - SHARP_SOFT_MONITORING_ENABLED=1  (use the Pinnacle line for the market layer)")
    print("  - VARIANCE_SCALING_ENABLED=1       (off pending a calibration backtest)")
    sys.exit(0 if _passed == _total else 1)
