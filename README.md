# NSE Onm/Decider Breakout Screener (Upstox + Streamlit)

Compares live NSE prices against yesterday's High/Low-derived "onm" (×0.146)
and "decider" (×0.236) extension levels and flags breakouts/breakdowns —
same logic as the original Excel sheet, now live and hosted.

## What you need before you start

1. An **Upstox trading account** (the API is tied to a real Upstox account).
2. A **developer app** registered at https://developer.upstox.com/ (or Upstox
   Developer Apps page from your account). This gives you an API Key
   (client_id) and API Secret (client_secret).
3. Confirm your app has **Market Data Feed** access if you want the live LTP
   to work — some plans/apps need this explicitly enabled and it may carry a
   fee. The previous-day High/Low (Historical Candle API) does not need this.
4. A **GitHub account** and a **Streamlit Community Cloud** account
   (streamlit.io/cloud, free tier is fine) — or you can run it locally.

## Getting a daily access token (the part that can't be fully automated)

Upstox access tokens expire every night (~3:30am IST). For a personal
screener like this, the simplest approach — explicitly supported by Upstox
for "small utility" apps — is:

1. Go to your app on the Upstox Developer Apps page.
2. Click **Generate** to create a fresh access token.
3. Copy it and paste it into the app's sidebar each trading day (or into
   Streamlit secrets if you're the only user — see below).

If you want a fully unattended login (no daily copy/paste), you'd need to
implement the full OAuth redirect flow (login dialog → auth code → token
exchange) with a public redirect URI, which is a bigger project than this
screener — happy to build that next if you want it.

## Project structure

```
upstox_screener/
├── app.py              # Streamlit UI
├── upstox_data.py       # Upstox API calls (instrument lookup, OHLC, LTP)
├── levels.py             # onm/decider ladder math (mirrors the Excel formulas)
├── tickers.csv           # editable list of tickers to screen
├── requirements.txt
├── .streamlit/
│   └── secrets.toml.example
└── .gitignore
```

## Run locally

```bash
git clone <your-repo-url>
cd upstox_screener
pip install -r requirements.txt
streamlit run app.py
```

Paste your access token into the sidebar field when the app opens.

## Deploy for free on Streamlit Community Cloud

1. Push this folder to a **new GitHub repository**.
2. Go to https://share.streamlit.io → **New app** → pick your repo/branch →
   set main file to `app.py` → Deploy.
3. (Optional, for personal use only) In the app's **Settings → Secrets**,
   add:
   ```
   UPSTOX_ACCESS_TOKEN = "todays-token"
   ```
   This pre-fills the sidebar field so you don't have to paste it in the UI,
   but you'll still need to update it there each day since it expires
   nightly. **Never commit a real token to the GitHub repo itself** —
   only Streamlit's Secrets manager, which isn't part of the repo.

## Editing the ticker list

- Quick/temporary: use the "Edit ticker list" expander in the app.
- Permanent: edit `tickers.csv` in the repo (one ticker per line, matching
  the exact NSE trading symbol) and redeploy/push. `NIFTY` and `BANKNIFTY`
  are handled specially as indices; everything else is looked up against
  Upstox's NSE instrument master by trading symbol.

## How the signal works

For each ticker, using yesterday's High/Low:

- `diff = High − Low`
- `onm level = High + diff×0.146` (and mirrored below Low)
- `decider level = High + diff×0.236` (and mirrored below Low)

The Screener flags:
- **BREAKOUT above Decider** — live price above the decider level over High
- **Above Onm (watch)** — live price above the onm level but below decider
- **BREAKDOWN below Decider** — live price below the decider level under Low
- **Below Onm (watch)** — live price below the onm level but above decider
- **Neutral / inside range** — otherwise

The "Full ladder" expander shows all 10 extension rungs on each side, same
as the extended columns in the original Excel sheet, in case you use those
further targets too.

## Caveats

- This is a **technical price-level screener, not investment advice**.
- Upstox's public instrument master and APIs occasionally change shape or
  rate-limit; if a ticker shows "No prev-day data" or a fetch error, hit
  Refresh, or check Upstox's API status page.
- "Previous day" always means the last **complete** daily candle — if you
  load the app mid-session, that's the prior trading day as intended.
