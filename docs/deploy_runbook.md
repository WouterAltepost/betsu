# Deploy runbook — Railway + n8n

betsu deploys as one stateless Flask service (gunicorn) on Railway. Google Sheets
is the store; **n8n** owns scheduling and calls the service's run endpoints. No
volume, no in-process scheduler, no SQLite.

Prerequisite: the Google Sheets store is set up (see `google_sheets_setup.md`)
and you have the spreadsheet id + the service-account JSON.

## Endpoints the service exposes

| Method + path     | Auth                          | Does |
|-------------------|-------------------------------|------|
| `GET  /healthz`   | none                          | liveness (200 `ok`); no Sheets call |
| `GET  /`          | Basic Auth (dashboard creds)  | performance dashboard |
| `POST /run/morning` | `X-Run-Key: <RUN_API_KEY>` (or `?key=`) | windowed scan → post only new value bets |
| `POST /run/grade`   | `X-Run-Key: <RUN_API_KEY>` (or `?key=`) | settle pending bets vs the Results tab → recap |

Runs are synchronous (a few seconds). A second immediate `/run/morning` posts
nothing new (dedup), so retries are safe.

## 1. Railway

1. **New Project → Deploy from GitHub repo** → `WouterAltepost/betsu`. **No volume.**
2. Railway reads the `Procfile`:
   `web: gunicorn app:app --workers 2 --timeout 120 --bind 0.0.0.0:$PORT`
3. **Variables** → add the environment variables in the table below.
4. Deploy. Open the service URL → you should get the dashboard (Basic-Auth prompt
   if you set dashboard creds). Hit `/healthz` → `ok`.

### Environment variables

| Var | Note |
|---|---|
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | existing secrets |
| `ODDS_API_KEY`, `ANTHROPIC_API_KEY` | existing secrets |
| `GOOGLE_SHEETS_ID` | the tracker spreadsheet id |
| `GOOGLE_CREDENTIALS_JSON` | the **full** service-account JSON, pasted as one value |
| `RUN_API_KEY` | shared secret n8n sends on the run endpoints |
| `DASHBOARD_USER`, `DASHBOARD_PASSWORD` | dashboard login (omit for an open dashboard) |
| `SCAN_WINDOW_HOURS` | optional, default 18 |
| `PORT` | Railway provides it automatically |

The deployed service has **no key file** — it authenticates from
`GOOGLE_CREDENTIALS_JSON`. (Locally, a `credentials.json` file works instead.)

## 2. n8n scheduling

Create three workflows (or one with three Schedule triggers). Activate them
**only for the tournament window (June 11 – July 19, 2026)** so no odds credits
are spent off-season — this replaces any in-app date guard.

**Morning + evening scan** — two Schedule triggers (≈09:00 and ≈20:00 Amsterdam):
- Node: **HTTP Request**
- Method `POST`, URL `https://<your-service>.up.railway.app/run/morning`
- Header `X-Run-Key: <RUN_API_KEY>`
- Two runs/day cover an afternoon→~03:00 slate: a 03:00 game is posted from the
  previous evening's run, well before kickoff (each run looks `SCAN_WINDOW_HOURS`
  ahead and dedup means nothing is double-posted).

**Grade** — one Schedule trigger (≈10:00 Amsterdam):
- **HTTP Request**, `POST .../run/grade`, header `X-Run-Key: <RUN_API_KEY>`.
- Grading needs final scores in the **Results** tab. Type scores straight into
  the sheet (it's the hub now), or wire football-data.org auto-results later.

Each run returns a small JSON summary (`matches`, `new_bets`, `sent` /
`settled`) you can log or branch on in n8n.

## 3. Smoke test (after deploy)

```bash
curl -s https://<service>/healthz                                  # -> ok
curl -s -X POST https://<service>/run/morning -H "X-Run-Key: WRONG"   # -> 401
curl -s -X POST https://<service>/run/morning -H "X-Run-Key: $RUN_API_KEY"  # -> {"ok":true,...}
curl -s -X POST https://<service>/run/morning -H "X-Run-Key: $RUN_API_KEY"  # -> new_bets:0 (dedup)
```

Type a score into the Results tab, then `POST /run/grade` → the matching bets
settle (`result` + `pnl_units` fill in) and a recap hits Telegram.

## Credit budget

One odds fetch per run = 3 credits (h2h+totals+btts). Two scans/day ≈ 6
credits/day — safe for the whole tournament against the remaining quota.
