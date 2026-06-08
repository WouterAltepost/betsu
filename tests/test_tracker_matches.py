"""
Offline tests for the per-model 1X2 capture added to record_matches.

The Matches tab now stores each predictor's raw 1X2 (market/elo/poisson)
alongside the blend, so a future leaderboard can score the contenders. These
tests stub the worksheet layer, so they run with no network and no Google
credentials. They assert that a full `preds` populates all nine per-model cells,
that a missing model writes blanks (and never raises), and that `preds` is
optional (the legacy 4-tuple still works).

Run:  python -m pytest tests/test_tracker_matches.py
  or:  python tests/test_tracker_matches.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools import tracker  # noqa: E402

H = tracker.MATCHES_HEADERS


class FakeWS:
    def __init__(self):
        self.appended = []

    def append_rows(self, rows, value_input_option=None):
        self.appended.extend(rows)


def _patch_matches(monkeypatch, ws, existing=None):
    """Stub _values (existing rows) and _ws (the append target)."""
    matrix = [list(H)] + [[d.get(h, "") for h in H] for d in (existing or [])]
    monkeypatch.setattr(tracker, "_values",
                        lambda title, headers: (ws, matrix))
    monkeypatch.setattr(tracker, "_ws", lambda title, headers: ws)


BLEND = {"1": 0.50, "X": 0.30, "2": 0.20}
PREDS_FULL = {
    "market": {"1": 0.55, "X": 0.27, "2": 0.18},
    "elo": {"1": 0.60, "X": 0.25, "2": 0.15},
    "poisson": {"1": 0.48, "X": 0.31, "2": 0.21},
}


def _written(ws):
    """The single appended row as a {header: cell} dict."""
    assert len(ws.appended) == 1
    return dict(zip(H, ws.appended[0]))


def test_record_matches_full_preds_populates_all_cells(monkeypatch):
    ws = FakeWS()
    _patch_matches(monkeypatch, ws)

    n = tracker.record_matches([("2026-06-16", "Argentina", "Mexico", BLEND, PREDS_FULL)])
    assert n == 1
    row = _written(ws)
    # blend is unchanged
    assert row["p_home"] == "0.5" and row["p_draw"] == "0.3" and row["p_away"] == "0.2"
    # every per-model cell is populated
    assert (row["mkt_1"], row["mkt_X"], row["mkt_2"]) == ("0.55", "0.27", "0.18")
    assert (row["elo_1"], row["elo_X"], row["elo_2"]) == ("0.6", "0.25", "0.15")
    assert (row["poi_1"], row["poi_X"], row["poi_2"]) == ("0.48", "0.31", "0.21")


def test_record_matches_partial_preds_blanks_missing_model(monkeypatch):
    ws = FakeWS()
    _patch_matches(monkeypatch, ws)

    # an unseeded match drops Elo/Poisson; only the market layer survives
    preds = {"market": {"1": 0.55, "X": 0.27, "2": 0.18}}
    n = tracker.record_matches([("2026-06-16", "Argentina", "Mexico", BLEND, preds)])
    assert n == 1
    row = _written(ws)
    assert (row["mkt_1"], row["mkt_X"], row["mkt_2"]) == ("0.55", "0.27", "0.18")
    # the absent models are blank, not raised
    assert row["elo_1"] == "" and row["elo_X"] == "" and row["elo_2"] == ""
    assert row["poi_1"] == "" and row["poi_X"] == "" and row["poi_2"] == ""


def test_record_matches_preds_optional_legacy_tuple(monkeypatch):
    ws = FakeWS()
    _patch_matches(monkeypatch, ws)

    # the legacy 4-tuple (no preds) must still work and blank all per-model cells
    n = tracker.record_matches([("2026-06-16", "Argentina", "Mexico", BLEND)])
    assert n == 1
    row = _written(ws)
    assert row["p_home"] == "0.5"
    for col in ("mkt_1", "mkt_X", "mkt_2", "elo_1", "elo_X", "elo_2",
                "poi_1", "poi_X", "poi_2"):
        assert row[col] == ""


def test_record_matches_none_preds_does_not_raise(monkeypatch):
    ws = FakeWS()
    _patch_matches(monkeypatch, ws)

    n = tracker.record_matches([("2026-06-16", "Argentina", "Mexico", BLEND, None)])
    assert n == 1
    row = _written(ws)
    assert row["elo_1"] == "" and row["poi_2"] == ""


def test_record_matches_dedups_existing(monkeypatch):
    ws = FakeWS()
    existing = [{"match_date": "2026-06-16", "home_team": "Argentina",
                 "away_team": "Mexico"}]
    _patch_matches(monkeypatch, ws, existing=existing)

    n = tracker.record_matches([("2026-06-16", "Argentina", "Mexico", BLEND, PREDS_FULL)])
    assert n == 0
    assert ws.appended == []


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
