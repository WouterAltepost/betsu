"""
tracker.py — Google Sheets store for predictions, suggested bets, and results.

Google Sheets is betsu's single source of truth (no local DB). This module keeps
the same public interface it had as a SQLite store, so run_daily.py and
dashboard/app.py keep working:

    record_match / record_matches   — match-level blended probs (calibration)
    record_bet   / record_bets      — suggested value bets (batched, deduped)
    record_result                   — final score for a fixture
    grade_pending                   — settle pending bets against results, in place
    summary                         — running record + ROI (optionally writes Summary tab)
    fetch_bets / fetch_results      — read the store (short TTL cache for the dashboard)

Tabs (created on first use if missing):
    Bets      — every suggested bet, with result + P&L once graded
    Results   — final scores (hand-typed into the sheet, or via record_result)
    Matches   — every fixture we predicted, with our blended 1X2 probs
    Summary   — running record, written by summary() for at-a-glance viewing

Dedup: a bet's identity is (match_date, home_team, away_team, market, selection);
a fixture's is (match_date, home_team, away_team). Writes skip rows whose key
already exists, so re-running a scan only appends genuinely new rows.

Auth is a Google Cloud *service account*:
    deploy — GOOGLE_CREDENTIALS_B64   (base64 of the key JSON; preferred, paste-safe)
             GOOGLE_CREDENTIALS_JSON  (full key JSON pasted into an env var)
    local  — a credentials.json key file (GOOGLE_CREDENTIALS_PATH)
Precedence: B64 -> JSON -> key file.
GOOGLE_SHEETS_ID selects the spreadsheet. See docs/google_sheets_setup.md.

CLI:
    python tools/tracker.py status     # show whether the store is configured
    python tools/tracker.py init       # ensure the tabs exist
    python tools/tracker.py summary     # print running record + ROI
"""

import json
import os
import sys
import time
from datetime import datetime, timezone

from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (SHEETS_CACHE_TTL, SHEETS_CREDENTIALS_DEFAULT, SHEETS_TAB_BETS,
                    SHEETS_TAB_BTTS, SHEETS_TAB_CONTEXT, SHEETS_TAB_MATCHES,
                    SHEETS_TAB_RESULTS, SHEETS_TAB_SUMMARY)

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

SHEET_ID = os.environ.get("GOOGLE_SHEETS_ID", "").strip()

# Column order for each tab. The store round-trips everything as text (see _cell)
# so dates never get coerced to date serials; types are restored on read.
BETS_HEADERS = ["match_date", "commence_time", "home_team", "away_team", "market",
                "selection", "selection_label", "model_prob", "implied_prob", "odds",
                "edge", "stake_units", "kelly_units", "staked_real", "result",
                "pnl_units", "created_at"]
RESULTS_HEADERS = ["match_date", "home_team", "away_team",
                   "home_score", "away_score", "outcome"]
MATCHES_HEADERS = ["match_date", "home_team", "away_team",
                   "p_home", "p_draw", "p_away", "created_at"]
SUMMARY_HEADERS = ["metric", "value"]
# LLM context-nudge cache. One row per fixture; key is "match_date|home|away".
# nudge is a JSON blob ({"1","X","2"}); fetched_at gates the TTL refresh.
CONTEXT_HEADERS = ["key", "nudge", "summary", "source", "confidence", "fetched_at"]
# Per-event BTTS price cache. One row per event id; fetched_at gates the TTL.
BTTS_HEADERS = ["event_id", "yes", "no", "fetched_at"]

BET_KEY_COLS = ("match_date", "home_team", "away_team", "market", "selection")
MATCH_KEY_COLS = ("match_date", "home_team", "away_team")
RESULT_KEY_COLS = ("match_date", "home_team", "away_team")

# Columns restored to float on read; everything else stays string.
_FLOAT_BET_COLS = {"model_prob", "implied_prob", "odds", "edge",
                   "stake_units", "kelly_units", "pnl_units"}


# --- Sheets connection (lazy, cached per process) ---------------------------

_GC = None          # gspread client
_SS = None          # opened spreadsheet
_WS = {}            # title -> worksheet handle
_CACHE = {}         # name -> (timestamp, data) for fetch_* read-through cache


def _client():
    global _GC
    if _GC is None:
        import gspread
        b64 = os.environ.get("GOOGLE_CREDENTIALS_B64", "").strip()
        info = os.environ.get("GOOGLE_CREDENTIALS_JSON", "").strip()
        if b64:
            import base64
            _GC = gspread.service_account_from_dict(
                json.loads(base64.b64decode(b64)))
        elif info:
            _GC = gspread.service_account_from_dict(json.loads(info))
        else:
            path = os.environ.get("GOOGLE_CREDENTIALS_PATH", SHEETS_CREDENTIALS_DEFAULT)
            if not os.path.exists(path):
                raise RuntimeError(
                    "No Google credentials. Set GOOGLE_CREDENTIALS_B64 or "
                    "GOOGLE_CREDENTIALS_JSON (deploy) or place a service-account "
                    f"key at {path} (local).")
            _GC = gspread.service_account(filename=path)
    return _GC


def _spreadsheet():
    global _SS
    if _SS is None:
        if not SHEET_ID:
            raise RuntimeError(
                "GOOGLE_SHEETS_ID is not set — Google Sheets is betsu's store. "
                "See docs/google_sheets_setup.md.")
        _SS = _client().open_by_key(SHEET_ID)
    return _SS


def _ws(title, headers):
    """Get or create a worksheet, writing the header row on creation. Cached."""
    if title in _WS:
        return _WS[title]
    import gspread
    ss = _spreadsheet()
    try:
        ws = ss.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(title=title, rows=200, cols=max(len(headers), 6))
        ws.update(range_name="A1", values=[headers], value_input_option="RAW")
    _WS[title] = ws
    return ws


def _values(title, headers):
    """Return (ws, all_values) with the header row present and matching `headers`.
    Repairs an empty or stale header in place (safe); refuses to proceed if the
    tab already holds data under a different header, so appends never misalign."""
    ws = _ws(title, headers)
    vals = ws.get_all_values()
    if not vals or vals[0] != headers:
        if len(vals) > 1:
            raise RuntimeError(
                f"The '{title}' tab's header doesn't match this version's schema "
                f"(its columns changed). Clear or delete that tab and re-run so "
                f"betsu recreates it, or set row 1 to: {headers}")
        ws.update(range_name="A1", values=[headers], value_input_option="RAW")
        return ws, [headers]
    return ws, vals


def _dicts(values):
    """Map a values matrix (header row + data) to a list of dict rows."""
    head = values[0]
    out = []
    for row in values[1:]:
        row = list(row) + [""] * (len(head) - len(row))
        out.append(dict(zip(head, row)))
    return out


def _cell(v):
    """Render a value for storage: None -> "", everything else stringified."""
    return "" if v is None else str(v)


def _col_a1(n):
    """1-based column index -> A1 letter (1->A, 27->AA)."""
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


# --- Read-through cache (keeps the dashboard snappy; writes invalidate) ------

def _cache_get(name):
    item = _CACHE.get(name)
    if item and (time.time() - item[0]) < SHEETS_CACHE_TTL:
        return item[1]
    return None


def _cache_put(name, data):
    _CACHE[name] = (time.time(), data)


def _cache_clear():
    _CACHE.clear()


# --- Type coercion (Sheets stores text; restore numbers on read) ------------

def _to_float(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _to_int(v):
    f = _to_float(v)
    return int(f) if f is not None else None


def _typed_bet(d):
    b = dict(d)
    for k in _FLOAT_BET_COLS:
        b[k] = _to_float(d.get(k))
    b["staked_real"] = _to_int(d.get("staked_real")) or 0
    b["result"] = d.get("result") or "pending"
    return b


def _typed_result(d):
    r = dict(d)
    r["home_score"] = _to_int(d.get("home_score"))
    r["away_score"] = _to_int(d.get("away_score"))
    r["outcome"] = d.get("outcome") or None
    return r


def _key(d, cols):
    return tuple(str(d.get(c, "")).strip() for c in cols)


# --- Public: ensure / status ------------------------------------------------

def init_db():
    """Ensure the store's tabs exist. (Name kept from the SQLite era for callers
    and the CLI; Sheets is the store now.)"""
    _ws(SHEETS_TAB_BETS, BETS_HEADERS)
    _ws(SHEETS_TAB_RESULTS, RESULTS_HEADERS)
    _ws(SHEETS_TAB_MATCHES, MATCHES_HEADERS)
    _ws(SHEETS_TAB_SUMMARY, SUMMARY_HEADERS)
    _ws(SHEETS_TAB_CONTEXT, CONTEXT_HEADERS)
    _ws(SHEETS_TAB_BTTS, BTTS_HEADERS)
    return SHEET_ID


def status():
    """Human-readable config check (no network)."""
    if not SHEET_ID:
        return "Store OFF — GOOGLE_SHEETS_ID is not set in .env."
    if os.environ.get("GOOGLE_CREDENTIALS_JSON", "").strip():
        return f"Store ON — sheet {SHEET_ID}, creds from GOOGLE_CREDENTIALS_JSON."
    path = os.environ.get("GOOGLE_CREDENTIALS_PATH", SHEETS_CREDENTIALS_DEFAULT)
    if not os.path.exists(path):
        return f"Store MISCONFIGURED — sheet {SHEET_ID} set but no creds (looked for {path})."
    return f"Store ON — sheet {SHEET_ID}, key {path}."


# --- Public: reads ----------------------------------------------------------

def fetch_bets():
    """All suggested bets, oldest first. List of typed dicts (short TTL cache)."""
    cached = _cache_get("bets")
    if cached is not None:
        return cached
    _, vals = _values(SHEETS_TAB_BETS, BETS_HEADERS)
    bets = [_typed_bet(d) for d in _dicts(vals)]
    _cache_put("bets", bets)
    return bets


def fetch_results():
    """All recorded results, oldest first. List of typed dicts (short TTL cache)."""
    cached = _cache_get("results")
    if cached is not None:
        return cached
    _, vals = _values(SHEETS_TAB_RESULTS, RESULTS_HEADERS)
    res = [_typed_result(d) for d in _dicts(vals)]
    _cache_put("results", res)
    return res


def fetch_matches():
    """All predicted fixtures from the Matches tab, oldest first. List of dicts
    with at least match_date/home_team/away_team — used as a reconciliation
    source when syncing results from an external feed (short TTL cache)."""
    cached = _cache_get("matches")
    if cached is not None:
        return cached
    _, vals = _values(SHEETS_TAB_MATCHES, MATCHES_HEADERS)
    rows = _dicts(vals)
    _cache_put("matches", rows)
    return rows


# --- Public: bets -----------------------------------------------------------

def _bet_row(b):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    src = {
        "match_date": b.get("match_date"),
        "commence_time": b.get("commence_time"),
        "home_team": b.get("home_team"),
        "away_team": b.get("away_team"),
        "market": b.get("market"),
        "selection": b.get("selection"),
        "selection_label": b.get("selection_label"),
        "model_prob": b.get("model_prob"),
        "implied_prob": b.get("implied_prob"),
        "odds": b.get("odds"),
        "edge": b.get("edge"),
        "stake_units": b.get("stake_units"),
        "kelly_units": b.get("kelly_units"),
        "staked_real": int(b.get("staked_real", 0) or 0),
        "result": b.get("result") or "pending",
        "pnl_units": b.get("pnl_units"),
        "created_at": b.get("created_at") or now,
    }
    return [_cell(src[h]) for h in BETS_HEADERS]


def filter_new(bets):
    """Return only bets whose key isn't already in the Bets tab (and dedup the
    batch against itself). Used to post only genuinely new selections."""
    existing = {_key(b, BET_KEY_COLS) for b in fetch_bets()}
    fresh, seen = [], set()
    for b in bets:
        k = _key(b, BET_KEY_COLS)
        if k in existing or k in seen:
            continue
        seen.add(k)
        fresh.append(b)
    return fresh


def record_bets(bets):
    """Append new value bets in one batched call (dedup-safe). Returns the bets
    actually written (the genuinely new ones)."""
    fresh = filter_new(bets)
    if not fresh:
        return []
    ws = _ws(SHEETS_TAB_BETS, BETS_HEADERS)
    ws.append_rows([_bet_row(b) for b in fresh], value_input_option="RAW")
    _cache_clear()
    return fresh


def record_bet(bet):
    """Append a single value bet (dedup-safe). Returns True if it was new."""
    return bool(record_bets([bet]))


# --- Public: matches (calibration) ------------------------------------------

def record_matches(rows):
    """Append match-level blended probs (dedup-safe). rows: iterable of
    (match_date, home, away, probs{"1","X","2"}). Returns count written."""
    _, vals = _values(SHEETS_TAB_MATCHES, MATCHES_HEADERS)
    existing = {_key(d, MATCH_KEY_COLS) for d in _dicts(vals)}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    new_rows, seen = [], set()
    for match_date, home, away, probs in rows:
        k = (str(match_date).strip(), str(home).strip(), str(away).strip())
        if k in existing or k in seen:
            continue
        seen.add(k)
        probs = probs or {}
        new_rows.append([_cell(match_date), _cell(home), _cell(away),
                         _cell(probs.get("1")), _cell(probs.get("X")),
                         _cell(probs.get("2")), now])
    if new_rows:
        _ws(SHEETS_TAB_MATCHES, MATCHES_HEADERS).append_rows(
            new_rows, value_input_option="RAW")
    return len(new_rows)


def record_match(match_date, home, away, probs):
    """Record one fixture's blended probs (dedup-safe)."""
    return record_matches([(match_date, home, away, probs)])


# --- Public: results --------------------------------------------------------

def record_result(match_date, home, away, home_score, away_score):
    """Upsert a final score into the Results tab. Returns the 1X2 outcome."""
    outcome = ("1" if home_score > away_score
               else "2" if away_score > home_score else "X")
    ws, vals = _values(SHEETS_TAB_RESULTS, RESULTS_HEADERS)
    row = [_cell(match_date), _cell(home), _cell(away),
           _cell(home_score), _cell(away_score), outcome]
    key = (str(match_date).strip(), str(home).strip(), str(away).strip())
    for i, d in enumerate(_dicts(vals), start=2):  # row 1 is the header
        if _key(d, RESULT_KEY_COLS) == key:
            ws.update(range_name=f"A{i}:{_col_a1(len(RESULTS_HEADERS))}{i}",
                      values=[row], value_input_option="RAW")
            _cache_clear()
            return outcome
    ws.append_rows([row], value_input_option="RAW")
    _cache_clear()
    return outcome


# --- Public: grading --------------------------------------------------------

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
    """Settle pending bets against recorded results, updating the Bets rows in
    place (one batched cell update). Returns the count settled."""
    ws, vals = _values(SHEETS_TAB_BETS, BETS_HEADERS)
    head = vals[0]
    res_col = head.index("result") + 1      # 1-based for A1
    pnl_col = head.index("pnl_units") + 1

    _, rvals = _values(SHEETS_TAB_RESULTS, RESULTS_HEADERS)
    rmap = {_key(d, RESULT_KEY_COLS): _typed_result(d) for d in _dicts(rvals)}

    updates, settled = [], 0
    for i, row in enumerate(vals[1:], start=2):
        row = list(row) + [""] * (len(head) - len(row))
        d = dict(zip(head, row))
        if (d.get("result") or "pending") != "pending":
            continue
        res = rmap.get(_key(d, RESULT_KEY_COLS))
        if not res or not res.get("outcome"):
            continue
        bet = _typed_bet(d)
        won = _bet_won(bet, res)
        if won is None:
            continue  # market needs scores we don't have yet
        stake = bet.get("stake_units") or 0.0
        odds = bet.get("odds") or 0.0
        pnl = stake * (odds - 1) if won else -stake
        rng = f"{_col_a1(res_col)}{i}:{_col_a1(pnl_col)}{i}"
        updates.append({"range": rng,
                        "values": [["win" if won else "loss", str(round(pnl, 3))]]})
        settled += 1

    if updates:
        ws.batch_update(updates, value_input_option="RAW")
        _cache_clear()
    return settled


# --- Public: summary --------------------------------------------------------

def summary(write=False):
    """Running record + ROI computed from the Bets tab. When write=True, also
    refresh the Summary tab for at-a-glance viewing in the sheet."""
    bets = fetch_bets()
    wins = sum(1 for b in bets if b["result"] == "win")
    losses = sum(1 for b in bets if b["result"] == "loss")
    pending = sum(1 for b in bets if b["result"] not in ("win", "loss", "void"))
    total_settled = wins + losses
    total_pnl = sum((b.get("pnl_units") or 0.0)
                    for b in bets if b["result"] in ("win", "loss"))
    staked = total_settled  # 1 unit flat
    roi = (total_pnl / staked * 100) if staked else 0.0
    hit = (wins / total_settled * 100) if total_settled else 0.0
    s = {
        "settled": total_settled, "wins": wins, "losses": losses,
        "pending": pending, "hit_rate": round(hit, 1),
        "pnl_units": round(total_pnl, 2), "roi_pct": round(roi, 1),
    }
    if write:
        _write_summary(s)
    return s


def _write_summary(s):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    rows = [
        SUMMARY_HEADERS,
        ["last_updated", now],
        ["settled", s["settled"]],
        ["wins", s["wins"]],
        ["losses", s["losses"]],
        ["pending", s["pending"]],
        ["hit_rate_pct", s["hit_rate"]],
        ["pnl_units", s["pnl_units"]],
        ["roi_pct", s["roi_pct"]],
    ]
    ws = _ws(SHEETS_TAB_SUMMARY, SUMMARY_HEADERS)
    ws.clear()
    ws.update(range_name="A1",
              values=[[_cell(c) for c in r] for r in rows],
              value_input_option="RAW")


# --- Public: LLM context-nudge cache ----------------------------------------

def context_key(match_date, home, away):
    """Stable cache key for a fixture's context nudge."""
    return f"{str(match_date).strip()}|{str(home).strip()}|{str(away).strip()}"


def fetch_context(key):
    """Return the cached context row for `key` as a dict (nudge parsed from
    JSON), or None if absent. Short TTL read-through cache like the others."""
    cached = _cache_get("context")
    if cached is None:
        _, vals = _values(SHEETS_TAB_CONTEXT, CONTEXT_HEADERS)
        cached = {d["key"]: d for d in _dicts(vals) if d.get("key")}
        _cache_put("context", cached)
    row = cached.get(key)
    if not row:
        return None
    out = dict(row)
    try:
        out["nudge"] = json.loads(row.get("nudge") or "{}")
    except (ValueError, TypeError):
        out["nudge"] = {}
    return out


def upsert_context(key, nudge, summary, source, confidence, fetched_at):
    """Insert or update one context-cache row (keyed by `key`). nudge is a
    {"1","X","2"} dict, stored as JSON. Returns the key written."""
    ws, vals = _values(SHEETS_TAB_CONTEXT, CONTEXT_HEADERS)
    row = [_cell(key), json.dumps(nudge or {}), _cell(summary),
           _cell(source), _cell(confidence), _cell(fetched_at)]
    for i, d in enumerate(_dicts(vals), start=2):  # row 1 is the header
        if str(d.get("key", "")).strip() == key:
            ws.update(range_name=f"A{i}:{_col_a1(len(CONTEXT_HEADERS))}{i}",
                      values=[row], value_input_option="RAW")
            _cache_clear()
            return key
    ws.append_rows([row], value_input_option="RAW")
    _cache_clear()
    return key


# --- Public: per-event BTTS price cache -------------------------------------

def fetch_btts_odds(event_id):
    """Return the cached BTTS row for `event_id` as
    {"yes": float, "no": float, "fetched_at": str}, or None if absent.
    Short TTL read-through cache like the others (the caller decides freshness
    against BTTS_CACHE_HOURS using fetched_at)."""
    cached = _cache_get("btts")
    if cached is None:
        _, vals = _values(SHEETS_TAB_BTTS, BTTS_HEADERS)
        cached = {d["event_id"]: d for d in _dicts(vals) if d.get("event_id")}
        _cache_put("btts", cached)
    row = cached.get(str(event_id))
    if not row:
        return None
    return {
        "yes": _to_float(row.get("yes")),
        "no": _to_float(row.get("no")),
        "fetched_at": row.get("fetched_at") or "",
    }


def upsert_btts_odds(event_id, yes, no, fetched_at):
    """Insert or update one BTTS-cache row (keyed by `event_id`).
    Returns the event_id written."""
    ws, vals = _values(SHEETS_TAB_BTTS, BTTS_HEADERS)
    event_id = str(event_id)
    row = [_cell(event_id), _cell(yes), _cell(no), _cell(fetched_at)]
    for i, d in enumerate(_dicts(vals), start=2):  # row 1 is the header
        if str(d.get("event_id", "")).strip() == event_id:
            ws.update(range_name=f"A{i}:{_col_a1(len(BTTS_HEADERS))}{i}",
                      values=[row], value_input_option="RAW")
            _cache_clear()
            return event_id
    ws.append_rows([row], value_input_option="RAW")
    _cache_clear()
    return event_id


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "summary"
    if cmd == "status":
        print(status())
    elif cmd == "init":
        init_db()
        print(f"Ensured Bets/Results/Matches/Summary/Context/BttsOdds tabs in sheet {SHEET_ID}")
    elif cmd == "summary":
        s = summary()
        print(f"Settled: {s['settled']}  W:{s['wins']} L:{s['losses']}  "
              f"Pending:{s['pending']}")
        print(f"Hit rate: {s['hit_rate']}%   P&L: {s['pnl_units']:+} units   "
              f"ROI: {s['roi_pct']:+}%")
    else:
        print("usage: python tools/tracker.py [status|init|summary]")
