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
import os
import sys
from datetime import date, datetime, timezone
from functools import wraps

from flask import Flask, Response, jsonify, render_template_string, request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_daily
from config import SCAN_WINDOW_HOURS
from tools import tracker as tracker_mod

app = Flask(__name__)

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
        "market": bet.get("market"),
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


# --- Dashboard --------------------------------------------------------------

TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>betsu — performance</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root { color-scheme: dark; }
    body { font-family: -apple-system, system-ui, sans-serif; margin: 0;
           background: #0e1116; color: #e6e6e6; }
    .wrap { max-width: 1000px; margin: 0 auto; padding: 24px 16px 64px; }
    h1 { font-size: 22px; margin: 0 0 4px; }
    .sub { color: #8b949e; font-size: 13px; margin-bottom: 24px; }
    .banner { background: #3d1418; border: 1px solid #f85149; color: #f8d7da;
              border-radius: 8px; padding: 12px 16px; margin-bottom: 24px;
              font-size: 14px; }
    .cards { display: grid; grid-template-columns: repeat(auto-fit,minmax(150px,1fr));
             gap: 12px; margin-bottom: 28px; }
    .card { background: #161b22; border: 1px solid #21262d; border-radius: 10px;
            padding: 14px 16px; }
    .card .label { color: #8b949e; font-size: 12px; text-transform: uppercase;
                   letter-spacing: .04em; }
    .card .value { font-size: 26px; font-weight: 600; margin-top: 4px; }
    .pos { color: #3fb950; } .neg { color: #f85149; } .muted { color: #8b949e; }
    .chart-box { background: #161b22; border: 1px solid #21262d; border-radius: 10px;
                 padding: 16px; margin-bottom: 28px; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { padding: 8px 10px; text-align: left; border-bottom: 1px solid #21262d; }
    th { color: #8b949e; font-weight: 600; position: sticky; top: 0; background: #0e1116; }
    tr:hover td { background: #11161d; }
    .pill { padding: 2px 8px; border-radius: 999px; font-size: 11px; font-weight: 600; }
    .win { background: #12331f; color: #3fb950; }
    .loss { background: #3a1717; color: #f85149; }
    .pending { background: #2d2410; color: #d29922; }
    .empty { color: #8b949e; padding: 40px 0; text-align: center; }
  </style>
</head>
<body>
<div class="wrap">
  <h1>⚽ betsu — performance</h1>
  <div class="sub">Paper-traded unless flagged real. Source: Google Sheets</div>
  {% if error %}
  <div class="banner">Store unreachable: {{ error }}</div>
  {% endif %}

  <div class="cards">
    <div class="card"><div class="label">Record (W-L)</div>
      <div class="value">{{ s.wins }}-{{ s.losses }}</div></div>
    <div class="card"><div class="label">Hit rate</div>
      <div class="value">{{ s.hit_rate }}%</div></div>
    <div class="card"><div class="label">P&amp;L (units)</div>
      <div class="value {{ 'pos' if s.pnl_units > 0 else 'neg' if s.pnl_units < 0 else 'muted' }}">
        {{ '%+.2f'|format(s.pnl_units) }}</div></div>
    <div class="card"><div class="label">ROI</div>
      <div class="value {{ 'pos' if s.roi_pct > 0 else 'neg' if s.roi_pct < 0 else 'muted' }}">
        {{ '%+.1f'|format(s.roi_pct) }}%</div></div>
    <div class="card"><div class="label">Pending</div>
      <div class="value muted">{{ s.pending }}</div></div>
  </div>

  {% if curve_labels %}
  <div class="chart-box"><canvas id="pnl"></canvas></div>
  {% endif %}

  <table>
    <thead><tr>
      <th>Date</th><th>Match</th><th>Market</th><th>Pick</th>
      <th>Odds</th><th>Model</th><th>Edge</th><th>Result</th><th>P&amp;L</th>
    </tr></thead>
    <tbody>
    {% for b in bets %}
      <tr>
        <td>{{ b.match_date }}</td>
        <td>{{ b.home_team }} vs {{ b.away_team }}</td>
        <td>{{ b.market }}</td>
        <td>{{ b.selection_label or b.selection }}</td>
        <td>{{ '%.2f'|format(b.odds) if b.odds is not none else '—' }}</td>
        <td>{{ '%.0f'|format(b.model_prob * 100) if b.model_prob is not none else '—' }}%</td>
        <td class="{{ 'pos' if (b.edge or 0) > 0 else 'muted' }}">{{ '%+.1f'|format((b.edge or 0) * 100) }}%</td>
        <td><span class="pill {{ b.result }}">{{ b.result }}</span></td>
        <td class="{{ 'pos' if (b.pnl_units or 0) > 0 else 'neg' if (b.pnl_units or 0) < 0 else 'muted' }}">
          {{ '%+.2f'|format(b.pnl_units) if b.pnl_units is not none else '—' }}</td>
      </tr>
    {% else %}
      <tr><td colspan="9" class="empty">No bets recorded yet. Run a morning card first.</td></tr>
    {% endfor %}
    </tbody>
  </table>
</div>

{% if curve_labels %}
<script>
  new Chart(document.getElementById('pnl'), {
    type: 'line',
    data: {
      labels: {{ curve_labels|tojson }},
      datasets: [{
        label: 'Cumulative P&L (units)',
        data: {{ curve_values|tojson }},
        borderColor: '#3fb950', backgroundColor: 'rgba(63,185,80,.12)',
        fill: true, tension: .2, pointRadius: 2
      }]
    },
    options: {
      plugins: { legend: { labels: { color: '#e6e6e6' } } },
      scales: {
        x: { ticks: { color: '#8b949e' }, grid: { color: '#21262d' } },
        y: { ticks: { color: '#8b949e' }, grid: { color: '#21262d' } }
      }
    }
  });
</script>
{% endif %}
</body>
</html>
"""


def _pnl_curve(bets):
    """Cumulative settled P&L over time, for the chart."""
    labels, values, running = [], [], 0.0
    for b in bets:
        if b.get("result") in ("win", "loss") and b.get("pnl_units") is not None:
            running += b["pnl_units"]
            labels.append(f"{b['match_date']} {b['home_team'][:3]}-{b['away_team'][:3]}")
            values.append(round(running, 2))
    return labels, values


@app.route("/")
@require_dashboard_auth
def index():
    # The Sheets store is opened lazily here; a creds/sharing problem must be
    # diagnosable from the browser (a banner) rather than collapsing to a 500.
    error = None
    try:
        bets = tracker_mod.fetch_bets()
        s = tracker_mod.summary()
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        bets = []
        s = {"settled": 0, "wins": 0, "losses": 0, "pending": 0,
             "hit_rate": 0.0, "pnl_units": 0.0, "roi_pct": 0.0}
    labels, values = _pnl_curve(bets)
    return render_template_string(
        TEMPLATE, s=s, bets=bets, curve_labels=labels, curve_values=values,
        error=error)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
