"""
Offline tests for the placed-bet (real-money) track added to tracker.py.

Covers the pure helpers (effective_result, _pnl_eur, _real_summary) and the two
Sheets writers (update_bet_user_fields, grade_pending) with the worksheet layer
stubbed — so these run with no network and no Google credentials.

Run:  python -m pytest tests/test_tracker_user_fields.py
  or:  python tests/test_tracker_user_fields.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools import tracker  # noqa: E402

H = tracker.BETS_HEADERS


def _row(**over):
    """A bet row dict with sane defaults; override any field by name."""
    base = {h: "" for h in H}
    base.update({
        "match_date": "2026-06-16", "home_team": "Argentina",
        "away_team": "Mexico", "market": "1X2", "selection": "1",
        "selection_label": "Home (Argentina)", "odds": "2.00",
        "edge": "0.10", "stake_units": "1", "result": "pending",
    })
    base.update(over)
    return base


def _matrix(rows):
    """Header row + data rows (list-of-lists), as get_all_values would return."""
    return [list(H)] + [[d.get(h, "") for h in H] for d in rows]


class FakeWS:
    def __init__(self):
        self.updates = []      # (range_name, values)
        self.batch = []        # accumulated batch_update entries

    def update(self, range_name=None, values=None, value_input_option=None):
        self.updates.append((range_name, values))

    def batch_update(self, updates, value_input_option=None):
        self.batch.extend(updates)

    def append_rows(self, rows, value_input_option=None):
        self.updates.append(("append", rows))


# --- effective_result -------------------------------------------------------

def test_effective_result():
    assert tracker.effective_result({}) == "pending"
    assert tracker.effective_result({"result": "win"}) == "win"
    assert tracker.effective_result({"result": "pending"}) == "pending"
    # manual override wins over the auto result
    assert tracker.effective_result({"result": "win", "manual_result": "loss"}) == "loss"
    assert tracker.effective_result({"manual_result": "win"}) == "win"


# --- _pnl_eur ---------------------------------------------------------------

def test_pnl_eur():
    # unplaced -> always model-track only
    assert tracker._pnl_eur(_row(result="win", staked_real="50")) == ""
    # placed win: stake * (odds - 1)
    assert tracker._pnl_eur(_row(placed="1", result="win", staked_real="50",
                                 odds="2.00")) == "50.0"
    # placed loss: -stake
    assert tracker._pnl_eur(_row(placed="1", result="loss", staked_real="50",
                                 odds="2.00")) == "-50"
    # manual override decides the euro outcome
    assert tracker._pnl_eur(_row(placed="1", result="win", manual_result="loss",
                                 staked_real="50", odds="2.00")) == "-50"
    # placed but unsettled, or zero stake -> empty
    assert tracker._pnl_eur(_row(placed="1", result="pending", staked_real="50")) == ""
    assert tracker._pnl_eur(_row(placed="1", result="win", staked_real="0",
                                 odds="2.00")) == ""


# --- update_bet_user_fields -------------------------------------------------

def _patch_bets(monkeypatch, ws, rows):
    monkeypatch.setattr(tracker, "_values",
                        lambda title, headers: (ws, _matrix(rows)))
    monkeypatch.setattr(tracker, "_cache_clear", lambda: None)


def test_update_bet_user_fields_places_and_prices(monkeypatch):
    ws = FakeWS()
    # an already-settled (won) suggestion that the user now marks placed @ €50
    rows = [_row(result="win", odds="2.00")]
    _patch_bets(monkeypatch, ws, rows)

    key = {"match_date": "2026-06-16", "home_team": "Argentina",
           "away_team": "Mexico", "market": "1X2", "selection": "1"}
    out = tracker.update_bet_user_fields(key, placed=True, stake_eur=50)

    assert out is not False
    assert out["placed"] == "1"
    assert out["staked_real"] == 50
    assert out["pnl_eur"] == 50.0          # 50 * (2.00 - 1)
    # one full-row write was issued
    assert len(ws.updates) == 1
    rng, vals = ws.updates[0]
    assert rng.startswith("A2:")
    written = dict(zip(H, vals[0]))
    assert written["placed"] == "1"
    assert written["staked_real"] == "50"
    assert written["pnl_eur"] == "50.0"
    # the model track is untouched
    assert written["result"] == "win"


def test_update_bet_user_fields_manual_override(monkeypatch):
    ws = FakeWS()
    rows = [_row(placed="1", staked_real="50", result="win", odds="2.00",
                 pnl_eur="50.0")]
    _patch_bets(monkeypatch, ws, rows)

    key = ("2026-06-16", "Argentina", "Mexico", "1X2", "1")
    out = tracker.update_bet_user_fields(key, manual_result="loss")
    assert out["manual_result"] == "loss"
    assert out["pnl_eur"] == -50.0         # override flips the euro P&L


def test_update_bet_user_fields_not_found(monkeypatch):
    ws = FakeWS()
    _patch_bets(monkeypatch, ws, [_row()])
    out = tracker.update_bet_user_fields(("nope", "x", "y", "1X2", "1"), placed=True)
    assert out is False
    assert ws.updates == []                # nothing written on a miss


# --- grade_pending: model track + euro track + manual override --------------

def _patch_grade(monkeypatch, ws, bet_rows, result_rows):
    def fake_values(title, headers):
        if title == tracker.SHEETS_TAB_BETS:
            return ws, _matrix(bet_rows)
        rmat = [list(tracker.RESULTS_HEADERS)] + [
            [d.get(h, "") for h in tracker.RESULTS_HEADERS] for d in result_rows]
        return FakeWS(), rmat
    monkeypatch.setattr(tracker, "_values", fake_values)
    monkeypatch.setattr(tracker, "_cache_clear", lambda: None)


def _result(outcome="1", hs="2", as_="1"):
    return {"match_date": "2026-06-16", "home_team": "Argentina",
            "away_team": "Mexico", "home_score": hs, "away_score": as_,
            "outcome": outcome}


def test_grade_pending_writes_units_and_euros_for_placed(monkeypatch):
    ws = FakeWS()
    # placed 1X2 home bet, home win -> should settle units AND euros
    bets = [_row(placed="1", staked_real="50", odds="2.00")]
    _patch_grade(monkeypatch, ws, bets, [_result()])

    settled = tracker.grade_pending()
    assert settled == 1
    flat = {u["range"]: u["values"][0] for u in ws.batch}
    # model track: result + pnl_units in one range (cols O:P)
    res_range = next(r for r in flat if ":" in r)
    assert flat[res_range][0] == "win"
    # euro track: a single-cell pnl_eur write
    eur_cell = next(r for r in flat if ":" not in r)
    assert flat[eur_cell] == ["50.0"]


def test_grade_pending_unplaced_has_no_euro(monkeypatch):
    ws = FakeWS()
    bets = [_row(staked_real="0", odds="2.00")]      # not placed
    _patch_grade(monkeypatch, ws, bets, [_result()])
    tracker.grade_pending()
    # only the model-track range write, no single-cell euro write
    assert all(":" in u["range"] for u in ws.batch)


def test_grade_pending_never_clobbers_manual_result(monkeypatch):
    ws = FakeWS()
    # user hand-settled this placed bet as a loss; feed says home win
    bets = [_row(placed="1", staked_real="50", odds="2.00",
                 manual_result="loss")]
    _patch_grade(monkeypatch, ws, bets, [_result()])

    tracker.grade_pending()
    # no write touches the manual_result column (col S)
    s_col = tracker._col_a1(H.index("manual_result") + 1)
    for u in ws.batch:
        assert not u["range"].startswith(f"{s_col}")
        # ranges that span columns must not include manual_result either
    # euro P&L follows the manual override (loss) not the feed (win)
    eur_cell = next((u for u in ws.batch if ":" not in u["range"]), None)
    assert eur_cell is not None and eur_cell["values"][0] == ["-50"]


# --- _real_summary ----------------------------------------------------------

def test_real_summary():
    bets = [
        tracker._typed_bet(_row(placed="1", staked_real="50", odds="2.00",
                                result="win", edge="0.10")),
        tracker._typed_bet(_row(placed="1", staked_real="40", odds="3.00",
                                result="loss", edge="0.20", selection="2")),
        tracker._typed_bet(_row(placed="1", staked_real="30", odds="2.00",
                                result="pending", selection="X")),
        tracker._typed_bet(_row(result="win", selection="1", market="OU2.5")),  # unplaced
    ]
    r = tracker._real_summary(bets)
    assert r["placed"] == 3
    assert r["settled"] == 2
    assert r["wins"] == 1 and r["losses"] == 1
    assert r["pnl_eur"] == 10.0            # +50 (win) - 40 (loss)
    assert r["open_exposure_eur"] == 30.0  # the pending placed bet
    assert r["staked_eur"] == 120.0
    # roi over settled stake (90): 10/90 -> 11.1%
    assert r["roi_eur_pct"] == 11.1


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
