"""
run_daily.py — the orchestrator (the "Agent" layer of the WAT framework).

Morning mode (default):
  1. Load Elo ratings
  2. Fetch today's fixtures + odds (the-odds-api)
  3. For each match: market probs + Elo probs -> ensemble blend
  4. Find value bets vs the odds
  5. Record matches + bets to SQLite
  6. Send the daily bet card to Telegram

Evening / grade mode (--grade):
  1. Pull results (manual entry or fetch_results)
  2. Grade pending bets, send a results recap

Usage:
  python run_daily.py                  # today's card
  python run_daily.py --date=2026-06-11
  python run_daily.py --dry-run        # build card, print it, do NOT send/store
  python run_daily.py --grade          # settle pending bets + recap
"""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import MAX_BETS_PER_DAY, HOST_NATIONS, OU_LINE
from tools import elo as elo_mod
from tools import ensemble as ensemble_mod
from tools import poisson as poisson_mod
from tools import value as value_mod
from tools import message as message_mod
from tools import tracker as tracker_mod
from tools import fixtures as fixtures_mod


def _neutral_and_host(home, away):
    """World Cup is neutral-venue except host nations playing at home.
    We only know the venue country from richer fixture data; default neutral.
    Host nation listed as home gets home advantage as a reasonable proxy."""
    if home in HOST_NATIONS:
        return False  # treat host as having home advantage
    return True


def _sync_sheets():
    """Mirror the DB to Google Sheets if configured. Never raises."""
    try:
        from tools import sheets as sheets_mod
        if sheets_mod.enabled():
            print(f"[betsu] {sheets_mod.sync_all()}")
    except Exception as e:
        print(f"[betsu] Sheets sync skipped: {e}")


def run_morning(run_date, dry_run=False):
    ratings = elo_mod.load_ratings()
    matches = fixtures_mod.get_matches(target_date=run_date)
    print(f"[betsu] {len(matches)} match(es) for {run_date}")

    all_bets = []
    for m in matches:
        home, away = m["home_team"], m["away_team"]
        neutral = _neutral_and_host(home, away)
        preds = {"market": m["market_probs"]}

        # Elo guard: only include the Elo layer when BOTH teams are seeded.
        # An unseeded team defaults to 1700, which skews the 30%-weighted Elo
        # layer toward longshots and fabricates value edges. When a team is
        # missing a seed we drop Elo for this match and let the blend
        # renormalise over the remaining layers (market only for the MVP).
        # Both Elo and Poisson read team ratings, so a missing seed disables
        # both layers (and the goal-based markets) for this match.
        unseeded = [t for t in (home, away) if not elo_mod.is_seeded(t, ratings)]
        poisson_mkts = None
        if unseeded:
            print(f"  [elo/poisson skipped — no seed for: {', '.join(unseeded)}]")
        else:
            preds["elo"] = elo_mod.predict(home, away, ratings, neutral=neutral)
            poisson_mkts = poisson_mod.markets(home, away, ratings, neutral=neutral)
            preds["poisson"] = poisson_mkts["1x2"]

        blended = ensemble_mod.blend(preds)
        if not dry_run:
            tracker_mod.record_match(run_date, home, away, blended)

        # 1X2 value from the blended probabilities.
        bets = value_mod.find_value_bets(run_date, home, away, blended, m["odds"])
        # Over/Under 2.5 and BTTS value come from Poisson alone (the only layer
        # that produces goal-based probabilities) vs the book's totals/btts odds.
        if poisson_mkts:
            bets += value_mod.find_value_totals(
                run_date, home, away, poisson_mkts["ou"],
                m.get("totals_odds"), OU_LINE)
            bets += value_mod.find_value_btts(
                run_date, home, away, poisson_mkts["btts"], m.get("btts_odds"))

        all_bets.extend(bets)
        print(f"  {home} vs {away}: blend={blended} -> {len(bets)} value bet(s)")

    ranked = value_mod.rank_and_cap(all_bets, MAX_BETS_PER_DAY)

    if not dry_run:
        for b in ranked:
            tracker_mod.record_bet(b)
        record = tracker_mod.summary()
    else:
        record = None

    card = message_mod.build_daily_card(run_date, ranked, len(matches), record)

    if dry_run:
        print("\n----- CARD (dry run, not sent) -----\n")
        print(card)
        return card

    from tools.telegram_send import send_message
    send_message(card)
    print(f"[betsu] Sent card with {len(ranked)} bet(s).")
    _sync_sheets()
    return card


def run_grade(run_date):
    settled = tracker_mod.grade_pending()
    record = tracker_mod.summary()
    recap = message_mod.build_results_recap(run_date, settled, record)
    from tools.telegram_send import send_message
    send_message(recap)
    print(f"[betsu] Graded {settled} bet(s).")
    _sync_sheets()
    return recap


if __name__ == "__main__":
    run_date = next((a.split("=")[1] for a in sys.argv if a.startswith("--date=")),
                    str(date.today()))
    tracker_mod.init_db()
    if "--grade" in sys.argv:
        run_grade(run_date)
    else:
        run_morning(run_date, dry_run="--dry-run" in sys.argv)
