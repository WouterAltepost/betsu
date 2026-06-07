# Google Sheets sync — one-time setup

betsu mirrors its SQLite tracker to a Google Sheet after every run, so you can
watch performance from your phone or anywhere else. SQLite stays the source of
truth; the sheet is rewritten from it each run (three tabs: **Bets**,
**Results**, **Summary**).

The daily run is automated and headless (and will be on Railway), so it
authenticates with a **service account** rather than your personal Google
login. You set this up once. Budget ~10 minutes.

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
4. Copy that file into the betsu project root and rename it `credentials.json`.
   (It is already gitignored, so it will never be committed. Never share it.)
5. Open the file and copy the `client_email` value — it looks like
   `betsu-writer@betsu-xxxx.iam.gserviceaccount.com`. You need it in step 5.

## 4. Create the sheet

1. Create a new Google Sheet (any name, e.g. `betsu tracker`).
2. From its URL, copy the **spreadsheet ID** — the long string between
   `/d/` and `/edit`:
   `https://docs.google.com/spreadsheets/d/`**`THIS_IS_THE_ID`**`/edit`

You don't need to make any tabs — betsu creates Bets / Results / Summary
automatically on first sync.

## 5. Share the sheet with the service account

In the sheet, click **Share**, paste the service account's `client_email` from
step 3, give it **Editor**, and send. (No real person receives anything; this
just grants the bot write access.)

## 6. Point betsu at it

In your `.env`:

```
GOOGLE_SHEETS_ID=THE_ID_FROM_STEP_4
GOOGLE_CREDENTIALS_PATH=credentials.json
```

Install the new deps if you haven't: `pip install -r requirements.txt`.

## 7. Verify

```bash
python tools/sheets.py status     # should say "Sheets sync ON ..."
python tools/sheets.py sync       # pushes current DB state to the sheet
```

Open the sheet — you should see the three tabs populated. From now on every
`python run_daily.py` and `python run_daily.py --grade` syncs automatically.

## Notes

- The sync is **optional and fail-safe**: if `GOOGLE_SHEETS_ID` is blank or the
  key is missing, betsu runs exactly as before and just skips the sync.
- A Sheets error never blocks the Telegram card or grading — it's wrapped and
  logged, not raised.
- The sheet is a **mirror**: betsu overwrites the three tabs each run, so don't
  hand-edit them expecting edits to stick. Use the SQLite DB (or add columns in
  new tabs) if you want notes that persist.
