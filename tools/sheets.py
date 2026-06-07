"""
sheets.py — optional Google Sheets mirror of the SQLite tracker.

SQLite stays the source of truth. After each run we rewrite three tabs of a
Google Sheet from the current DB state, so you can watch performance from
anywhere (phone included) and once betsu is deployed on Railway:

    Bets      — every suggested bet, with result + P&L once graded
    Results   — final scores we've recorded
    Summary   — running record, hit rate, P&L, ROI, last updated

Design choices:
  - Rewriting whole tabs from the DB each run is idempotent and avoids any
    dedup/ordering bugs; the volume (a few hundred bets over a tournament) is
    trivial for the Sheets API.
  - The whole module is OPTIONAL and FAIL-SAFE. It activates only when
    GOOGLE_SHEETS_ID is set in .env and the credentials file exists. gspread is
    imported lazily, so betsu runs fine even if the package isn't installed.
    Callers wrap sync_all() in try/except so a Sheets hiccup never blocks the
    Telegram card or grading.

Auth: a Google Cloud *service account*. Share the target sheet with the service
account's email (Editor). See docs/google_sheets_setup.md for the one-time setup.

CLI:
    python tools/sheets.py status     # show whether sync is configured
    python tools/sheets.py sync       # push current DB state to the sheet
"""

import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (SHEETS_CREDENTIALS_DEFAULT, SHEETS_TAB_BETS,
                    SHEETS_TAB_RESULTS, SHEETS_TAB_SUMMARY)
from tools import tracker as tracker_mod

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

SHEET_ID = os.environ.get("GOOGLE_SHEETS_ID", "").strip()
CREDENTIALS_PATH = os.environ.get("GOOGLE_CREDENTIALS_PATH", SHEETS_CREDENTIALS_DEFAULT)

BETS_HEADERS = ["match_date", "home_team", "away_team", "market", "selection",
                "model_prob", "odds", "edge", "stake_units", "staked_real",
                "result", "pnl_units", "created_at"]
RESULTS_HEADERS = ["match_date", "home_team", "away_team",
                   "home_score", "away_score", "outcome"]


def enabled():
    """True only when a sheet id is configured and the key file exists."""
    return bool(SHEET_ID) and os.path.exists(CREDENTIALS_PATH)


def status():
    """Human-readable config check (no network)."""
    if not SHEET_ID:
        return "Sheets sync OFF — GOOGLE_SHEETS_ID is not set in .env."
    if not os.path.exists(CREDENTIALS_PATH):
        return f"Sheets sync OFF — credentials file not found at {CREDENTIALS_PATH}."
    return f"Sheets sync ON — sheet {SHEET_ID}, key {CREDENTIALS_PATH}."


def _open_spreadsheet():
    """Authorise via the service account and open the configured sheet."""
    import gspread  # lazy: betsu runs without the package when sync is off
    gc = gspread.service_account(filename=CREDENTIALS_PATH)
    return gc.open_by_key(SHEET_ID)


def _ensure_tab(ss, title, n_cols):
    try:
        return ss.worksheet(title)
    except Exception:
        return ss.add_worksheet(title=title, rows=100, cols=max(n_cols, 6))


def _write_table(ws, headers, rows):
    """Clear a worksheet and write headers + rows in one batched update."""
    ws.clear()
    data = [headers] + [[("" if v is None else v) for v in r] for r in rows]
    ws.update(range_name="A1", values=data, value_input_option="RAW")


def sync_all():
    """Rewrite all three tabs from the current SQLite state. Returns a note."""
    if not enabled():
        return status()

    ss = _open_spreadsheet()

    bets = tracker_mod.fetch_bets()
    _write_table(_ensure_tab(ss, SHEETS_TAB_BETS, len(BETS_HEADERS)),
                 BETS_HEADERS, [[b.get(h) for h in BETS_HEADERS] for b in bets])

    results = tracker_mod.fetch_results()
    _write_table(_ensure_tab(ss, SHEETS_TAB_RESULTS, len(RESULTS_HEADERS)),
                 RESULTS_HEADERS, [[r.get(h) for h in RESULTS_HEADERS] for r in results])

    s = tracker_mod.summary()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    summary_rows = [
        ["metric", "value"],
        ["last_updated", now],
        ["settled", s["settled"]],
        ["wins", s["wins"]],
        ["losses", s["losses"]],
        ["pending", s["pending"]],
        ["hit_rate_pct", s["hit_rate"]],
        ["pnl_units", s["pnl_units"]],
        ["roi_pct", s["roi_pct"]],
    ]
    sum_ws = _ensure_tab(ss, SHEETS_TAB_SUMMARY, 2)
    sum_ws.clear()
    sum_ws.update(range_name="A1", values=summary_rows, value_input_option="RAW")

    return f"Synced {len(bets)} bet(s), {len(results)} result(s) to Google Sheets."


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        print(status())
    elif cmd == "sync":
        tracker_mod.init_db()
        print(sync_all())
    else:
        print("usage: python tools/sheets.py [status|sync]")
