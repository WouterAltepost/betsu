"""
results_fetch.py — pull finished World Cup scores from football-data.org and
write them into the Results tab, so grading settles without hand-typed scores.

The flow (called from run_daily.run_grade, before grade_pending):
  1. fetch_finished(date_from, date_to) — finished WC matches from football-data
  2. sync_results(store_fixtures)       — reconcile each finished match to one of
     our stored fixtures by fuzzy name match (date +/- 1 day), then record the
     score under the STORE's team names so the pending bets actually settle.

The one hard part is team-name reconciliation: bets are stored under
the-odds-api's names ("South Korea"), football-data uses its own ("Korea
Republic"). We resolve both through the same alias map + rapidfuzz threshold as
tools/elo.py and record under the store's names, never football-data's. A match
we can't confidently reconcile is skipped (never invented) and logged.

Everything here is fail-safe: any network/parse/auth error — or a competition
code the free tier won't serve — logs and returns 0, so a football-data outage
never blocks grading of results already in the sheet. Manual entry stays
authoritative: an existing score is never overwritten with a conflicting auto
value (the discrepancy is logged instead).

CLI:
    python tools/results_fetch.py            # print finished WC matches (last 3d)
    python tools/results_fetch.py 2026-06-11 2026-06-14
    python tools/results_fetch.py --sync     # reconcile + write to Results
"""

import os
import sys
import unicodedata
from datetime import date, datetime, timedelta, timezone

import requests
from dotenv import load_dotenv
from rapidfuzz import fuzz

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (AUTO_RESULTS_ENABLED, FOOTBALL_DATA_BASE,
                    FOOTBALL_DATA_COMPETITION, RESULTS_LOOKBACK_DAYS)
from tools import elo as elo_mod
from tools import tracker as tracker_mod

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
API_KEY = os.environ.get("FOOTBALL_DATA_API_KEY", "").strip()

# football-data.org's spellings that differ from our store (the-odds-api) names
# beyond what elo's ALIASES already covers — verified against the live WC feed's
# 48 teams. Resolved before the fuzzy fallback so a known variant never rides on
# a fuzzy score. (elo.ALIASES already maps "korea republic", "usa", "congo dr",
# "côte d'ivoire", etc.; these are the football-data-only extras.)
FOOTBALL_DATA_ALIASES = {
    "cape verde islands": "Cape Verde",
    "bosnia-herzegovina": "Bosnia and Herzegovina",
}
_ALIASES = {**elo_mod.ALIASES, **FOOTBALL_DATA_ALIASES}

# Reconciliation threshold, deliberately HIGHER than elo's seed-lookup threshold
# (85). At 85, distinct countries collide — Australia vs Austria scores 87.5, and
# both are at this World Cup, so a loose match would record one team's score under
# the other's fixture. Accent- and punctuation-only variants are handled by
# canonicalisation + explicit aliases, so fuzzy only needs to absorb minor
# spelling noise; 90 keeps Australia/Austria (and Iran/Iraq, Slovakia/Slovenia)
# apart while still matching genuine variants.
_THRESHOLD = 90


def _log(msg):
    print(f"[results_fetch] {msg}")


def _strip_accents(s):
    """Drop combining accents so 'Curaçao' and 'Curacao' compare equal."""
    return "".join(c for c in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(c))


def _canon(name):
    """Normalise a team name for comparison: trim, resolve a known alias to its
    canonical store spelling, then strip accents."""
    s = (name or "").strip()
    s = _ALIASES.get(s.lower(), s)
    return _strip_accents(s)


def _names_match(a, b):
    """True if two team names refer to the same team — exact (post-alias,
    accent-folded) or a fuzzy token-sort match at the reconciliation threshold."""
    ca, cb = _canon(a).lower(), _canon(b).lower()
    if ca == cb:
        return True
    return fuzz.token_sort_ratio(ca, cb) >= _THRESHOLD


def fetch_finished(date_from, date_to):
    """Finished WC matches from football-data between two YYYY-MM-DD dates.

    Returns a list of {utc_date, home, away, home_score, away_score}. Fully
    fail-safe: missing key, bad competition code, network/auth/parse error all
    log and return [] (never raise), so grading proceeds on whatever is already
    in the Results tab.
    """
    if not API_KEY:
        _log("no FOOTBALL_DATA_API_KEY — skipping auto-results (manual entry intact).")
        return []
    url = f"{FOOTBALL_DATA_BASE}/competitions/{FOOTBALL_DATA_COMPETITION}/matches"
    params = {"status": "FINISHED", "dateFrom": date_from, "dateTo": date_to}
    try:
        resp = requests.get(url, params=params,
                            headers={"X-Auth-Token": API_KEY}, timeout=30)
    except requests.RequestException as e:
        _log(f"network error reaching football-data ({e}) — skipping auto-results.")
        return []
    if resp.status_code in (403, 404):
        _log(f"football-data returned {resp.status_code} for competition "
             f"'{FOOTBALL_DATA_COMPETITION}' — the free tier may not serve it. "
             f"No-op; keep entering scores in the Results tab.")
        return []
    if resp.status_code != 200:
        _log(f"football-data HTTP {resp.status_code} — skipping auto-results.")
        return []
    try:
        matches = resp.json().get("matches", [])
    except ValueError:
        _log("football-data sent unparseable JSON — skipping auto-results.")
        return []

    out = []
    for m in matches:
        ft = (m.get("score") or {}).get("fullTime") or {}
        hs, as_ = ft.get("home"), ft.get("away")
        if hs is None or as_ is None:
            continue  # finished but no full-time score (shouldn't happen) — skip
        out.append({
            "utc_date": (m.get("utcDate") or "")[:10],
            "home": (m.get("homeTeam") or {}).get("name", ""),
            "away": (m.get("awayTeam") or {}).get("name", ""),
            "home_score": int(hs),
            "away_score": int(as_),
        })
    return out


def _within_window(fd_date, store_date, days=1):
    """True if two YYYY-MM-DD dates are within `days` of each other (covers the
    midnight-UTC boundary between the feed's date and our stored kickoff date)."""
    try:
        a = datetime.strptime(fd_date, "%Y-%m-%d").date()
        b = datetime.strptime(str(store_date)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return False
    return abs((a - b).days) <= days


def _reconcile(fd, store_fixtures):
    """Find the store fixture matching a finished football-data match `fd`.

    Matches on the unordered team pair (the venue is neutral, so home/away
    listing order can differ between feeds) within +/-1 day. Returns
    (fixture, home_score, away_score) with scores re-oriented to the store's
    home/away, or None if nothing matches confidently.
    """
    for fx in store_fixtures:
        s_home, s_away = fx.get("home_team", ""), fx.get("away_team", "")
        if not _within_window(fd["utc_date"], fx.get("match_date", "")):
            continue
        # Same orientation: fd home == store home, fd away == store away.
        if _names_match(fd["home"], s_home) and _names_match(fd["away"], s_away):
            return fx, fd["home_score"], fd["away_score"]
        # Flipped: the feeds disagree on who is "home" — swap the scores so they
        # line up with the store's ordering (otherwise the 1X2 outcome inverts).
        if _names_match(fd["home"], s_away) and _names_match(fd["away"], s_home):
            return fx, fd["away_score"], fd["home_score"]
    return None


def sync_results(store_fixtures, lookback_days=RESULTS_LOOKBACK_DAYS, today=None):
    """Pull recent finished WC matches and write each to the Results tab under
    the matching store fixture's team names, so the pending bets settle.

    store_fixtures: iterable of dicts with match_date/home_team/away_team
    (pending bets + the Matches tab). Returns a summary dict:
        {synced, skipped_existing, unmatched: [..], conflicts: [..]}
    Fully fail-safe — returns zeros on any failure rather than raising.
    """
    summary = {"synced": 0, "skipped_existing": 0, "unmatched": [], "conflicts": []}
    if not AUTO_RESULTS_ENABLED:
        _log("AUTO_RESULTS_ENABLED=0 — skipping auto-results (Results tab as-is).")
        return summary
    if not API_KEY:
        _log("no FOOTBALL_DATA_API_KEY — skipping auto-results (manual entry intact).")
        return summary

    today = today or datetime.now(timezone.utc).date()
    date_from = (today - timedelta(days=lookback_days)).isoformat()
    date_to = today.isoformat()
    finished = fetch_finished(date_from, date_to)
    if not finished:
        return summary

    store_fixtures = list(store_fixtures)
    # Existing results, keyed by store identity, so we never silently overwrite a
    # hand-typed score with a conflicting auto value.
    existing = {}
    try:
        for r in tracker_mod.fetch_results():
            k = (str(r.get("match_date", ""))[:10].strip(),
                 str(r.get("home_team", "")).strip(),
                 str(r.get("away_team", "")).strip())
            existing[k] = r
    except Exception as e:  # reading the store should never block syncing
        _log(f"could not read existing Results ({e}); proceeding without dedup.")

    for fd in finished:
        match = _reconcile(fd, store_fixtures)
        if not match:
            summary["unmatched"].append(f"{fd['home']} vs {fd['away']} ({fd['utc_date']})")
            continue
        fx, hs, as_ = match
        m_date = str(fx.get("match_date", ""))[:10].strip()
        home, away = fx.get("home_team", ""), fx.get("away_team", "")
        prior = existing.get((m_date, str(home).strip(), str(away).strip()))
        if prior is not None and prior.get("home_score") is not None:
            if prior["home_score"] == hs and prior["away_score"] == as_:
                summary["skipped_existing"] += 1  # already recorded, identical
            else:
                # Manual entry is authoritative: log, don't clobber.
                summary["conflicts"].append(
                    f"{home} {prior['home_score']}-{prior['away_score']} {away} "
                    f"(stored) vs {hs}-{as_} (football-data) — kept stored.")
                _log(f"score conflict for {home} vs {away} on {m_date}: stored "
                     f"{prior['home_score']}-{prior['away_score']}, football-data "
                     f"{hs}-{as_}. Keeping stored value.")
            continue
        try:
            tracker_mod.record_result(m_date, home, away, hs, as_)
            summary["synced"] += 1
            _log(f"recorded {home} {hs}-{as_} {away} ({m_date}) "
                 f"[football-data: {fd['home']} vs {fd['away']}]")
        except Exception as e:
            _log(f"failed to record {home} vs {away} ({e}); will retry next run.")

    if summary["unmatched"]:
        _log(f"{len(summary['unmatched'])} finished match(es) had no confident "
             f"store fixture: {'; '.join(summary['unmatched'])}")
    return summary


if __name__ == "__main__":
    if "--sync" in sys.argv:
        fixtures = tracker_mod.fetch_bets() + tracker_mod.fetch_matches()
        s = sync_results(fixtures)
        print(f"Synced {s['synced']}, skipped {s['skipped_existing']} existing, "
              f"{len(s['unmatched'])} unmatched, {len(s['conflicts'])} conflict(s).")
    else:
        args = [a for a in sys.argv[1:] if not a.startswith("--")]
        today = datetime.now(timezone.utc).date()
        d_from = args[0] if len(args) >= 1 else (today - timedelta(days=RESULTS_LOOKBACK_DAYS)).isoformat()
        d_to = args[1] if len(args) >= 2 else today.isoformat()
        for m in fetch_finished(d_from, d_to):
            print(f"{m['utc_date']}  {m['home']} {m['home_score']}-{m['away_score']} {m['away']}")
