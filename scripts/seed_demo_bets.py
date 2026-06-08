"""
seed_demo_bets.py — one-off demo-data seeder for manual dashboard testing.

Appends a batch of plausible *suggested* bets to the live Bets tab so the user can
hand-exercise the place -> stake -> settle flow on the dashboard, then watch the
Performance page recompute. All bets start UNPLACED (blank slate): only the
suggestion fields are set, so `placed` / `staked_real` / `result` / `manual_result`
/ `pnl_eur` default to empty via tracker._bet_row.

This is a dev tool, NOT part of the run flow:
  - it appends via tracker.record_bets (dedup-safe, batched), nothing else;
  - it makes no odds calls, sends no Telegram, and does not touch /run/morning
    or /run/grade. No imports of fixtures or telegram.

The seeded set:
  - ~16 settle-able bets with PAST kickoffs (commence_time in the past), spread
    across the last ~12 days, mixed evenly across 1X2 / OU2.5 / BTTS. The
    dashboard only shows Win/Loss settle buttons once a placed bet is `played`,
    which app.py:_kickoff_past drives off commence_time — so these can be settled.
  - 3 future-dated bets (match_date = today, kickoff a few hours/days ahead) that
    land on the Today tab and stay unplayed (place control, no settle yet).

Markets use the real backend strings ("OU2.5", not "OU 2.5"), so the API's
display normalization is exactly what makes them render correctly — the same path
real June-11 bets take. The user deletes these rows from the sheet by hand
afterwards (no marker column, no purge tooling).

Run:
    python scripts/seed_demo_bets.py --dry-run   # print rows, write nothing
    python scripts/seed_demo_bets.py             # append to the live Bets tab
"""

import argparse
import os
import sys
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools import tracker

FLAT_STAKE_UNITS = 1.0


def _kelly(prob, odds, fraction=0.25):
    """Quarter-Kelly guide, mirroring tools/value.kelly_units (kept local so the
    seeder pulls in nothing from the run flow)."""
    b = odds - 1.0
    if b <= 0:
        return 0.0
    full = (prob * odds - 1.0) / b
    return max(0.0, round(full * fraction, 3))


def _bet(match_date, commence_time, home, away, market, selection,
         selection_label, model_prob, odds):
    """Build one suggestion row. edge = model_prob*odds - 1 (kept in +5%..+22%);
    implied = 1/odds. Only suggestion fields are set — the bet starts unplaced."""
    edge = model_prob * odds - 1.0
    return {
        "match_date": match_date,
        "commence_time": commence_time,
        "home_team": home,
        "away_team": away,
        "market": market,
        "selection": selection,
        "selection_label": selection_label,
        "model_prob": round(model_prob, 4),
        "implied_prob": round(1.0 / odds, 3),
        "odds": odds,
        "edge": round(edge, 4),
        "stake_units": FLAT_STAKE_UNITS,
        "kelly_units": _kelly(model_prob, odds),
    }


def build_demo_bets(today):
    """The demo set: ~16 settle-able (past kickoff) + 3 future-dated (today).

    Each tuple is (days_ago, home, away, market, selection, label, model_prob,
    odds). model_prob is chosen so edge lands in +5%..+22%; probs are spread
    across the calibration bins (~0.30 / ~0.50 / ~0.70) and the three markets are
    mixed roughly evenly so ROI-by-market has all three groups.
    """
    # (days_ago, home, away, market, selection, label, model_prob, odds)
    past = [
        # --- 1X2 ---
        (12, "Brazil", "Serbia", "1X2", "1", "Home (Brazil)", 0.70, 1.70),
        (11, "Spain", "Croatia", "1X2", "1", "Home (Spain)", 0.52, 2.20),
        (10, "France", "Denmark", "1X2", "X", "Draw", 0.32, 3.60),
        (8, "Argentina", "Mexico", "1X2", "1", "Home (Argentina)", 0.68, 1.75),
        (6, "Germany", "Japan", "1X2", "2", "Away (Japan)", 0.30, 4.00),
        (4, "Portugal", "Uruguay", "1X2", "1", "Home (Portugal)", 0.50, 2.30),
        # --- OU2.5 ---
        (12, "Netherlands", "Ecuador", "OU2.5", "Over", "Over 2.5", 0.55, 2.05),
        (10, "England", "Wales", "OU2.5", "Under", "Under 2.5", 0.53, 2.10),
        (7, "Belgium", "Morocco", "OU2.5", "Over", "Over 2.5", 0.51, 2.25),
        (5, "Italy", "Switzerland", "OU2.5", "Under", "Under 2.5", 0.50, 2.20),
        (3, "USA", "Iran", "OU2.5", "Over", "Over 2.5", 0.69, 1.70),
        # --- BTTS ---
        (11, "Colombia", "Senegal", "BTTS", "Yes", "BTTS Yes", 0.56, 2.00),
        (9, "Mexico", "Poland", "BTTS", "No", "BTTS No", 0.52, 2.15),
        (6, "Canada", "Ghana", "BTTS", "Yes", "BTTS Yes", 0.50, 2.25),
        (4, "Korea Republic", "Qatar", "BTTS", "No", "BTTS No", 0.31, 3.50),
        (2, "Australia", "Tunisia", "BTTS", "Yes", "BTTS Yes", 0.70, 1.65),
    ]
    # Future-dated: match_date = today, kickoff a few hours/days ahead. One per
    # market so the Today tab shows a mix.
    future = [
        # (hours_ahead, home, away, market, selection, label, model_prob, odds)
        (5, "Brazil", "Spain", "1X2", "1", "Home (Brazil)", 0.50, 2.30),
        (28, "Norway", "Austria", "OU2.5", "Over", "Over 2.5", 0.54, 2.10),
        (52, "Croatia", "Nigeria", "BTTS", "Yes", "BTTS Yes", 0.53, 2.05),
    ]

    bets = []
    for days_ago, home, away, market, sel, label, p, odds in past:
        d = today - timedelta(days=days_ago)
        # Kickoff at 18:00 UTC on the match day — comfortably in the past.
        ct = datetime(d.year, d.month, d.day, 18, 0, 0,
                      tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        bets.append(_bet(d.isoformat(), ct, home, away, market, sel, label, p, odds))

    now = datetime.now(timezone.utc)
    for hours_ahead, home, away, market, sel, label, p, odds in future:
        ct = (now + timedelta(hours=hours_ahead)).strftime("%Y-%m-%dT%H:%M:%SZ")
        bets.append(_bet(today.isoformat(), ct, home, away, market, sel, label, p, odds))

    return bets


def _print_rows(bets):
    print(f"{'date':12} {'fixture':28} {'market':7} {'pick':12} "
          f"{'p':>5} {'odds':>5} {'edge':>6} {'kelly':>6}")
    for b in bets:
        fixture = f"{b['home_team']} v {b['away_team']}"
        print(f"{b['match_date']:12} {fixture:28.28} {b['market']:7} "
              f"{b['selection']:12.12} {b['model_prob']*100:4.0f}% "
              f"{b['odds']:5.2f} {b['edge']*100:+5.1f}% {b['kelly_units']:6.3f}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                    help="print the rows that would be inserted; write nothing")
    args = ap.parse_args()

    today = date.today()
    bets = build_demo_bets(today)

    if args.dry_run:
        _print_rows(bets)
        print(f"\n[dry-run] {len(bets)} demo bets — nothing written.")
        return

    tracker.init_db()
    written = tracker.record_bets(bets)
    _print_rows(bets)
    print(f"\nWrote {len(written)} of {len(bets)} demo bets "
          f"({len(bets) - len(written)} skipped as duplicates).")
    print("Demo rows added to the live Bets tab. Delete them from the sheet "
          "before the first real scan on June 11.")


if __name__ == "__main__":
    main()
