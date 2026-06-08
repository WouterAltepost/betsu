# Mobile PWA — runbook

The mobile app is a second, mobile-first surface for betsu. It lives at **`/m`**
on the same Flask service and reads/writes the same Google Sheets data through the
same `/api/*` endpoints as the desktop dashboard at `/`. Sheets is the single
source of truth — there is no localStorage and no demo data.

- **Files:** `static/mobile/` (vendored libs under `vendor/`, design system under
  `_ds/`, icons under `assets/`). No runtime CDN.
- **Routes:** `GET /m` (shell) and `GET /m/<path>` (assets), both gated by the
  same `DASHBOARD_USER` / `DASHBOARD_PASSWORD` Basic Auth as `/`. Asset references
  in `index.html` are root-absolute under `/m/`, so `/m` (no trailing slash) loads
  everything correctly — no `/m` vs `/m/` ambiguity.
- **PWA scope:** installable only — a web app manifest + Apple meta tags + an app
  icon. **No service worker, no offline cache** (data is live from Sheets). With
  no signal, the app shows its error banner; that is the intended behaviour.
- **Built from:** the approved prototype at `docs/mobile_src/` (Direction A —
  editorial / condensed ledger). The demo `data.js` and the fake iPhone bezel
  (`frames/ios-frame.jsx`) are deliberately not shipped. See
  `docs/mobile_pwa_briefing.md` for the full build spec.

## Add to home screen (iOS Safari)

1. Open `https://<your-railway-host>/m` in Safari and sign in (Basic Auth).
2. Tap **Share** → **Add to Home Screen** → **Add**.
3. Launch from the new icon: it opens fullscreen (standalone), clearing the notch
   and home indicator via iOS safe-area insets.

On Chrome (Android/desktop), the install prompt appears under the address-bar
menu / "Install app".

## Local dev

```bash
python app.py            # http://127.0.0.1:5000/m
```

Then in the browser at ~390px wide (device emulation): the three tabs
(Performance · Today · All bets) render, placing a bet and nudging the stepper
writes through to Sheets (`POST /api/bets/update`), and a failed write reverts
with a toast. Confirm no requests hit any CDN — everything loads from `/m/...`.

## What it does NOT touch

`/run/morning`, `/run/grade`, `run_daily.py`, odds fetching, the Odds-API budget,
the `/api/*` shapes, or the desktop dashboard at `/`. It is purely additive.
