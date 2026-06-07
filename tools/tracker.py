"""
tracker.py — SQLite store for predictions, suggested bets, and results.

Tables:
  matches   — every fixture we predicted (date, teams, our blended probs)
  bets      — every value bet we suggested (market, selection, odds, edge, stake)
  results   — final scores once known, used to grade bets

This is the source of truth for calibration and ROI. Grading is paper by
default; a `staked_real` flag lets you mark bets you actually placed.

CLI:
  python tools/tracker.py init           # create tables
  python tools/tracker.py summary        # print running record + ROI
"""

import os
import sqlite3
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATA_DIR, DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS matches (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    match_date  TEXT NOT NULL,
    home_team   TEXT NOT NULL,
    away_team   TEXT NOT NULL,
    p_home      REAL,
    p_draw      REAL,
    p_away      REAL,
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(match_date, home_team, away_team)
);

CREATE TABLE IF NOT EXISTS bets (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    match_date   TEXT NOT NULL,
    home_team    TEXT NOT NULL,
    away_team    TEXT NOT NULL,
    market       TEXT NOT NULL,        -- e.g. "1X2"
    selection    TEXT NOT NULL,        -- e.g. "1", "X", "2"
    model_prob   REAL NOT NULL,
    odds         REAL NOT NULL,        -- decimal odds offered
    edge         REAL NOT NULL,        -- model_prob * odds - 1
    stake_units  REAL NOT NULL,
    staked_real  INTEGER DEFAULT 0,    -- 1 if you placed real money
    result       TEXT DEFAULT 'pending', -- pending | win | loss | void
    pnl_units    REAL,                 -- settled profit/loss in units
    created_at   TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(match_date, home_team, away_team, market, selection)
);

CREATE TABLE IF NOT EXISTS results (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    match_date  TEXT NOT NULL,
    home_team   TEXT NOT NULL,
    away_team   TEXT NOT NULL,
    home_score  INTEGER,
    away_score  INTEGER,
    outcome     TEXT,                 -- "1" | "X" | "2"
    UNIQUE(match_date, home_team, away_team)
);
"""


def connect():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = connect()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def record_match(match_date, home, away, probs):
    conn = connect()
    conn.execute(
        """INSERT OR REPLACE INTO matches
           (match_date, home_team, away_team, p_home, p_draw, p_away)
           VALUES (?,?,?,?,?,?)""",
        (match_date, home, away, probs["1"], probs["X"], probs["2"]),
    )
    conn.commit()
    conn.close()


def record_bet(bet):
    """bet: dict with keys match_date, home_team, away_team, market, selection,
    model_prob, odds, edge, stake_units, staked_real(optional)."""
    conn = connect()
    conn.execute(
        """INSERT OR REPLACE INTO bets
           (match_date, home_team, away_team, market, selection,
            model_prob, odds, edge, stake_units, staked_real)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (bet["match_date"], bet["home_team"], bet["away_team"], bet["market"],
         bet["selection"], bet["model_prob"], bet["odds"], bet["edge"],
         bet["stake_units"], int(bet.get("staked_real", 0))),
    )
    conn.commit()
    conn.close()


def record_result(match_date, home, away, home_score, away_score):
    outcome = "1" if home_score > away_score else "2" if away_score > home_score else "X"
    conn = connect()
    conn.execute(
        """INSERT OR REPLACE INTO results
           (match_date, home_team, away_team, home_score, away_score, outcome)
           VALUES (?,?,?,?,?,?)""",
        (match_date, home, away, home_score, away_score, outcome),
    )
    conn.commit()
    conn.close()
    return outcome


def _bet_won(bet, res):
    """Decide whether a bet won given a results row.
    Returns True/False, or None if the market needs scores we don't have.
    Supports 1X2, OU<line> (e.g. OU2.5), and BTTS."""
    market, sel = bet["market"], bet["selection"]
    if market == "1X2":
        return sel == res["outcome"]

    hs, as_ = res["home_score"], res["away_score"]
    if hs is None or as_ is None:
        return None
    total = hs + as_

    if market.startswith("OU"):
        line = float(market[2:])           # "OU2.5" -> 2.5
        if sel == "Over":
            return total > line
        if sel == "Under":
            return total < line
        return None
    if market == "BTTS":
        both = hs >= 1 and as_ >= 1
        if sel == "Yes":
            return both
        if sel == "No":
            return not both
        return None
    return None


def grade_pending():
    """Settle pending bets against recorded results. Returns count settled."""
    conn = connect()
    rows = conn.execute("SELECT * FROM bets WHERE result = 'pending'").fetchall()
    settled = 0
    for b in rows:
        res = conn.execute(
            """SELECT outcome, home_score, away_score FROM results
               WHERE match_date=? AND home_team=? AND away_team=?""",
            (b["match_date"], b["home_team"], b["away_team"]),
        ).fetchone()
        if not res or res["outcome"] is None:
            continue
        won = _bet_won(b, res)
        if won is None:
            continue  # market needs scores we don't have yet
        result = "win" if won else "loss"
        pnl = b["stake_units"] * (b["odds"] - 1) if won else -b["stake_units"]
        conn.execute("UPDATE bets SET result=?, pnl_units=? WHERE id=?",
                     (result, round(pnl, 3), b["id"]))
        settled += 1
    conn.commit()
    conn.close()
    return settled


def summary():
    conn = connect()
    rows = conn.execute(
        "SELECT result, COUNT(*) n, COALESCE(SUM(pnl_units),0) pnl "
        "FROM bets GROUP BY result").fetchall()
    conn.close()
    stats = {r["result"]: (r["n"], r["pnl"]) for r in rows}
    wins = stats.get("win", (0, 0))[0]
    losses = stats.get("loss", (0, 0))[0]
    pending = stats.get("pending", (0, 0))[0]
    total_settled = wins + losses
    total_pnl = sum(v[1] for k, v in stats.items() if k in ("win", "loss"))
    staked = total_settled  # 1 unit flat
    roi = (total_pnl / staked * 100) if staked else 0.0
    hit = (wins / total_settled * 100) if total_settled else 0.0
    return {
        "settled": total_settled, "wins": wins, "losses": losses,
        "pending": pending, "hit_rate": round(hit, 1),
        "pnl_units": round(total_pnl, 2), "roi_pct": round(roi, 1),
    }


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "summary"
    if cmd == "init":
        init_db()
        print(f"Initialised {DB_PATH}")
    elif cmd == "summary":
        init_db()
        s = summary()
        print(f"Settled: {s['settled']}  W:{s['wins']} L:{s['losses']}  "
              f"Pending:{s['pending']}")
        print(f"Hit rate: {s['hit_rate']}%   P&L: {s['pnl_units']:+} units   "
              f"ROI: {s['roi_pct']:+}%")
