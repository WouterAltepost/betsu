"""
fixtures.py — fetch today's fixtures and bookmaker odds from the-odds-api (v4).

One call returns events with odds, so fixtures and odds come together.
For each match we compute:
  - best decimal odds per outcome (1/X/2) across all bookmakers
  - de-vigged market-implied probabilities (the "market" predictor)

Docs: https://the-odds-api.com/liveapi/guides/v4/

CLI:
  python tools/fixtures.py                 # today, default sport
  python tools/fixtures.py --date=2026-06-11
  python tools/fixtures.py --sports        # list available soccer sport keys
"""

import os
import sys
from datetime import datetime, date, timedelta, timezone

import requests
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (ODDS_API_BASE, ODDS_REGION, ODDS_MARKETS,
                    ODDS_SPORT_WORLDCUP, OU_LINE)

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
API_KEY = os.environ.get("ODDS_API_KEY")


def _require_key():
    if not API_KEY:
        raise RuntimeError("ODDS_API_KEY not set in .env — get a free key at the-odds-api.com")


def list_soccer_sports():
    """Return active sport keys that look like soccer (for picking the WC key)."""
    _require_key()
    url = f"{ODDS_API_BASE}/sports"
    resp = requests.get(url, params={"apiKey": API_KEY}, timeout=30)
    resp.raise_for_status()
    return [s for s in resp.json() if s.get("group", "").lower() == "soccer"]


def _devig(odds_1x2):
    """De-vig decimal odds into probabilities that sum to 1."""
    raw = {o: (1.0 / odds_1x2[o]) for o in odds_1x2 if odds_1x2.get(o)}
    total = sum(raw.values())
    if total <= 0:
        return None
    return {o: round(raw[o] / total, 4) for o in raw}


def _best_odds(event):
    """Best (highest) decimal odds per outcome across all bookmakers."""
    home, away = event["home_team"], event["away_team"]
    best = {}
    for bk in event.get("bookmakers", []):
        for market in bk.get("markets", []):
            if market["key"] != "h2h":
                continue
            for oc in market["outcomes"]:
                name, price = oc["name"], oc["price"]
                if name == home:
                    key = "1"
                elif name == away:
                    key = "2"
                elif name.lower() == "draw":
                    key = "X"
                else:
                    continue
                if key not in best or price > best[key]:
                    best[key] = price
    return best


def _best_totals(event, line=OU_LINE):
    """Best decimal odds for Over/Under at the given line across all books.
    Returns {"Over": odds, "Under": odds} or {} if the line isn't offered."""
    best = {}
    for bk in event.get("bookmakers", []):
        for market in bk.get("markets", []):
            if market["key"] != "totals":
                continue
            for oc in market["outcomes"]:
                if oc.get("point") != line:
                    continue
                name, price = oc["name"], oc["price"]  # "Over" / "Under"
                if name in ("Over", "Under") and (name not in best or price > best[name]):
                    best[name] = price
    return best


def _best_btts(event):
    """Best decimal odds for both-teams-to-score Yes/No across all books.
    Returns {"Yes": odds, "No": odds} or {} if not offered."""
    best = {}
    for bk in event.get("bookmakers", []):
        for market in bk.get("markets", []):
            if market["key"] != "btts":
                continue
            for oc in market["outcomes"]:
                name, price = oc["name"], oc["price"]  # "Yes" / "No"
                if name in ("Yes", "No") and (name not in best or price > best[name]):
                    best[name] = price
    return best


def _parse_iso(ts):
    """Parse an ISO-8601 commence_time (the-odds-api uses '...Z') to aware UTC."""
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def get_matches(target_date=None, sport=ODDS_SPORT_WORLDCUP, region=ODDS_REGION,
                window_hours=None):
    """
    Return a list of match dicts:
      {home_team, away_team, commence_time, odds:{"1","X","2"}, market_probs:{...},
       totals_odds, btts_odds}
    Matches with incomplete 1X2 odds are skipped.

    Selection mode:
      - window_hours set: upcoming events that have NOT kicked off and start
        within now .. now + window_hours (used by the scheduled run; spans a
        whole afternoon→late-night slate so nothing is missed).
      - otherwise: events on target_date (UTC date, default today) — kept for
        manual/CLI use.
    """
    _require_key()
    target = target_date or str(date.today())
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(hours=window_hours) if window_hours is not None else None

    url = f"{ODDS_API_BASE}/sports/{sport}/odds"
    params = {
        "apiKey": API_KEY,
        "regions": region,
        "markets": ODDS_MARKETS,
        "oddsFormat": "decimal",
        "dateFormat": "iso",
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    events = resp.json()

    matches = []
    for ev in events:
        commence = ev.get("commence_time")
        if window_hours is not None:
            kickoff = _parse_iso(commence)
            if kickoff is None or kickoff < now or kickoff > horizon:
                continue  # already started, too far out, or unparseable
        else:
            ev_date = commence[:10] if commence else None  # ISO date (UTC)
            if ev_date != target:
                continue
        odds = _best_odds(ev)
        if not all(k in odds for k in ("1", "X", "2")):
            continue  # need full 1X2 to value a bet
        totals = _best_totals(ev)        # {} when the 2.5 line isn't offered
        btts = _best_btts(ev)            # {} when btts isn't offered
        matches.append({
            "home_team": ev["home_team"],
            "away_team": ev["away_team"],
            "commence_time": commence,
            "odds": odds,
            "market_probs": _devig(odds),
            "totals_odds": totals if {"Over", "Under"} <= set(totals) else None,
            "btts_odds": btts if {"Yes", "No"} <= set(btts) else None,
        })
    return matches


if __name__ == "__main__":
    if "--sports" in sys.argv:
        for s in list_soccer_sports():
            print(f"{s['key']:35} active={s.get('active')}  {s['title']}")
        sys.exit(0)
    date_arg = next((a.split("=")[1] for a in sys.argv if a.startswith("--date=")), None)
    win_arg = next((int(a.split("=")[1]) for a in sys.argv if a.startswith("--window=")), None)
    ms = get_matches(target_date=date_arg, window_hours=win_arg)
    scope = f"next {win_arg}h" if win_arg is not None else (date_arg or "today")
    print(f"{len(ms)} match(es) for {scope}")
    for m in ms:
        print(f"  {m['home_team']} vs {m['away_team']}  odds={m['odds']}  "
              f"mkt={m['market_probs']}")
        if m.get("totals_odds"):
            print(f"      O/U {OU_LINE}: {m['totals_odds']}")
        if m.get("btts_odds"):
            print(f"      BTTS: {m['btts_odds']}")
