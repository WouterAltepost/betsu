"""
app.py — betsu's single Flask service (stateless; deploy on Railway with gunicorn).

It does two jobs:
  - serves the performance dashboard at GET / (reads the Google Sheets store)
  - exposes protected run endpoints that n8n calls on a schedule:
      POST /run/morning  — windowed scan, post only new value bets
      POST /run/grade    — settle pending bets against the Results tab
  - GET /healthz         — liveness check (no Sheets call), for n8n/Railway

Auth:
  - run endpoints require RUN_API_KEY, sent as header `X-Run-Key: <key>` or `?key=`.
  - the dashboard uses HTTP Basic Auth when DASHBOARD_USER/DASHBOARD_PASSWORD are
    set (open if unset, for local dev).

Runs are synchronous inside the request (a few seconds) — gunicorn --timeout 120.
No background worker, no in-process scheduler; n8n owns scheduling.

Run:
    python app.py                                   # local dev, http://127.0.0.1:5000
    gunicorn app:app --workers 2 --timeout 120      # production (see Procfile)
"""

import hashlib
import hmac
import mimetypes
import os
import sys
from datetime import date, datetime, timezone
from functools import wraps

from flask import Flask, Response, jsonify, request, send_from_directory

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_daily
from config import SCAN_WINDOW_HOURS
from tools import tracker as tracker_mod

app = Flask(__name__)

# Serve .webmanifest with the right type (some setups default to octet-stream).
mimetypes.add_type("application/manifest+json", ".webmanifest")

RUN_API_KEY = os.environ.get("RUN_API_KEY", "").strip()
DASHBOARD_USER = os.environ.get("DASHBOARD_USER", "")
DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "")


# --- Auth helpers -----------------------------------------------------------

def require_run_key(f):
    """Gate a run endpoint on RUN_API_KEY (header X-Run-Key or ?key=)."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not RUN_API_KEY:
            return jsonify({"error": "run endpoints disabled: RUN_API_KEY not set"}), 503
        provided = request.headers.get("X-Run-Key") or request.args.get("key") or ""
        if not hmac.compare_digest(provided, RUN_API_KEY):
            return jsonify({"error": "unauthorized"}), 401
        return f(*args, **kwargs)
    return wrapper


def require_dashboard_auth(f):
    """HTTP Basic Auth for the dashboard when creds are configured; open if not."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if DASHBOARD_USER or DASHBOARD_PASSWORD:
            auth = request.authorization
            ok = (auth is not None
                  and hmac.compare_digest(auth.username or "", DASHBOARD_USER)
                  and hmac.compare_digest(auth.password or "", DASHBOARD_PASSWORD))
            if not ok:
                return Response(
                    "Authentication required.", 401,
                    {"WWW-Authenticate": 'Basic realm="betsu"'})
        return f(*args, **kwargs)
    return wrapper


# --- Health + run endpoints -------------------------------------------------

@app.route("/healthz")
def healthz():
    """Liveness only — deliberately does not touch Sheets, so it stays green
    during boot and even if the store is briefly unreachable."""
    return "ok", 200


@app.route("/run/morning", methods=["POST"])
@require_run_key
def run_morning_endpoint():
    result = run_daily.run_morning(str(date.today()), window_hours=SCAN_WINDOW_HOURS)
    return jsonify({
        "ok": True,
        "matches": result["matches"],
        "new_bets": result["new_bets"],
        "sent": result["sent"],
    })


@app.route("/run/grade", methods=["POST"])
@require_run_key
def run_grade_endpoint():
    result = run_daily.run_grade(str(date.today()))
    return jsonify({"ok": True, "settled": result["settled"], "record": result["record"]})


# --- JSON API for the SPA (read state + write placed/stake/manual_result) ----
# These power the React dashboard. They are gated by the same dashboard auth as
# GET / (no new secret), and degrade defensively so a Sheets hiccup never 500s
# the SPA. They never touch odds and never affect /run/morning or /run/grade.

BET_KEY_FIELDS = ("match_date", "home_team", "away_team", "market", "selection")


def _bet_id(bet):
    """Stable id for a bet from its key tuple (deterministic across processes,
    unlike Python's salted hash)."""
    raw = "|".join(str(bet.get(c, "")).strip() for c in BET_KEY_FIELDS)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def _kickoff_past(bet):
    """True if the fixture's kickoff (commence_time, ISO/UTC) is in the past."""
    ct = str(bet.get("commence_time") or "").strip()
    if not ct:
        return False
    try:
        dt = datetime.fromisoformat(ct.replace("Z", "+00:00"))
    except ValueError:
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt < datetime.now(timezone.utc)


def _display_market(m):
    """Map the stored totals market `"OU<line>"` (no space) to the SPA's
    `"OU <line>"` (with a space) so Over/Under bets match the dashboard's filter
    and ROI-by-market grouping. Only the *display* market is normalized — the raw
    value still keys the row for updates (see `_bet_to_spa`)."""
    m = (m or "").strip()
    if m.startswith("OU") and m[2:3].isdigit():
        return "OU " + m[2:]          # "OU2.5" -> "OU 2.5"
    return m


def _bet_to_spa(bet):
    """Shape one typed Bets row into the SPA's bet object (section 8 field map)."""
    eff = tracker_mod.effective_result(bet)          # win / loss / pending
    outcome = eff if eff in ("win", "loss") else None
    key = {c: str(bet.get(c, "")).strip() for c in BET_KEY_FIELDS}
    return {
        "id": _bet_id(bet),
        "date": bet.get("match_date"),
        "home": bet.get("home_team"),
        "away": bet.get("away_team"),
        "market": _display_market(bet.get("market")),
        "pick": bet.get("selection_label") or bet.get("selection"),
        "odds": bet.get("odds"),
        "model": bet.get("model_prob"),
        "market_p": bet.get("implied_prob"),
        "edge": bet.get("edge"),
        "kelly": bet.get("kelly_units"),
        "outcome": outcome,
        "played": outcome is not None or _kickoff_past(bet),
        "note": bet.get("context_note") or None,
        "placed": (bet.get("placed") or "").strip() == "1",
        "stake": bet.get("staked_real") or 0,
        "result": eff,
        "key": key,
    }


@app.route("/api/bets")
@require_dashboard_auth
def api_bets():
    """All bets, typed and shaped for the SPA. Degrades to {"error": ...} with a
    200 so the SPA can show a banner instead of a hard failure."""
    try:
        bets = tracker_mod.fetch_bets()
    except Exception as exc:
        return jsonify({"error": f"{type(exc).__name__}: {exc}"}), 200
    return jsonify([_bet_to_spa(b) for b in bets])


@app.route("/api/summary")
@require_dashboard_auth
def api_summary():
    """summary() dict: the real-money block (headline) + the units/model track."""
    try:
        return jsonify(tracker_mod.summary())
    except Exception as exc:
        return jsonify({"error": f"{type(exc).__name__}: {exc}"}), 200


@app.route("/api/bets/update", methods=["POST"])
@require_dashboard_auth
def api_bets_update():
    """Write the user-owned fields of one bet (placed / stake / manual_result).
    Body: {key:{match_date,home_team,away_team,market,selection}, placed?, stake?,
    manual_result?}. Returns the updated bet in SPA shape."""
    body = request.get_json(silent=True) or {}
    key = body.get("key") or {}
    if not all(str(key.get(c, "")).strip() for c in BET_KEY_FIELDS):
        return jsonify({"error": "missing or incomplete key"}), 400

    placed = body.get("placed")
    if placed is not None:
        placed = bool(placed)

    stake = body.get("stake")
    if stake is not None:
        try:
            stake = float(stake)
        except (TypeError, ValueError):
            return jsonify({"error": "stake must be numeric"}), 400
        if stake < 0:
            return jsonify({"error": "stake must be >= 0"}), 400

    manual = body.get("manual_result")
    if manual is not None:
        manual = str(manual).strip().lower()
        if manual not in ("win", "loss", ""):
            return jsonify({"error": "manual_result must be win, loss, or empty"}), 400

    try:
        updated = tracker_mod.update_bet_user_fields(
            key, placed=placed, stake_eur=stake, manual_result=manual)
    except Exception as exc:
        return jsonify({"error": f"{type(exc).__name__}: {exc}"}), 500
    if updated is False:
        return jsonify({"error": "bet not found"}), 404
    return jsonify(_bet_to_spa(updated))


# --- Dashboard (React SPA served as static files) ---------------------------
# The performance UI is the vendored React app in static/dashboard/ (libs are
# vendored locally under vendor/, so a dashboard load has no runtime CDN
# dependency). Everything here is gated by the same dashboard auth as the API.

DASHBOARD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "static", "dashboard")

# --- Mobile PWA (installable at /m) ------------------------------------------
# A second, mobile-first surface that reads/writes the same Sheets data through
# the same /api/* endpoints as the desktop dashboard. Additive and isolated: it
# adds no new API endpoints, spends zero Odds-API credits, and never touches the
# run path. Asset references in index.html are root-absolute under /m/, so /m
# (no trailing slash) loads everything correctly. See docs/mobile_pwa_briefing.md.

MOBILE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "static", "mobile")


@app.route("/m")
@require_dashboard_auth
def mobile_index():
    """Serve the mobile PWA shell (installable at /m)."""
    return send_from_directory(MOBILE_DIR, "index.html")


@app.route("/m/<path:filename>")
@require_dashboard_auth
def mobile_asset(filename):
    """Serve the mobile app's static assets (jsx, manifest, icons, vendored libs,
    design system). These specific rules win over the dashboard catch-all below,
    so /m/store.jsx resolves to the mobile copy. send_from_directory blocks path
    traversal; a miss 404s."""
    return send_from_directory(MOBILE_DIR, filename)


@app.route("/")
@require_dashboard_auth
def index():
    """Serve the SPA shell. The app fetches its data from /api/bets + /api/summary
    (which degrade to an error banner on a Sheets problem rather than 500ing)."""
    return send_from_directory(DASHBOARD_DIR, "index.html")


@app.route("/<path:filename>")
@require_dashboard_auth
def dashboard_asset(filename):
    """Serve the SPA's static assets (jsx, bundle, vendored libs, design system).
    More specific routes (/healthz, /api/*, /run/*) win over this catch-all, so
    only genuine asset paths fall through here. send_from_directory blocks path
    traversal; a missing file 404s."""
    return send_from_directory(DASHBOARD_DIR, filename)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
