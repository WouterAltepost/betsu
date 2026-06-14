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
from datetime import date, datetime, timedelta, timezone
from time import perf_counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (MAX_BETS_PER_DAY, HOST_NATIONS, OU_LINE, SCAN_WINDOW_HOURS,
                    LLM_ENABLED, LLM_RUN_BUDGET_S, LLM_MAX_PARALLEL,
                    AUTO_RESULTS_ENABLED, BTTS_ENABLED,
                    BTTS_CACHE_HOURS, XG_ENABLED, SHARP_SOFT_MONITORING_ENABLED)
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


def _btts_odds_for(event_id, dry_run=False):
    """Best BTTS Yes/No odds for an event, cached per event id and TTL-gated.

    BTTS is an ADDITIONAL market billed per event, so this is the ONLY place we
    fetch it: a fresh cache row (even one recording "not offered") is reused, so
    API use is bounded to ~one call per event per BTTS_CACHE_HOURS. Returns
    {"Yes": odds, "No": odds} or None. In dry-run we still fetch (for a realistic
    card) but never write the cache. Fail-safe: any miss/error yields None."""
    if not event_id:
        return None
    now = datetime.now(timezone.utc)
    cached = tracker_mod.fetch_btts_odds(event_id)
    if cached:
        try:
            fetched = datetime.fromisoformat(
                str(cached.get("fetched_at", "")).replace("Z", "+00:00"))
        except ValueError:
            fetched = None
        if fetched and (now - fetched) < timedelta(hours=BTTS_CACHE_HOURS):
            if cached.get("yes") and cached.get("no"):
                return {"Yes": cached["yes"], "No": cached["no"]}
            return None  # fresh row recording "no BTTS offered" — don't refetch

    odds = fixtures_mod.fetch_event_btts(event_id)
    print(f"  [btts fetch event {event_id}: "
          f"{odds if odds else 'not offered'}]")
    if not dry_run:
        yes = odds["Yes"] if odds else ""
        no = odds["No"] if odds else ""
        tracker_mod.upsert_btts_odds(event_id, yes, no, now.isoformat())
    return odds


def _gather_llm_nudges(seeded_matches):
    """Precompute the LLM context nudge for each seeded fixture, bounded by
    LLM_RUN_BUDGET_S wall-clock and parallelised over LLM_MAX_PARALLEL workers.

    `seeded_matches` is a list of (home, away, commence_time). Returns
    {(home, away): result_dict} for fixtures that resolved in time; any fixture
    not finished within the run budget is simply omitted, and the caller falls
    back to a zero nudge for it. This is the big win over the old per-match
    sequential calls: N fixtures cost ~one fixture's latency, not N×.

    Cache discipline (gspread is not thread-safe): warm-cache reads happen here
    on the main thread first, only the misses are researched in the pool with
    use_cache=False (network only), and their results are written to the cache
    serially on the main thread afterwards."""
    from concurrent.futures import (ThreadPoolExecutor, TimeoutError as FutTimeout,
                                     as_completed)
    from tools import llm_context as llm_mod

    results, misses = {}, []
    # Warm-cache reads, serial (cheap; keeps Sheets access off the worker threads).
    for (home, away, ct) in seeded_matches:
        try:
            cached = llm_mod.cache_load_public(ct, home, away)
        except Exception:
            cached = None
        if cached is not None:
            results[(home, away)] = cached
        else:
            misses.append((home, away, ct))

    if not misses:
        return results

    to_store = []
    # Not a `with` block on purpose: the context-manager exit joins in-flight
    # threads, which would let a slow wave overrun the budget. We shut down
    # without waiting so LLM_RUN_BUDGET_S is a real wall-clock ceiling; any
    # straggler thread (already capped by LLM_FIXTURE_DEADLINE_S) finishes in
    # the background and its result is harmlessly discarded. The timeout on
    # as_completed enforces the budget even while we're blocked waiting for the
    # next fixture to land — not only when one happens to complete.
    ex = ThreadPoolExecutor(max_workers=LLM_MAX_PARALLEL)
    try:
        futs = {ex.submit(llm_mod.get_adjustment, h, a, ct, use_cache=False): (h, a, ct)
                for (h, a, ct) in misses}
        try:
            for fut in as_completed(futs, timeout=LLM_RUN_BUDGET_S):
                h, a, ct = futs[fut]
                try:
                    res = fut.result()  # already resolved by as_completed
                    results[(h, a)] = res
                    to_store.append((ct, h, a, res))
                except Exception:
                    pass  # this fixture errored → zero nudge downstream
        except FutTimeout:
            pass  # whole-run LLM budget spent → remaining fixtures use zero nudge
    finally:
        ex.shutdown(wait=False, cancel_futures=True)

    # Serial cache writes on the main thread (never inside the pool).
    for ct, h, a, res in to_store:
        try:
            llm_mod.cache_store_public(ct, h, a, res)
        except Exception:
            pass
    return results


def run_morning(run_date, dry_run=False, window_hours=None):
    """Scan fixtures, blend, find value, post only genuinely-new bets.

    window_hours set (scheduled run): scan upcoming, not-yet-started games within
    the window — each bet is dated by its own kickoff (UTC), so it grades against
    the right Results row. Otherwise: scan run_date's slate (manual/CLI).
    Returns a dict summary {matches, new_bets, card, sent}.
    """
    t_start = perf_counter()
    ratings = elo_mod.load_ratings()
    if window_hours is not None:
        matches = fixtures_mod.get_matches(window_hours=window_hours)
        scope = f"next {window_hours}h"
    else:
        matches = fixtures_mod.get_matches(target_date=run_date)
        scope = run_date
    t_fetch = perf_counter()
    print(f"[betsu] {len(matches)} match(es) for {scope}")

    # LLM context pre-pass: gather the nudge for every seeded fixture up front,
    # in parallel and under a whole-run wall-clock budget, so the per-match loop
    # below just reads a precomputed value. This is what keeps /run/morning under
    # the worker timeout with the layer ON — N fixtures cost ~one fixture's
    # latency, not N× (see docs/llm_keep_on_fix_briefing.md). The seeded gate
    # here mirrors the Elo/Poisson gate in the loop, so we never research a
    # fixture whose nudge won't be applied.
    llm_nudges = {}
    if LLM_ENABLED:
        seeded_for_llm = [
            (m["home_team"], m["away_team"], m.get("commence_time", ""))
            for m in matches
            if not [t for t in (m["home_team"], m["away_team"])
                    if not elo_mod.is_seeded(t, ratings)]
        ]
        if seeded_for_llm:
            llm_nudges = _gather_llm_nudges(seeded_for_llm)

    match_rows, candidates = [], []
    for m in matches:
        home, away = m["home_team"], m["away_team"]
        # In window mode a slate can straddle UTC midnight; date each game by its
        # own kickoff so grading lines up with the Results row.
        m_date = (m.get("commence_time") or "")[:10] if window_hours is not None else run_date
        m_date = m_date or run_date
        neutral = _neutral_and_host(home, away)

        # Market layer source: best-price-across-books de-vig by default. With
        # the sharp layer on and Pinnacle pricing this match, estimate the
        # market from Pinnacle's own de-vig instead — a single sharp book is the
        # textbook market estimate. The actual BET price still uses best-price-
        # across-books (m["odds"] -> find_value_bets below); estimating the
        # market from a sharp book while betting the best price is intentional.
        odds_for_blend = m["market_probs"]
        if SHARP_SOFT_MONITORING_ENABLED and m.get("sharp_market_probs"):
            odds_for_blend = m["sharp_market_probs"]
            print(f"  [sharp: using {fixtures_mod.SHARP_BOOKMAKER_KEY} line for {home} vs {away}]")

        preds = {"market": odds_for_blend}

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
            # Defence in depth: a Poisson failure drops that layer (and the
            # goal-based markets) for this match and the blend renormalises —
            # it must never take down a live run.
            try:
                poisson_mkts = poisson_mod.markets(home, away, ratings, neutral=neutral)
                preds["poisson"] = poisson_mkts["1x2"]
            except Exception as e:
                poisson_mkts = None
                print(f"  [poisson: skipped — {type(e).__name__}]")

            # xG layer (Expected Goals): optional 5% weight, fully fail-safe.
            # get_xg_prediction returns 1X2 from FBref team xG (via the Poisson
            # grid) or None — too few played matches, an unmapped team, or any
            # scrape/import error all yield None and the blend renormalises. The
            # guard is defence in depth; the layer must never take down a run.
            if XG_ENABLED:
                try:
                    from tools import xg as xg_mod
                    xg_prob = xg_mod.get_xg_prediction(home, away, ratings)
                    if xg_prob:
                        preds["xg"] = xg_prob
                        print(f"  [xg: {xg_prob}]")
                except Exception as e:
                    print(f"  [xg: skipped — {type(e).__name__}]")

            # LLM context nudge (1X2 only): same seeded gate as Elo/Poisson, and
            # only when explicitly enabled. The layer is fail-safe — a failure
            # returns a zero nudge, so the blend is unaffected.
            if LLM_ENABLED:
                # Read the precomputed nudge from the parallel pre-pass. A fixture
                # that missed the run budget is absent → zero nudge (no-op blend).
                ctx = llm_nudges.get((home, away))
                if ctx and any(v for v in ctx["nudge"].values()):
                    llm_adjust = ctx["nudge"]
                    src = (ctx.get("factors") or [{}])[0].get("source", "") \
                        or ctx.get("source", "")
                    context_note = ctx.get("summary") or "Context nudge applied."
                    if src:
                        context_note = f"{context_note} ({src})"
                    print(f"  [llm context: {ctx['nudge']} — {ctx.get('summary','')}]")

        blended = ensemble_mod.blend(preds, llm_adjust=llm_adjust)
        # Capture per-model 1X2 alongside the blend for a future model
        # leaderboard. `preds` carries market always, and elo/poisson only when
        # both teams are seeded; record_matches blanks any absent model.
        match_rows.append((m_date, home, away, blended, preds))

        # 1X2 value from the blended probabilities. When the sharp layer is on,
        # pass Pinnacle's de-vig so a best price far longer than the sharp line
        # is dropped as a polluted outlier (see docs/fix_inflated_odds_briefing.md).
        sharp_for_value = (m.get("sharp_market_probs")
                           if SHARP_SOFT_MONITORING_ENABLED else None)
        bets = value_mod.find_value_bets(m_date, home, away, blended, m["odds"],
                                         sharp_probs=sharp_for_value)
        # Over/Under 2.5 and BTTS value come from Poisson alone (the only layer
        # that produces goal-based probabilities) vs the book's totals/btts odds.
        if poisson_mkts:
            bets += value_mod.find_value_totals(
                m_date, home, away, poisson_mkts["ou"],
                m.get("totals_odds"), OU_LINE)
            # BTTS price isn't in the bulk fetch (additional market); resolve it
            # per event, cached + TTL-gated, only when enabled. find_value_btts
            # returns [] for None odds, so a missing price forces no bet.
            btts_odds = (_btts_odds_for(m.get("event_id"), dry_run=dry_run)
                         if BTTS_ENABLED else None)
            bets += value_mod.find_value_btts(
                m_date, home, away, poisson_mkts["btts"], btts_odds)

        for b in bets:
            b["commence_time"] = m.get("commence_time", "")
            if context_note:
                b["context_note"] = context_note
        candidates.extend(bets)
        print(f"  {home} vs {away}: blend={blended} -> {len(bets)} value bet(s)")

    t_blend = perf_counter()

    if dry_run:
        ranked = value_mod.rank_and_cap(candidates, MAX_BETS_PER_DAY)
        card = message_mod.build_daily_card(run_date, ranked, len(matches), None)
        print("\n----- CARD (dry run, not sent) -----\n")
        print(card)
        print(f"[betsu] timing: fetch={t_fetch - t_start:.1f}s "
              f"blend={t_blend - t_fetch:.1f}s sheets=0.0s(dry) "
              f"total={perf_counter() - t_start:.1f}s")
        return {"matches": len(matches), "new_bets": len(ranked),
                "card": card, "sent": False}

    # Record match-level probs (calibration), then post only the best NEW bets.
    tracker_mod.record_matches(match_rows)
    fresh = tracker_mod.filter_new(candidates)
    ranked = value_mod.rank_and_cap(fresh, MAX_BETS_PER_DAY)
    posted = tracker_mod.record_bets(ranked)
    record = tracker_mod.summary(write=True)
    card = message_mod.build_daily_card(run_date, posted, len(matches), record)
    t_sheets = perf_counter()

    if posted:
        from tools.telegram_send import send_message
        send_message(card)
    print(f"[betsu] {len(posted)} new bet(s) posted.")
    print(f"[betsu] timing: fetch={t_fetch - t_start:.1f}s "
          f"blend={t_blend - t_fetch:.1f}s sheets={t_sheets - t_blend:.1f}s "
          f"total={perf_counter() - t_start:.1f}s")
    return {"matches": len(matches), "new_bets": len(posted),
            "card": card, "sent": bool(posted)}


def run_grade(run_date):
    """Settle pending bets against the Results tab and post a recap.

    First (when enabled and a key is present) pull recent finished scores from
    football-data.org and write them under our store's team names, so grading
    settles without hand-typed scores. The sync is fail-safe — any outage logs
    and no-ops, and manual Results entries still grade.
    Returns a dict summary {settled, record, recap, synced}."""
    synced = None
    if AUTO_RESULTS_ENABLED and os.environ.get("FOOTBALL_DATA_API_KEY", "").strip():
        from tools import results_fetch
        # Reconcile against fixtures we actually track: pending bets (what needs
        # settling) plus the Matches tab (broader coverage).
        store_fixtures = tracker_mod.fetch_bets() + tracker_mod.fetch_matches()
        synced = results_fetch.sync_results(store_fixtures)
        print(f"[betsu] auto-results: synced {synced['synced']}, "
              f"skipped {synced['skipped_existing']} existing, "
              f"{len(synced['unmatched'])} unmatched, "
              f"{len(synced['conflicts'])} conflict(s).")

    settled = tracker_mod.grade_pending()
    record = tracker_mod.summary(write=True)
    recap = message_mod.build_results_recap(run_date, settled, record)
    from tools.telegram_send import send_message
    send_message(recap)
    print(f"[betsu] Graded {settled} bet(s).")
    return {"settled": settled, "record": record, "recap": recap, "synced": synced}


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
