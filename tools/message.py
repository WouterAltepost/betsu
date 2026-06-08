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


def euro_stake_guide(kelly_units, bankroll=BANKROLL_EUR):
    """€ quarter-Kelly stake guide from the bet's Kelly fraction of bankroll,
    rounded to the nearest €5 with a €10 floor (matches the dashboard's suggested
    stake). A guide only — the real stake is the user's choice."""
    raw = round((kelly_units or 0.0) * bankroll / 5) * 5
    return max(10, int(raw))


def _fmt_bet(b, i):
    sel = b.get("selection_label") or LABEL.get(b["selection"], b["selection"])
    lines = [
        f"<b>{i}. {b['home_team']} vs {b['away_team']}</b>",
        f"   Pick: <b>{sel}</b>  @ <b>{b['odds']:.2f}</b>",
        f"   Model {b['model_prob']*100:.0f}% vs market {b['implied_prob']*100:.0f}%  "
        f"→ edge <b>{b['edge']*100:+.1f}%</b>",
        f"   Stake guide: <b>€{euro_stake_guide(b.get('kelly_units'))}</b> (¼-Kelly)",
    ]
    if b.get("context_note"):
        lines.append(f"   <i>Context: {b['context_note']}</i>")
    return "\n".join(lines)


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
    """bets: ranked value bets. record: optional tracker.summary() dict."""
    lines = [f"⚽ <b>betsu — {run_date}</b>",
             f"{n_matches} match(es) scanned · {len(bets)} value bet(s)\n"]
    if not bets:
        lines.append("No value bets clear the edge threshold today. Sitting out.")
    else:
        lines += [_fmt_bet(b, i) for i, b in enumerate(bets, 1)]
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
    bets = [{
        "home_team": "Argentina", "away_team": "Mexico", "selection": "1",
        "selection_label": "Home (Argentina)", "model_prob": 0.62,
        "implied_prob": 0.51, "odds": 1.95, "edge": 0.209,
        "stake_units": 1.0, "kelly_units": 0.05,
    }]
    rec = {"settled": 10, "wins": 6, "losses": 4, "hit_rate": 60.0,
           "pnl_units": 1.8, "roi_pct": 18.0,
           "real": {"placed": 8, "settled": 7, "wins": 4, "losses": 3,
                    "hit_rate": 57.1, "pnl_eur": 42.0, "roi_eur_pct": 11.5}}
    print(build_daily_card("2026-06-11", bets, 4, rec))
    print("\n---\n")
    print(build_results_recap("2026-06-11", 3, rec))
