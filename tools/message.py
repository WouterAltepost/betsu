"""
message.py — format the daily bet card and results recap for Telegram (HTML).
Pure string building, no network — easy to unit-test.
"""

LABEL = {"1": "Home win", "X": "Draw", "2": "Away win"}


def _fmt_bet(b, i):
    sel = b.get("selection_label") or LABEL.get(b["selection"], b["selection"])
    return (
        f"<b>{i}. {b['home_team']} vs {b['away_team']}</b>\n"
        f"   Pick: <b>{sel}</b>  @ <b>{b['odds']:.2f}</b>\n"
        f"   Model {b['model_prob']*100:.0f}% vs market {b['implied_prob']*100:.0f}%  "
        f"→ edge <b>{b['edge']*100:+.1f}%</b>\n"
        f"   Stake: {b['stake_units']:.0f}u (¼-Kelly guide {b['kelly_units']:.2f})"
    )


def build_daily_card(run_date, bets, n_matches, record=None):
    """bets: ranked value bets. record: optional tracker.summary() dict."""
    lines = [f"⚽ <b>betsu — {run_date}</b>",
             f"{n_matches} match(es) scanned · {len(bets)} value bet(s)\n"]
    if not bets:
        lines.append("No value bets clear the edge threshold today. Sitting out.")
    else:
        lines += [_fmt_bet(b, i) for i, b in enumerate(bets, 1)]
    if record and record.get("settled", 0) > 0:
        lines.append(
            f"\n📊 Running: {record['wins']}-{record['losses']} "
            f"({record['hit_rate']:.0f}%) · {record['pnl_units']:+.1f}u · "
            f"ROI {record['roi_pct']:+.1f}%")
    lines.append("\n<i>Paper unless you choose to back it. Bet responsibly.</i>")
    return "\n".join(lines)


def build_results_recap(run_date, settled, record):
    lines = [f"📋 <b>betsu results — {run_date}</b>",
             f"Settled {settled} bet(s) today.\n",
             f"Record: {record['wins']}-{record['losses']} "
             f"({record['hit_rate']:.0f}%)",
             f"P&L: {record['pnl_units']:+.1f}u · ROI {record['roi_pct']:+.1f}%"]
    return "\n".join(lines)


if __name__ == "__main__":
    bets = [{
        "home_team": "Argentina", "away_team": "Mexico", "selection": "1",
        "selection_label": "Home (Argentina)", "model_prob": 0.62,
        "implied_prob": 0.51, "odds": 1.95, "edge": 0.209,
        "stake_units": 1.0, "kelly_units": 0.05,
    }]
    rec = {"settled": 10, "wins": 6, "losses": 4, "hit_rate": 60.0,
           "pnl_units": 1.8, "roi_pct": 18.0}
    print(build_daily_card("2026-06-11", bets, 4, rec))
