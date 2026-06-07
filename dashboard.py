"""
dashboard.py — local performance dashboard for betsu.

A single-file Flask app that reads the SQLite tracker and shows the running
record, ROI, a cumulative P&L chart, and a colour-coded table of every bet.
No external services; it just visualises data/betsu.db.

Run:
    python dashboard.py            # serves http://127.0.0.1:5000
    PORT=8080 python dashboard.py  # custom port

Deploying this (e.g. on Railway) is optional and comes later; locally it's the
quickest way to "see performance" without touching Google.
"""

import os
import sys

from flask import Flask, render_template_string

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tools import tracker as tracker_mod

app = Flask(__name__)

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
  <div class="sub">Paper-traded unless flagged real. Source: data/betsu.db</div>

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
        <td>{{ '%.2f'|format(b.odds) }}</td>
        <td>{{ '%.0f'|format(b.model_prob * 100) }}%</td>
        <td class="{{ 'pos' if b.edge > 0 else 'muted' }}">{{ '%+.1f'|format(b.edge * 100) }}%</td>
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
def index():
    tracker_mod.init_db()
    bets = tracker_mod.fetch_bets()
    s = tracker_mod.summary()
    labels, values = _pnl_curve(bets)
    return render_template_string(
        TEMPLATE, s=s, bets=bets, curve_labels=labels, curve_values=values)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
