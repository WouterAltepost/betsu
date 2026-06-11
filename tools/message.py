"""
message.py — format the daily bet card and results recap for Telegram (HTML).
Pure string building, no network — easy to unit-test.

User-facing money is euros: the morning card shows a € quarter-Kelly stake guide
(the user places real bets and tracks them on the dashboard), and the running
line / results recap report real-€ P&L on placed bets. The model/paper units
track stays internal (calibration + the benchmark betsu is judged on).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import BANKROLL_EUR

LABEL = {"1": "Home win", "X": "Draw", "2": "Away win"}

# World Cup nations → (ISO-3166 alpha-2 for the flag emoji, short FIFA-style code
# for the context prefix). WC 2026 is 48 teams; this covers the likely field, with
# a graceful fallback (no flag, first-3-letters code) for anything unmapped. Keys
# are lower-cased team names; aliases point at the same tuple.
_NATION = {
    "argentina": ("AR", "ARG"), "brazil": ("BR", "BRA"), "france": ("FR", "FRA"),
    "spain": ("ES", "ESP"), "germany": ("DE", "GER"), "portugal": ("PT", "POR"),
    "netherlands": ("NL", "NED"), "belgium": ("BE", "BEL"), "croatia": ("HR", "CRO"),
    "italy": ("IT", "ITA"), "uruguay": ("UY", "URU"), "colombia": ("CO", "COL"),
    "mexico": ("MX", "MEX"), "usa": ("US", "USA"), "united states": ("US", "USA"),
    "canada": ("CA", "CAN"), "japan": ("JP", "JPN"), "south korea": ("KR", "KOR"),
    "korea republic": ("KR", "KOR"), "australia": ("AU", "AUS"),
    "morocco": ("MA", "MAR"), "senegal": ("SN", "SEN"), "ghana": ("GH", "GHA"),
    "nigeria": ("NG", "NGA"), "cameroon": ("CM", "CMR"), "ivory coast": ("CI", "CIV"),
    "egypt": ("EG", "EGY"), "tunisia": ("TN", "TUN"), "algeria": ("DZ", "ALG"),
    "south africa": ("ZA", "RSA"), "saudi arabia": ("SA", "KSA"), "iran": ("IR", "IRN"),
    "qatar": ("QA", "QAT"), "ecuador": ("EC", "ECU"), "peru": ("PE", "PER"),
    "chile": ("CL", "CHI"), "paraguay": ("PY", "PAR"), "venezuela": ("VE", "VEN"),
    "costa rica": ("CR", "CRC"), "panama": ("PA", "PAN"), "switzerland": ("CH", "SUI"),
    "denmark": ("DK", "DEN"), "sweden": ("SE", "SWE"), "norway": ("NO", "NOR"),
    "poland": ("PL", "POL"), "serbia": ("RS", "SRB"), "czech republic": ("CZ", "CZE"),
    "austria": ("AT", "AUT"), "turkey": ("TR", "TUR"), "ukraine": ("UA", "UKR"),
    "greece": ("GR", "GRE"), "new zealand": ("NZ", "NZL"), "jamaica": ("JM", "JAM"),
    "honduras": ("HN", "HON"), "jordan": ("JO", "JOR"), "uzbekistan": ("UZ", "UZB"),
    "iraq": ("IQ", "IRQ"), "scotland": (None, "SCO"), "wales": (None, "WAL"),
    "england": (None, "ENG"),
}
# Subdivision flags that aren't simple ISO-2 regional-indicator pairs.
_SPECIAL_FLAG = {
    "england": "\U0001F3F4\U000E0067\U000E0062\U000E0065\U000E006E\U000E0067\U000E007F",
    "scotland": "\U0001F3F4\U000E0067\U000E0062\U000E0073\U000E0063\U000E0074\U000E007F",
    "wales": "\U0001F3F4\U000E0067\U000E0062\U000E0077\U000E006C\U000E0073\U000E007F",
}


def _nation(team):
    """(iso2, short_code) for a team name, with a graceful fallback."""
    return _NATION.get((team or "").strip().lower(),
                        (None, (team or "???")[:3].upper()))


def _flag(team):
    """Flag emoji for a team name, or '⚽' when unknown."""
    key = (team or "").strip().lower()
    if key in _SPECIAL_FLAG:
        return _SPECIAL_FLAG[key]
    iso2, _ = _nation(team)
    if not iso2:
        return "⚽"
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in iso2)


def _team_code(team):
    return _nation(team)[1]


def euro_stake_guide(kelly_units, bankroll=BANKROLL_EUR):
    """€ quarter-Kelly stake guide from the bet's Kelly fraction of bankroll,
    rounded to the nearest €5 with a €10 floor (matches the dashboard's suggested
    stake). A guide only — the real stake is the user's choice."""
    raw = round((kelly_units or 0.0) * bankroll / 5) * 5
    return max(10, int(raw))


def _fmt_bet_line(b):
    """One compact pick line:
        Home (SK) @ 2.82 | 39% → +11.1% edge | €15"""
    sel = b.get("selection_label") or LABEL.get(b["selection"], b["selection"])
    return (f"  {sel} @ {b['odds']:.2f} | {b['model_prob']:.0%} → "
            f"{b['edge']:+.1%} edge | €{euro_stake_guide(b.get('kelly_units'))}")


def _fmt_match_group(match):
    """A match heading (flag + all-caps name) followed by its compact pick lines."""
    home = match["bets"][0]["home_team"]
    lines = [f"{_flag(home)} <b>{match['name']}</b>"]
    lines += [_fmt_bet_line(b) for b in match["bets"]]
    return "\n".join(lines)


def _fmt_context_line(home, bets):
    """One de-duplicated context line for a match, prefixed by the home team's
    short code, e.g. 'KOR: Altitude acclimatization (https://...)'. Returns None
    when none of the match's picks carry a context note."""
    seen, notes = set(), []
    for b in bets:
        note = (b.get("context_note") or "").strip()
        if not note or note in seen:
            continue
        seen.add(note)
        url = (b.get("context_url") or "").strip()
        notes.append(f"{note} ({url})" if url else note)
    if not notes:
        return None
    return f"{_team_code(home)}: {'; '.join(notes)}"


def _real_record_line(record):
    """One-line real-€ running record from summary()'s 'real' block, or None when
    there's nothing settled yet."""
    real = (record or {}).get("real") or {}
    if real.get("settled", 0) > 0:
        return (f"\n📊 Running (your money): {real['wins']}-{real['losses']} "
                f"({real['hit_rate']:.0f}%) · {real['pnl_eur']:+.0f}€ · "
                f"ROI {real['roi_eur_pct']:+.1f}%")
    return None


def build_daily_card(run_date, bets, n_matches, record=None):
    """bets: ranked value bets. record: optional tracker.summary() dict.

    Bets are grouped by match: each match shows a flagged heading and its compact
    pick lines, then a de-duplicated context section, keeping the whole card
    scannable at a glance. Match order follows the ranked-bet order (best edge
    first)."""
    lines = [f"⚽ <b>betsu — {run_date}</b> | {len(bets)} value bet(s)\n"]
    if not bets:
        lines.append("No value bets clear the edge threshold today. Sitting out.")
        lines.append("\n<i>Bet responsibly.</i>")
        return "\n".join(lines)

    # Group bets by match, preserving first-seen (ranked) order.
    matches = {}
    for b in bets:
        key = (b["home_team"], b["away_team"])
        if key not in matches:
            matches[key] = {
                "name": f"{b['home_team'].upper()} vs {b['away_team'].upper()}",
                "bets": [],
            }
        matches[key]["bets"].append(b)

    lines.append("\n\n".join(_fmt_match_group(m) for m in matches.values()))

    context_lines = [_fmt_context_line(home, m["bets"])
                     for (home, _away), m in matches.items()]
    context_lines = [c for c in context_lines if c]
    if context_lines:
        lines.append("\n" + "\n".join(context_lines))

    record_line = _real_record_line(record)
    if record_line:
        lines.append(record_line)
    lines.append("\n<i>Stakes are a ¼-Kelly guide, bet what you choose. "
                 "Bet responsibly.</i>")
    return "\n".join(lines)


def build_results_recap(run_date, settled, record):
    real = (record or {}).get("real") or {}
    lines = [f"📋 <b>betsu results — {run_date}</b>",
             f"Settled {settled} bet(s) today.\n"]
    if real.get("settled", 0) > 0:
        lines += [f"Your money: {real['wins']}-{real['losses']} "
                  f"({real['hit_rate']:.0f}%)",
                  f"P&L: {real['pnl_eur']:+.0f}€ · ROI {real['roi_eur_pct']:+.1f}%"]
    else:
        lines.append("No settled placed bets yet. Tick the bets you backed on "
                     "the dashboard to track real P&L.")
    return "\n".join(lines)


if __name__ == "__main__":
    bets = [
        {"home_team": "South Korea", "away_team": "Czech Republic", "selection": "1",
         "selection_label": "Home (KOR)", "model_prob": 0.39, "implied_prob": 0.355,
         "odds": 2.82, "edge": 0.111, "kelly_units": 0.08,
         "context_note": "Altitude acclimatization"},
        {"home_team": "South Korea", "away_team": "Czech Republic", "selection": "O2.5",
         "selection_label": "Over 2.5", "model_prob": 0.48, "implied_prob": 0.435,
         "odds": 2.30, "edge": 0.108, "kelly_units": 0.10,
         "context_note": "Altitude acclimatization"},
        {"home_team": "Mexico", "away_team": "South Africa", "selection": "1",
         "selection_label": "Home (MEX)", "model_prob": 0.75, "implied_prob": 0.68,
         "odds": 1.47, "edge": 0.102, "kelly_units": 0.28,
         "context_note": "Altitude + RSA lineup gaps"},
        {"home_team": "Mexico", "away_team": "South Africa", "selection": "O2.5",
         "selection_label": "Over 2.5", "model_prob": 0.48, "implied_prob": 0.444,
         "odds": 2.25, "edge": 0.084, "kelly_units": 0.08,
         "context_note": "Altitude + RSA lineup gaps"},
        {"home_team": "Mexico", "away_team": "South Africa", "selection": "BTTS_N",
         "selection_label": "BTTS No", "model_prob": 0.66, "implied_prob": 0.625,
         "odds": 1.60, "edge": 0.051, "kelly_units": 0.10,
         "context_note": "Altitude + RSA lineup gaps"},
    ]
    rec = {"settled": 10, "wins": 6, "losses": 4, "hit_rate": 60.0,
           "pnl_units": 1.8, "roi_pct": 18.0,
           "real": {"placed": 8, "settled": 7, "wins": 4, "losses": 3,
                    "hit_rate": 57.1, "pnl_eur": 42.0, "roi_eur_pct": 11.5}}
    print(build_daily_card("2026-06-11", bets, 2, rec))
    print("\n---\n")
    print(build_results_recap("2026-06-11", 3, rec))
