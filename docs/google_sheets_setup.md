# Google Sheets store — one-time setup

Google Sheets is betsu's **single source of truth** (there is no local database).
The tracker reads and writes four tabs: **Bets**, **Results**, **Matches**, and
**Summary**. You can watch performance from your phone, and — because the sheet is
the hub — type final scores straight into the **Results** tab for grading.

betsu runs headless (locally and on Railway), so it authenticates with a Google
Cloud **service account**, not your personal login. You set this up once. Budget
~10 minutes.

## 1. Create a Google Cloud project

1. Go to https://console.cloud.google.com and sign in.
2. Top bar → project dropdown → **New Project**. Name it e.g. `betsu`. Create,
   then select it.

## 2. Enable the two APIs

In the project, open **APIs & Services → Library** and enable both:

- **Google Sheets API**
- **Google Drive API**

(Search each by name, click **Enable**.)

## 3. Create the service account + key

1. **APIs & Services → Credentials → Create credentials → Service account**.
2. Name it e.g. `betsu-writer`. Create and continue, skip the optional
   role/grant steps, click **Done**.
3. Click the new service account → **Keys** tab → **Add key → Create new key →
   JSON**. A `.json` file downloads. This is the credential.
4. For **local** use, copy that file into the betsu project root and rename it
   `credentials.json` (it is gitignored — never commit or share it).
5. Open the file and copy the `client_email` value — it looks like
   `betsu-writer@betsu-xxxx.iam.gserviceaccount.com`. You need it in step 5.

## 4. Create the sheet

1. Create a new Google Sheet (any name, e.g. `betsu tracker`).
2. From its URL, copy the **spreadsheet ID** — the long string between
   `/d/` and `/edit`:
   `https://docs.google.com/spreadsheets/d/`**`THIS_IS_THE_ID`**`/edit`

You don't need to make any tabs — betsu creates Bets / Results / Matches /
Summary automatically on first use.

## 5. Share the sheet with the service account

In the sheet, click **Share**, paste the service account's `client_email` from
step 3, give it **Editor**, and send. (No real person receives anything; this
just grants the bot write access.)

## 6. Point betsu at it

In your `.env` (local):

```
GOOGLE_SHEETS_ID=THE_ID_FROM_STEP_4
GOOGLE_CREDENTIALS_PATH=credentials.json
```

For **deployment** (Railway), there is no key file — paste the full JSON into an
env var instead, which takes precedence over the file path:

```
GOOGLE_CREDENTIALS_JSON={ ...the entire service-account JSON... }
```

Install the deps if you haven't: `pip install -r requirements.txt`.

## 7. Verify

```bash
python tools/tracker.py status    # should say "Store ON — sheet <id>, key credentials.json."
python tools/tracker.py init      # ensures the Bets/Results/Matches/Summary tabs exist
python tools/tracker.py summary   # prints the running record (empty at first)
```

Open the sheet — you should see the tabs. From then on every run (`run_daily.py`,
or the `/run/morning` and `/run/grade` endpoints) reads and writes them directly.

## Notes

- **The sheet is the store, not a mirror.** Edits stick. In particular you can
  type final scores into the **Results** tab (`home_score`, `away_score`) and the
  next `/run/grade` settles the matching bets.
- **Schema upgrades are safe.** If a tab exists but is empty with an outdated
  header (e.g. a Bets tab from the old mirror), betsu rewrites the header to the
  current schema on first use. If a tab already holds data under a mismatched
  header, betsu refuses to append (to avoid misaligning columns) and asks you to
  clear or recreate that tab — your data is never silently corrupted.
- **Dedup.** A bet is keyed by `(match_date, home, away, market, selection)`, so
  re-running a scan only ever appends genuinely new selections.
