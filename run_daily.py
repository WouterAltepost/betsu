"""
run_daily.py — the orchestrator (the "Agent" layer of the WAT framework).

Scan mode (default):
  1. Load Elo ratings
  2. Fetch fixtures + odds (the-odds-api) — a time window in --window mode, else a date
  3. For each match: market + Elo + Poisson probs -> ensemble blend
  4. Find value bets vs the odds; keep only selections not already posted (dedup)
  5. Record match probs + the new bets to the Google Sheets store
  6. Send the bet card (the new bets) to Telegram

Grade mode (--grade):
  1. Read final scores from the Sheets Results tab
  2. Grade pending bets in place, send a results recap

Usage:
  python run_daily.py                  # today's card (date mode)
  python run_daily.py --date=2026-06-11
  python run_daily.py --window         # scan the next SCAN_WINDOW_HOURS (as the scheduler does)
  python run_daily.py --window=18
  python run_daily.py --dry-run        # build card, print it, do NOT send/store
  python run_daily.py --grade          # settle pending bets + recap

In production the scheduled scan runs via the /run/morning and /run/grade
endpoints in app.py (n8n calls them); this CLI is the same logic for manual use.
"""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (MAX_BETS_PER_DAY, HOST_NATIONS, OU_LINE, SCAN_WINDOW_HOURS,
                    LLM_ENABLED)
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


def run_morning(run_date, dry_run=False, window_hours=None):
    """Scan fixtures, blend, find value, post only genuinely-new bets.

    window_hours set (scheduled run): scan upcoming, not-yet-started games within
    the window — each bet is dated by its own kickoff (UTC), so it grades against
    the right Results row. Otherwise: scan run_date's slate (manual/CLI).
    Returns a dict summary {matches, new_bets, card, sent}.
    """
    ratings = elo_mod.load_ratings()
    if window_hours is not None:
        matches = fixtures_mod.get_matches(window_hours=window_hours)
        scope = f"next {window_hours}h"
    else:
        matches = fixtures_mod.get_matches(target_date=run_date)
        scope = run_date
    print(f"[betsu] {len(matches)} match(es) for {scope}")

    match_rows, candidates = [], []
    for m in matches:
        home, away = m["home_team"], m["away_team"]
        # In window mode a slate can straddle UTC midnight; date each game by its
        # own kickoff so grading lines up with the Results row.
        m_date = (m.get("commence_time") or "")[:10] if window_hours is not None else run_date
        m_date = m_date or run_date
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
        llm_adjust = None
        context_note = None
        if unseeded:
            print(f"  [elo/poisson skipped — no seed for: {', '.join(unseeded)}]")
        else:
            preds["elo"] = elo_mod.predict(home, away, ratings, neutral=neutral)
            poisson_mkts = poisson_mod.markets(home, away, ratings, neutral=neutral)
            preds["poisson"] = poisson_mkts["1x2"]

            # LLM context nudge (1X2 only): same seeded gate as Elo/Poisson, and
            # only when explicitly enabled. The layer is fail-safe — a failure
            # returns a zero nudge, so the blend is unaffected.
            if LLM_ENABLED:
                from tools import llm_context as llm_mod
                ctx = llm_mod.get_adjustment(home, away, m.get("commence_time", ""))
                if any(v for v in ctx["nudge"].values()):
                    llm_adjust = ctx["nudge"]
                    src = (ctx.get("factors") or [{}])[0].get("source", "") \
                        or ctx.get("source", "")
                    context_note = ctx.get("summary") or "Context nudge applied."
                    if src:
                        context_note = f"{context_note} ({src})"
                    print(f"  [llm context: {ctx['nudge']} — {ctx.get('summary','')}]")

        blended = ensemble_mod.blend(preds, llm_adjust=llm_adjust)
        match_rows.append((m_date, home, away, blended))

        # 1X2 value from the blended probabilities.
        bets = value_mod.find_value_bets(m_date, home, away, blended, m["odds"])
        # Over/Under 2.5 and BTTS value come from Poisson alone (the only layer
        # that produces goal-based probabilities) vs the book's totals/btts odds.
        if poisson_mkts:
            bets += value_mod.find_value_totals(
                m_date, home, away, poisson_mkts["ou"],
                m.get("totals_odds"), OU_LINE)
            bets += value_mod.find_value_btts(
                m_date, home, away, poisson_mkts["btts"], m.get("btts_odds"))

        for b in bets:
            b["commence_time"] = m.get("commence_time", "")
            if context_note:
                b["context_note"] = context_note
        candidates.extend(bets)
        print(f"  {home} vs {away}: blend={blended} -> {len(bets)} value bet(s)")

    if dry_run:
        ranked = value_mod.rank_and_cap(candidates, MAX_BETS_PER_DAY)
        card = message_mod.build_daily_card(run_date, ranked, len(matches), None)
        print("\n----- CARD (dry run, not sent) -----\n")
        print(card)
        return {"matches": len(matches), "new_bets": len(ranked),
                "card": card, "sent": False}

    # Record match-level probs (calibration), then post only the best NEW bets.
    tracker_mod.record_matches(match_rows)
    fresh = tracker_mod.filter_new(candidates)
    ranked = value_mod.rank_and_cap(fresh, MAX_BETS_PER_DAY)
    posted = tracker_mod.record_bets(ranked)
    record = tracker_mod.summary(write=True)
    card = message_mod.build_daily_card(run_date, posted, len(matches), record)

    if posted:
        from tools.telegram_send import send_message
        send_message(card)
    print(f"[betsu] {len(posted)} new bet(s) posted.")
    return {"matches": len(matches), "new_bets": len(posted),
            "card": card, "sent": bool(posted)}


def run_grade(run_date):
    """Settle pending bets against the Results tab and post a recap.
    Returns a dict summary {settled, record, recap}."""
    settled = tracker_mod.grade_pending()
    record = tracker_mod.summary(write=True)
    recap = message_mod.build_results_recap(run_date, settled, record)
    from tools.telegram_send import send_message
    send_message(recap)
    print(f"[betsu] Graded {settled} bet(s).")
    return {"settled": settled, "record": record, "recap": recap}


if __name__ == "__main__":
    run_date = next((a.split("=")[1] for a in sys.argv if a.startswith("--date=")),
                    str(date.today()))
    window = None
    if "--window" in sys.argv:
        window = SCAN_WINDOW_HOURS
    window = next((int(a.split("=")[1]) for a in sys.argv if a.startswith("--window=")),
                  window)
    tracker_mod.init_db()
    if "--grade" in sys.argv:
        run_grade(run_date)
    else:
        run_morning(run_date, dry_run="--dry-run" in sys.argv, window_hours=window)
