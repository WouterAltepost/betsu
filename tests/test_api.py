"""
Offline tests for the SPA JSON API in app.py. The tracker (Sheets) layer is
stubbed, so these run with no network / no Google credentials. Dashboard auth is
open here (DASHBOARD_USER/PASSWORD unset), matching local dev.

Run:  python -m pytest tests/test_api.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app as app_mod  # noqa: E402
from tools import tracker  # noqa: E402


def _typed(**over):
    base = {h: "" for h in tracker.BETS_HEADERS}
    base.update({"match_date": "2026-06-16", "home_team": "Argentina",
                 "away_team": "Mexico", "market": "1X2", "selection": "1",
                 "selection_label": "Home (Argentina)", "odds": "1.95",
                 "model_prob": "0.62", "implied_prob": "0.51", "edge": "0.209",
                 "kelly_units": "0.05", "result": "pending"})
    base.update(over)
    return tracker._typed_bet(base)


def _client():
    app_mod.app.config["TESTING"] = True
    return app_mod.app.test_client()


def test_api_bets_shape(monkeypatch):
    monkeypatch.setattr(app_mod.tracker_mod, "fetch_bets",
                        lambda: [_typed(placed="1", staked_real="50",
                                        result="win")])
    resp = _client().get("/api/bets")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 1
    b = data[0]
    assert b["home"] == "Argentina" and b["away"] == "Mexico"
    assert b["pick"] == "Home (Argentina)"
    assert b["placed"] is True and b["stake"] == 50
    assert b["outcome"] == "win" and b["result"] == "win" and b["played"] is True
    assert b["key"] == {"match_date": "2026-06-16", "home_team": "Argentina",
                        "away_team": "Mexico", "market": "1X2", "selection": "1"}
    assert b["id"]  # stable id present


def test_api_bets_degrades_on_error(monkeypatch):
    def boom():
        raise RuntimeError("sheets down")
    monkeypatch.setattr(app_mod.tracker_mod, "fetch_bets", boom)
    resp = _client().get("/api/bets")
    assert resp.status_code == 200
    assert "error" in resp.get_json()


def test_api_summary(monkeypatch):
    monkeypatch.setattr(app_mod.tracker_mod, "summary",
                        lambda: {"pnl_units": 1.2, "real": {"pnl_eur": 50.0}})
    resp = _client().get("/api/summary")
    assert resp.status_code == 200
    assert resp.get_json()["real"]["pnl_eur"] == 50.0


def test_api_update_ok(monkeypatch):
    captured = {}

    def fake_update(key, placed=None, stake_eur=None, manual_result=None):
        captured.update(key=key, placed=placed, stake_eur=stake_eur,
                        manual_result=manual_result)
        return _typed(placed="1", staked_real="50", result="win")

    monkeypatch.setattr(app_mod.tracker_mod, "update_bet_user_fields", fake_update)
    key = {"match_date": "2026-06-16", "home_team": "Argentina",
           "away_team": "Mexico", "market": "1X2", "selection": "1"}
    resp = _client().post("/api/bets/update",
                          json={"key": key, "placed": True, "stake": 50})
    assert resp.status_code == 200
    assert captured["placed"] is True and captured["stake_eur"] == 50.0
    assert resp.get_json()["placed"] is True


def test_api_update_missing_key():
    resp = _client().post("/api/bets/update", json={"placed": True})
    assert resp.status_code == 400


def test_api_update_bad_stake():
    key = {"match_date": "d", "home_team": "h", "away_team": "a",
           "market": "1X2", "selection": "1"}
    resp = _client().post("/api/bets/update", json={"key": key, "stake": -5})
    assert resp.status_code == 400


def test_api_update_bad_manual():
    key = {"match_date": "d", "home_team": "h", "away_team": "a",
           "market": "1X2", "selection": "1"}
    resp = _client().post("/api/bets/update",
                          json={"key": key, "manual_result": "tie"})
    assert resp.status_code == 400


def test_api_update_not_found(monkeypatch):
    monkeypatch.setattr(app_mod.tracker_mod, "update_bet_user_fields",
                        lambda *a, **k: False)
    key = {"match_date": "d", "home_team": "h", "away_team": "a",
           "market": "1X2", "selection": "1"}
    resp = _client().post("/api/bets/update", json={"key": key, "placed": True})
    assert resp.status_code == 404


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
