# Briefing: fix the Railway 500 (Sheets creds robustness + visible errors)

**For:** Claude Code. **Symptom:** `GET /` returns 500 on Railway; `/healthz` is
200. Root cause is the Google Sheets connection failing at runtime (the dashboard
route is the first thing that opens the store). Works locally with a key file, so
the suspect is the `GOOGLE_CREDENTIALS_JSON` env var.

Make two changes.

## 1. Add base64 credential support (removes paste fragility)

In `tools/tracker.py` `_client()`, before the existing `GOOGLE_CREDENTIALS_JSON`
branch, accept `GOOGLE_CREDENTIALS_B64`: if set, base64-decode it to bytes,
`json.loads` the result, and authorize with
`gspread.service_account_from_dict(...)`. Order of precedence: `B64` -> `JSON`
-> key file. Base64 is a single safe line in a Railway var, immune to the
newline/quote mangling that breaks a raw-JSON paste of a service-account key.

Update `docs/google_sheets_setup.md` deploy section to recommend B64:
generate it locally with `base64 -w0 credentials.json` (macOS: `base64 -i
credentials.json | tr -d '\n'`) and paste the output into `GOOGLE_CREDENTIALS_B64`.

## 2. Make the dashboard fail visibly, not with a blank 500

In `app.py` `index()`, wrap the `fetch_bets()` / `summary()` calls in try/except.
On error, still return HTTP 200 with the normal page shell but a clear banner at
the top: "Store unreachable: <exception message>". This way a creds/sharing
problem is diagnosable from the browser instead of an opaque 500, and a transient
Sheets blip doesn't take the page down. Keep `/healthz` exactly as is.

## Acceptance

- With a correct `GOOGLE_CREDENTIALS_B64`, `/` renders the dashboard.
- With creds removed/broken, `/` returns 200 showing the banner with the real
  error (e.g. "PermissionError 403" or "Expecting value: line 1"), not a 500.
- `/run/morning` and `/run/grade` unchanged; they already surface errors as JSON.
- Local runs (key file) still work; precedence B64 -> JSON -> file.

## Note for the user (CC: include in your report)

The same Sheets auth powers the run endpoints, so this fix unblocks the scheduled
runs too, not just the dashboard. After deploying, set `GOOGLE_CREDENTIALS_B64`
in Railway (and you can delete the old `GOOGLE_CREDENTIALS_JSON`).
