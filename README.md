# NSE Onm/Decider Breakout Screener (Upstox + Streamlit, runs on your own computer)

Compares live NSE prices against yesterday's High/Low-derived "onm" (×0.146)
and "decider" (×0.236) extension levels and flags breakouts/breakdowns.

This version is meant to run **on your own computer** — no GitHub, no cloud
deployment. One command (or one double-click) and it opens in your browser.

## What you need first

1. **Python installed.** If you don't have it: go to
   https://www.python.org/downloads/ → download → during install, **tick
   "Add Python to PATH"** (Windows) → Install.
2. **An Upstox trading account + developer app.** See "Getting a daily
   access token" below — same as before, this part doesn't change.

## Running it — the easy way

**Windows:** double-click **`run_windows.bat`**
**Mac:** double-click **`run_mac.command`**
(If Mac blocks it as "unidentified developer": right-click the file → **Open**
→ confirm "Open" in the dialog that pops up. You only need to do this once.)

Either one will:
1. Install the few required packages (only takes time the first run)
2. Launch the app
3. Open your default browser to the app automatically (usually
   `http://localhost:8501`)

**Keep the black terminal window open** while you use the app — closing it
stops the app. To use it again later, just double-click the same file again.

## Running it — the manual way (if you prefer the terminal)

```bash
cd path/to/upstox_screener
pip install -r requirements.txt
streamlit run app.py
```

## Getting a daily access token

Upstox access tokens expire every night (~3:30am IST). Each trading day:

1. Go to your app on the **Upstox Developer Apps** page (developer.upstox.com,
   or via your Upstox account's API/Apps section).
   - First time only: click **Create new app**, give it any name, and for
     **Redirect URI** put something like `https://127.0.0.1` (required field,
     but not actually used for the flow below).
2. Click **Generate** (or "Generate Access Token") on your app's page.
3. Log into Upstox when prompted, copy the token shown.
4. Paste it into the app's sidebar (in your browser) each time you open it.

**Note on live price (LTP):** if the LTP column comes back empty or errors,
check your app's entitlements on the Developer Apps page — Upstox requires
"Market Data Feed" access for live quotes on some plans, separate from the
Historical Candle API (which the previous-day High/Low uses and needs no
extra entitlement).

## Files in this folder

```
app.py               - the Streamlit app itself
upstox_data.py        - talks to Upstox: instrument lookup, prev-day OHLC, live LTP
levels.py              - onm/decider ladder math
tickers.csv            - editable list of tickers to screen
requirements.txt
run_windows.bat         - double-click launcher (Windows)
run_mac.command          - double-click launcher (Mac)
```

## Editing the ticker list

Open `tickers.csv` in any text editor (Notepad, TextEdit) or the app's own
"Edit ticker list" panel. One ticker per line, matching the exact NSE trading
symbol. `NIFTY` and `BANKNIFTY` are handled specially as indices.

## How the signal works

For each ticker, using yesterday's High/Low:
- `diff = High − Low`
- `onm level = High + diff×0.146` (mirrored below Low)
- `decider level = High + diff×0.236` (mirrored below Low)

The Screener flags:
- **BREAKOUT above Decider** — live price above the decider level over High
- **Above Onm (watch)** — above onm but below decider
- **BREAKDOWN below Decider** — live price below the decider level under Low
- **Below Onm (watch)** — below onm but above decider
- **Neutral / inside range** — otherwise

A **PrevDate** column shows the exact calendar date each row's High/Low came
from, so you can verify at a glance it's using yesterday's session and not an
older one.

## Troubleshooting

- **A terminal/black window flashes and closes immediately:** Python likely
  isn't installed, or wasn't added to PATH. Reinstall Python and make sure
  that checkbox is ticked.
- **"streamlit: command not found":** the pip install step didn't finish or
  failed silently — run the manual commands above in a terminal so you can
  see the actual error message, and share it if you're stuck.
- **PrevDate shows blank/None or the wrong date:** this means the request to
  Upstox didn't return data as expected — check your access token hasn't
  expired, and that the ticker/instrument key resolved correctly (see the
  "Couldn't resolve an instrument key for..." warning if one appears).
- **LTP column blank:** almost always the Market Data Feed entitlement issue
  mentioned above.

## Later: hosting this publicly (optional)

Everything here also works as a GitHub + Streamlit Community Cloud
deployment if you want a shareable public link later — the same `app.py`,
`upstox_data.py`, `levels.py`, `tickers.csv`, and `requirements.txt` work
as-is. Happy to walk through that again once the local version is confirmed
working, since debugging locally (where you can see real error messages
directly) is a much faster way to shake out any remaining issues first.

## Caveats

- This is a **technical price-level screener, not investment advice**.
- Upstox's public instrument master and APIs occasionally change shape or
  rate-limit; if a ticker shows "No prev-day data," hit **Refresh now** in
  the sidebar.
