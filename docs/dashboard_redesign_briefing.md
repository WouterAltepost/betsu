# Dashboard redesign + placed-bet tracking — implementation briefing

**For:** Claude Code (CC). **From:** architect (Cowork). **Date:** 2026-06-08.
**Status:** ready to build. Tournament opens 2026-06-11, so land this in clean,
per-phase commits before then.

## 1. What we're building and why

We're replacing the server-rendered Jinja dashboard (the `TEMPLATE` string in
`app.py`) with the React redesign in `docs/redesign_src/` (the unzipped bundle,
see section 9 for where to put it). The redesign also introduces one real new
feature: **the user records which suggested bets they actually placed, the € stake
on each, and (as a fallback) settles them**, and every headline number on the
Performance page is derived from those placed bets in euros.

Today the app is paper-only: flat 1-unit stakes, P&L in units. The redesign drops
all "paper / units" language from the user-facing surfaces and tracks real money.

### Four decisions already made by the user (build to these)

1. **Settlement = hybrid.** Auto-grade from the football-data feed stays the
   default (the user only ticks *placed* and sets a *stake*). A manual Win/Loss
   override is available in the UI and auto-grading must never overwrite it. This
   mirrors how a hand-typed score already overrides the feed in `results_fetch`.
2. **Scope = project-wide.** The shift away from paper language reaches the
   Telegram card, `run_daily`, `config.py`, `CLAUDE.md`, and the design-system
   readme, not just the web dashboard.
3. **Architecture = SPA + Sheets write API.** Serve the React app as static
   files; add small, auth-gated JSON endpoints that read state and write
   *placed / stake / manual_result* back to the Sheets `Bets` tab. Sheets stays
   the single source of truth (the prototype's `localStorage` store is replaced).
4. **Evaluation = keep both.** Real € placed-bet P&L is the headline, but we
   retain a model-performance view (calibration + paper-units ROI over **all**
   suggestions, not just placed ones), because that is what the project was set up
   to judge betsu on.

### How decisions 2 and 4 reconcile (read this before touching anything)

"Remove paper trading" and "keep both" are not in tension. We are **not** deleting
the units machinery. We are:

- **relabelling** every user-facing surface (dashboard, Telegram card, copy in
  docs) from "paper / units" to real euros on placed bets, and
- **keeping** `stake_units` / `pnl_units` internally as the *model-evaluation
  track* that powers the "Model performance" panel and the calibration the project
  is judged on.

So `FLAT_STAKE_UNITS`, `pnl_units`, and the units-based `summary()` survive as the
internal paper benchmark. The new € fields sit alongside them. Nothing that
currently runs in production changes behaviour until the new fields are populated.

## 2. Hard constraints (do not break these)

- **Odds API budget.** This change touches no odds calls. Keep `ODDS_MARKETS =
  "h2h,totals"` and the BTTS per-event cache exactly as they are. Do not add any
  odds fetch to the dashboard or the write API.
- **Stateless service.** `app.py` stays stateless on Railway. The write API reads
  and writes Sheets directly; no in-process state, no background worker.
- **Sheets is the store.** No local DB, no JSON file of bet state. Placed / stake
  / manual_result live in the `Bets` tab.
- **Fail-safe.** A dashboard or write-API failure must never affect `/run/morning`
  or `/run/grade`. Keep the new routes isolated and defensive (the dashboard
  already degrades to a banner on a Sheets error; preserve that).
- **Secrets.** No new secrets in git. If the write API needs auth config it reuses
  the existing `DASHBOARD_USER` / `DASHBOARD_PASSWORD` (see section 6).
- **Verify before done** (section 10): `py_compile`, offline tests, and a dry-run.

## 3. Data model: `Bets` tab schema change

Current `BETS_HEADERS` (tracker.py) ends with `... staked_real, result, pnl_units,
created_at`. Note `staked_real` already exists and is already plumbed through
`_bet_row` and `_typed_bet` as an int. **Reuse it as the € stake.**

**Add three columns, appended after `created_at`** (append at the end so existing
column positions are untouched):

| New column      | Type        | Meaning |
|-----------------|-------------|---------|
| `placed`        | "1" or ""   | User ticked that they actually placed this bet |
| `manual_result` | win/loss/"" | User's manual settle; overrides the auto `result`, never overwritten by grading |
| `pnl_eur`       | float or "" | Real euro P&L for a settled placed bet |

Keep `staked_real` (the € stake), `result` (the auto-graded outcome), `stake_units`
and `pnl_units` (the paper/model track). 

**Effective result helper** (add to tracker.py, use everywhere a settled outcome is
read): `effective_result(bet) = bet["manual_result"] or bet["result"] or "pending"`.

### Migration (important: the header guard will trip)

`tracker._values()` raises if `row 1 != headers` while data rows exist. The live
`Bets` tab holds pre-tournament **test** data under the old header, so changing
`BETS_HEADERS` will hard-fail until the sheet is reconciled. Because it is only
test data and we are pre-tournament, the clean path is:

1. Update `BETS_HEADERS` in tracker.py (and the `_FLOAT_BET_COLS` set: add
   `pnl_eur`).
2. Clear the `Bets` tab in the Google Sheet (delete all rows including the header),
   then run `python tools/tracker.py init` to recreate it with the new header.
3. Re-run a windowed dry-run, then a real scan, to repopulate.

Document this in the commit message so it is not a surprise on deploy.

## 4. Backend: tracker.py additions

Add one write function and one effective-result helper. Keep the existing
`record_bets` / `grade_pending` / `summary` working unchanged for the paper track.

```python
def update_bet_user_fields(key, placed=None, stake_eur=None, manual_result=None):
    """Locate a bet row by its BET_KEY_COLS tuple and update only the user-owned
    fields (placed / staked_real / manual_result). Recomputes pnl_eur when the
    bet is settled and a stake is known. Batched single-row update; clears cache.
    No-ops cleanly if the key is not found (returns False)."""
```

- Locate the row the same way `record_result` does (iterate `_dicts(vals)`, match
  on `_key(d, BET_KEY_COLS)`, update by A1 range).
- `pnl_eur` recompute: when `effective_result` is win/loss and `staked_real > 0`,
  `pnl_eur = staked_real * (odds - 1)` if win else `-staked_real`. Else "".
- Cache: call `_cache_clear()` after the write (matches the other upserts).

### grade_pending: respect the manual override + write € P&L

`grade_pending` currently settles `result` + `pnl_units`. Two changes:

1. **Skip rows where `manual_result` is set** (the user override wins; auto-grading
   never clobbers it). It still settles the paper `result` column for the model
   track, but must not touch `manual_result`.
2. When a row is **placed** and gets settled (by feed or already-set manual),
   also write `pnl_eur` from `staked_real` using the same win/loss math. Unplaced
   bets keep `pnl_eur` empty (they are model-track only).

### summary: keep units, add euros

Extend `summary()` to also return a real-money block computed over **placed**
bets using `effective_result` and `staked_real`:

```
real = {
  placed, staked_eur, open_exposure_eur, settled, wins, losses,
  pnl_eur, roi_eur_pct, hit_rate, avg_edge_pct, pending
}
```

Keep the existing units keys for the model track and the Summary tab. The
dashboard reads `real` for the headline and the units keys for the model panel.

## 5. Backend: app.py routes

Replace the inline `TEMPLATE` server-render with static file serving + a small
JSON API. Keep `/healthz`, `/run/morning`, `/run/grade` exactly as they are.

- `GET /` -> serve the redesign's `index.html` (static). Stays behind
  `require_dashboard_auth`.
- Static assets (`/assets/...`, the `_ds/...` bundle, the `.jsx`/bundled JS,
  `data`-replacement) served from the static dir (Flask `static_folder` or a
  catch-all route). Also behind dashboard auth.
- `GET /api/bets` -> JSON array of all bets, typed, shaped for the SPA (field map
  in section 8). This replaces `data.js`. Include `effective_result` as `outcome`
  and the user fields `placed` / `stake`. Degrade like `index()` does: on a Sheets
  error return `{"error": "..."}` with 200 so the SPA can show a banner, not a 500.
- `GET /api/summary` -> the `summary()` dict (both `real` and units blocks). The
  SPA may compute most numbers client-side from `/api/bets` via `computePerf`;
  expose `/api/summary` anyway for the model-track numbers and as a cross-check.
- `POST /api/bets/update` -> body `{key: {match_date, home_team, away_team, market,
  selection}, placed?, stake?, manual_result?}`. Calls
  `tracker.update_bet_user_fields(...)`. Returns the updated bet. Behind dashboard
  auth. Validate inputs (stake >= 0 numeric; manual_result in {win, loss, ""}).

Use the bet key tuple as identity, not row index (rows re-sort). The SPA already
has the five key fields per bet.

## 6. Auth on the write API

Gate `/api/*` with the **same** `require_dashboard_auth` as the dashboard, so a
logged-in dashboard session can write. Do not invent a new secret. Notes:

- If `DASHBOARD_USER` / `DASHBOARD_PASSWORD` are unset (local dev) the API is open,
  same as the dashboard is today. Acceptable for local.
- This is a single-user personal tool behind Basic Auth, so CSRF risk is low;
  do not over-engineer. A simple same-origin write API is fine.

## 7. Frontend: what to keep, strip, and rewire

The bundle is a design-exploration prototype. Ship one clean app.

**Strip:**

- `tweaks-panel.jsx` entirely, and the `TweaksPanel` / `TweakCtx` wiring in
  `app.jsx`. Hardcode the chosen design: `layout = editorial`, `gradient =
  balanced`, `density = comfortable`. (Defaults already set in `app.jsx`; the user
  can revisit later.)
- `layouts.jsx`: keep `LayoutEditorial` + `Overview`; drop `LayoutCockpit` and
  `LayoutBrand`. Keep `dens()` returning the comfortable branch (or inline the
  comfortable values).
- The "Reset demo data" button and `seedState()` random history in `store.jsx`.
- `data.js` (the seeded random catalog) is replaced by `GET /api/bets`.

**Rewire `store.jsx` from localStorage to the API:**

- On load, fetch `GET /api/bets` into the catalog; derive `today` (bets whose
  `match_date` is today or within the scan window) and `played` (bets with a
  non-null `outcome`, i.e. an effective result) from it.
- `place(id, on)`, `setStake(id, amt)`, `settle(id, result)`, `unsettle(id)` keep
  their signatures but: update local state optimistically (so the UI stays
  instant), then POST to `/api/bets/update` (**debounced ~600ms for the stake
  input** so typing does not fire a Sheets write per keystroke). On a write error,
  revert the optimistic change and surface a small toast/banner.
- `computePerf` stays as the derivation engine (it already produces €
  placed-only numbers). For "keep both," add a second derivation over **all**
  catalog bets (placed or not) for the model panel: calibration bins and paper ROI
  using `model` / `outcome` across every suggestion, not just placed ones. Surface
  it on the Performance page as a "Model performance" panel beneath the real-money
  hero (a small toggle or a labelled section is fine; do not bury the distinction:
  label one "Your money" and one "Model (all suggestions, paper)").

**Keep as-is (they already read from the store/computePerf):** `modules.jsx`
(`Header`, `VerdictHero`, `StatStrip`, `BetLog`, `TodayView`, `StakeInput`,
`PlaceControl`), `allbets.jsx`, `charts.jsx`, `util.jsx`. The "Send card" /
"Send to Telegram" buttons in `modules.jsx` are currently inert; either wire them
to a new auth-gated `POST /api/send-card` that calls the existing run, or hide them
for v1. Recommend **hide for v1** to keep the diff small (note it as a follow-up).

## 8. Field map: Sheets `Bets` row -> SPA bet object

`GET /api/bets` returns objects in this shape (the SPA's `data.js` contract):

| SPA field   | Source (Bets tab)                          |
|-------------|--------------------------------------------|
| `id`        | stable hash of the key tuple (compute server-side, send it) |
| `date`      | `match_date` (the SPA shows it as-is; keep `MM-DD` or send ISO and format client-side, pick one and be consistent) |
| `home`      | `home_team`                                |
| `away`      | `away_team`                                |
| `market`    | `market`                                   |
| `pick`      | `selection_label` or `selection`           |
| `odds`      | `odds` (float)                             |
| `model`     | `model_prob` (0..1)                         |
| `market_p`  | `implied_prob`                             |
| `edge`      | `edge`                                      |
| `kelly`     | `kelly_units`                              |
| `outcome`   | `effective_result` mapped to win/loss/null |
| `played`    | true if `outcome` is win/loss OR kickoff is in the past |
| `note`      | `context_note` if present                  |
| `placed`    | `placed` == "1"                            |
| `stake`     | `staked_real` (int €)                       |
| `result`    | `effective_result` (win/loss/pending)      |

Also send `key` (the five-field object) on each bet so the SPA can POST updates
without reconstructing it.

## 9. Where the redesign source goes

The unzipped bundle currently lives in the session scratch. Vendor it into the
repo so the deploy stays pure-Python (no Node build, no runtime CDN dependency):

- Put the app under `static/dashboard/` (or `web/`): `index.html`, the `.jsx`
  files, `betsu-bundle.js`, `assets/`, and the `_ds/.../` design-system folder.
- **Vendor the external libs** (react, react-dom, @babel/standalone, chart.js,
  lucide) into `static/dashboard/vendor/` and point `index.html` at the local
  copies instead of unpkg/jsdelivr. Rationale: the project values reliability and
  a Railway pure-Python deploy; a runtime CDN dependency on every dashboard load is
  a fragility we do not want, and a Node build step complicates the deploy.
- This keeps Babel-in-browser compile (a ~1s cost on each load, acceptable for a
  single-user dashboard). **Tradeoff flagged:** if that load cost ever annoys, a
  follow-up can precompile the `.jsx` to one JS file with esbuild; out of scope
  for v1 to avoid adding a Node toolchain to the Railway build.

## 10. Project-wide copy + behaviour (decision 2)

Keep the units track internal; relabel the user-facing surfaces:

- **`message.py`**: drop `"Paper unless you choose to back it."`. The morning card
  is pre-placement suggestions, so keep model% / edge / odds, and change the
  `Stake: 1u (...)` line to a euro quarter-Kelly guide using `BANKROLL_EUR` (see
  config below). The running line and `build_results_recap` switch from
  `pnl_units` / units ROI to the real € block (`pnl_eur`, `roi_eur_pct`) from the
  new `summary()`; fall back to "no settled placed bets yet" when empty.
- **`config.py`**: add `BANKROLL_EUR = int(os.environ.get("BANKROLL_EUR", "1000"))`
  for the € quarter-Kelly guide (the prototype assumed 1000). Keep
  `FLAT_STAKE_UNITS` and `KELLY_FRACTION` (model track + Kelly math).
- **`CLAUDE.md`** and the design-system `readme.md`: update the stance language so
  it reflects the dual framing: betsu is judged on model calibration + ROI vs the
  closing line (paper, all suggestions), and the user separately tracks real €
  P&L on the bets they place. Do not claim everything is paper-traded anymore.
- **`run_daily.py`**: no logic change required (it records suggestions; placement
  is a dashboard action). Only adjust any user-facing print/log copy that says
  "paper".

## 11. Build order (one commit per phase, keep diffs clean)

1. **Schema + tracker** (section 3, 4): headers, `effective_result`,
   `update_bet_user_fields`, `grade_pending` override + `pnl_eur`, `summary` real
   block. Plus the Sheets migration step. Unit-testable offline.
2. **API** (section 5, 6): `/api/bets`, `/api/summary`, `/api/bets/update`, auth.
   Smoke-test with curl against a test sheet.
3. **Frontend vendoring + serve** (section 9): drop the bundle in `static/`,
   vendor libs, switch `app.py` `GET /` to serve it. Confirm it renders.
4. **Frontend rewire** (section 7, 8): store -> API, strip tweaks/extra layouts,
   add the model-performance panel, debounce stake writes.
5. **Project-wide copy** (section 10): message.py, config, CLAUDE.md, readme.

## 12. Verification (before calling anything done)

- `python -m py_compile app.py run_daily.py tools/tracker.py tools/message.py
  config.py` clean.
- Offline tests in `tests/` pass (run the suite; add a test for
  `update_bet_user_fields` row-matching and for `effective_result` /
  `grade_pending` not clobbering a `manual_result`).
- `python run_daily.py --window --dry-run` builds a card and sends nothing,
  with the new euro copy and no "paper" language.
- Dashboard smoke test: load `/`, tick a bet placed, set a stake, confirm it
  writes to the `Bets` tab and the headline € P&L updates; set a manual Win,
  run `--grade`, confirm grading did not overwrite the manual result.
- Confirm `/run/morning` and `/run/grade` are byte-for-byte unaffected by the
  dashboard changes (the model/paper track still records and grades).

## 13. Open follow-ups (note, do not build in v1)

- Wire the "Send card" / "Send to Telegram" buttons to an auth-gated endpoint.
- Optional esbuild precompile to drop the in-browser Babel cost.
- Consider a `result_source` audit column if you later want to show whether each
  settle was auto or manual.
