"""
xg.py — Expected Goals (xG) layer for the ensemble (FBref via soccerdata).

Real World Cup xG (Opta-sourced) is pulled from FBref's `INT-World Cup`
competition with soccerdata, aggregated per team over their last
XG_MATCHES_BACK matches, then turned into a 1X2 distribution by reusing the
tested Poisson grid (poisson.markets_from_lambdas). FBref team names are
reconciled to our seed names through the Elo resolver (elo.lookup_rating) — the
same ALIASES + accent-fold + fuzzy>=90 + ambiguity guard — so a confusable pair
(Austria/Australia, Iran/Iraq) can never silently mis-map.

The layer is FULLY FAIL-SAFE. Any of: xG disabled, scrape/parse error, an
unmapped team, or too few played matches (< XG_MIN_MATCHES) yields None, and the
ensemble renormalises over the remaining layers. It never raises into
run_morning.

State of FBref data (verified 2026-06-12): national-team xG is the hard case and
is published late. Early in the tournament FBref exposes NO xG columns at all for
`INT-World Cup` — so the table is empty and every prediction is None (the correct
cold-start). The layer activates automatically once FBref starts carrying xG.
xG is OFF by default (XG_ENABLED) and should be turned on only after the slate
has enough played matches with xG to validate calibration.

Heads-up: soccerdata's FBref reader uses a headless browser (seleniumbase /
undetected-chromedriver) to clear Cloudflare — it is NOT plain HTTP. Enabling
this on a server therefore requires Chrome/Chromium available to that runtime.

Public:
    get_xg_prediction(home, away, ratings) -> {"1","X","2"} | None

CLI:
    python tools/xg.py --test     # resolved-table size + one sample prediction
"""

import os
import sys
import time
from pathlib import Path
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (XG_ENABLED, XG_SEASON, XG_MATCHES_BACK, XG_MIN_MATCHES,
                    XG_CACHE_HOURS, TMP_DIR)
from tools import elo as elo_mod
from tools import poisson as poisson_mod

# Confirmed via soccerdata FBref.available_leagues() — the men's World Cup.
FBREF_LEAGUE = "INT-World Cup"

# In-process cache of the whole resolved xG table. Built once per cold process
# (a soccerdata scrape is expensive — it launches a headless browser), reused for
# every match in a run, and rebuilt only after XG_CACHE_HOURS. On stateless
# Railway each cold run rebuilds it once, which is fine.
_TABLE_CACHE = {"built_at": 0.0, "table": None}


def _flat_name(col) -> str:
    """A MultiIndex column ('Expected','xG') -> 'Expected/xG'; flat stays as-is."""
    return "/".join(str(x) for x in col) if isinstance(col, tuple) else str(col)


def _find_col(columns, *names) -> Optional[object]:
    """First column whose flattened name (or its last '/'-segment, for a
    MultiIndex like 'Expected/xG') case-insensitively equals one of `names`."""
    wanted = {n.lower() for n in names}
    for c in columns:
        flat = _flat_name(c).strip().lower()
        leaf = flat.split("/")[-1].strip()
        if flat in wanted or leaf in wanted:
            return c
    return None


def _build_xg_table(ratings: dict) -> dict:
    """Scrape FBref once and aggregate per-team xG-for / xG-against over each
    team's last XG_MATCHES_BACK matches, keyed by our canonical team name.

    Returns {canonical_team: {"xg_for","xg_against","matches"}}. Returns {} when
    FBref exposes no xG yet (correct cold-start) or when nothing resolves."""
    import soccerdata as sd  # lazy: importing this module must never need soccerdata
    import pandas as pd      # pandas ships with soccerdata

    data_dir = Path(TMP_DIR) / "soccerdata"
    data_dir.mkdir(parents=True, exist_ok=True)
    fb = sd.FBref(leagues=FBREF_LEAGUE, seasons=XG_SEASON, data_dir=data_dir)
    df = fb.read_team_match_stats(stat_type="schedule")
    if df is None or len(df) == 0:
        return {}

    xg_col = _find_col(df.columns, "xg")
    xga_col = _find_col(df.columns, "xga")
    if xg_col is None or xga_col is None:
        # FBref has not published xG for this competition yet — correct cold-start.
        return {}

    # `team` is an index level on the match-log frame; work off a flat copy.
    flat = df.reset_index()
    team_col = "team" if "team" in flat.columns else _find_col(flat.columns, "team")
    date_col = _find_col(flat.columns, "date")
    if team_col is None or date_col is None:
        return {}

    flat = flat[[team_col, date_col, xg_col, xga_col]].copy()
    flat.columns = ["team", "date", "xg", "xga"]
    flat["xg"] = pd.to_numeric(flat["xg"], errors="coerce")
    flat["xga"] = pd.to_numeric(flat["xga"], errors="coerce")
    flat = flat.dropna(subset=["xg", "xga"])
    if len(flat) == 0:
        return {}
    flat = flat.sort_values("date")

    table = {}
    for fbref_name, grp in flat.groupby("team"):
        canonical = elo_mod.lookup_rating(str(fbref_name), ratings)[1]
        if canonical is None:
            continue  # unmapped FBref name — skip rather than guess (see ALIASES)
        recent = grp.tail(XG_MATCHES_BACK)
        if len(recent) == 0:
            continue
        table[canonical] = {
            "xg_for": float(recent["xg"].mean()),
            "xg_against": float(recent["xga"].mean()),
            "matches": int(len(recent)),
        }
    return table


def _load_xg_table(ratings: dict) -> dict:
    """Return the cached xG table, rebuilding past the TTL. Fail-safe: any error
    caches an EMPTY table for the TTL, so one broken scrape doesn't relaunch the
    browser on every match in a run."""
    now = time.time()
    if (_TABLE_CACHE["table"] is not None
            and now - _TABLE_CACHE["built_at"] < XG_CACHE_HOURS * 3600):
        return _TABLE_CACHE["table"]
    try:
        table = _build_xg_table(ratings)
    except Exception as e:
        print(f"  [xg: table build failed — {type(e).__name__}: {e}]")
        table = {}
    _TABLE_CACHE["table"] = table
    _TABLE_CACHE["built_at"] = now
    return table


def get_xg_prediction(home, away, ratings) -> Optional[dict]:
    """1X2 from team xG via the Poisson grid, or None.

    None when: xG disabled, either team missing or under-sampled
    (< XG_MIN_MATCHES) in the xG table, or any error. Lambdas use the standard
    conversion:
        lam_home = (home_xg_for + away_xg_against) / 2
        lam_away = (away_xg_for + home_xg_against) / 2
    """
    if not XG_ENABLED:
        return None
    try:
        table = _load_xg_table(ratings)
        if not table:
            return None
        h = table.get(elo_mod.lookup_rating(home, ratings)[1] or home)
        a = table.get(elo_mod.lookup_rating(away, ratings)[1] or away)
        if not h or not a:
            return None
        if h["matches"] < XG_MIN_MATCHES or a["matches"] < XG_MIN_MATCHES:
            return None
        lam_home = (h["xg_for"] + a["xg_against"]) / 2.0
        lam_away = (a["xg_for"] + h["xg_against"]) / 2.0
        return poisson_mod.markets_from_lambdas(lam_home, lam_away)["1x2"]
    except Exception as e:
        print(f"  [xg: skipped — {type(e).__name__}]")
        return None


if __name__ == "__main__":
    if "--test" not in sys.argv:
        print("usage: python tools/xg.py --test")
        sys.exit(0)

    ratings = elo_mod.load_ratings()
    print(f"xG layer: XG_ENABLED={XG_ENABLED}, league={FBREF_LEAGUE!r}, "
          f"season={XG_SEASON}, matches_back={XG_MATCHES_BACK}, "
          f"min_matches={XG_MIN_MATCHES}")

    if not XG_ENABLED:
        # Prove the module loads and is fail-safe even with the layer off.
        print("layer OFF — get_xg_prediction is a no-op:")
        print("  Brazil vs Spain ->", get_xg_prediction("Brazil", "Spain", ratings))
        sys.exit(0)

    table = _load_xg_table(ratings)
    print(f"resolved xG table: {len(table)} team(s)")
    for team, v in sorted(table.items()):
        print(f"  {team:24} xg_for={v['xg_for']:.2f}  "
              f"xg_against={v['xg_against']:.2f}  n={v['matches']}")

    if len(table) >= 2:
        h, a = sorted(table.keys())[:2]
        print(f"\nsample {h} vs {a}: {get_xg_prediction(h, a, ratings)}")
    else:
        print("\nno xG published yet for INT-World Cup — layer correctly yields "
              "None (it activates automatically once FBref carries xG).")
        print("sample Brazil vs Spain:", get_xg_prediction("Brazil", "Spain", ratings))
