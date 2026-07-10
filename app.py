import time

import pandas as pd
import streamlit as st

from levels import compute_levels, classify
from upstox_data import (
    load_instrument_master,
    build_symbol_lookup,
    resolve_instrument_key,
    get_prev_day_high_low,
    get_ltp_batch,
)

st.set_page_config(page_title="NSE Onm/Decider Screener", layout="wide")

# ---------------------------------------------------------------------------
# Sidebar: auth + controls
# ---------------------------------------------------------------------------
st.sidebar.title("Settings")

try:
    default_token = st.secrets.get("UPSTOX_ACCESS_TOKEN", "")
except Exception:
    default_token = ""
access_token = st.sidebar.text_input(
    "Upstox access token",
    value=default_token,
    type="password",
    help=(
        "Generate a fresh token each trading day from your Upstox Developer "
        "Apps page (Apps -> your app -> Generate). Tokens expire nightly."
    ),
)

auto_refresh = st.sidebar.checkbox("Auto-refresh live price", value=False)
refresh_secs = st.sidebar.number_input(
    "Refresh interval (seconds)", min_value=5, max_value=300, value=15, step=5,
    disabled=not auto_refresh,
)
manual_refresh = st.sidebar.button("Refresh now", use_container_width=True)

st.sidebar.divider()
st.sidebar.caption(
    "Live LTP requires your Upstox app to have Market Data Feed access. "
    "Previous-day High/Low uses the Historical Candle API and needs no "
    "extra data subscription."
)

if auto_refresh:
    try:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=refresh_secs * 1000, key="autorefresh")
    except ImportError:
        st.sidebar.warning(
            "Install streamlit-autorefresh (see requirements.txt) to enable "
            "auto-refresh. Falling back to manual refresh only."
        )

# ---------------------------------------------------------------------------
# Ticker list (editable in the UI, persisted to tickers.csv on save)
# ---------------------------------------------------------------------------
st.title("NSE Onm / Decider Breakout Screener")
st.caption(
    "Compares live price against yesterday's High/Low-derived onm & decider "
    "levels and flags breakouts/breakdowns. Data source: Upstox API."
)

TICKERS_FILE = "tickers.csv"

@st.cache_data
def load_tickers(path: str) -> pd.DataFrame:
    return pd.read_csv(path)

if "tickers_df" not in st.session_state:
    st.session_state.tickers_df = load_tickers(TICKERS_FILE)

with st.expander("Edit ticker list", expanded=False):
    edited = st.data_editor(
        st.session_state.tickers_df,
        num_rows="dynamic",
        use_container_width=True,
        key="ticker_editor",
    )
    col1, col2 = st.columns(2)
    if col1.button("Apply changes for this session"):
        st.session_state.tickers_df = edited
        st.rerun()
    col2.caption("To make changes permanent, edit tickers.csv in the repo and redeploy.")

tickers_df = st.session_state.tickers_df

if not access_token:
    st.info("Enter your Upstox access token in the sidebar to load data.")
    st.stop()

# ---------------------------------------------------------------------------
# Instrument resolution (cached: the master file only changes once a day)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=6 * 60 * 60, show_spinner="Downloading Upstox instrument master...")
def get_symbol_lookup():
    master = load_instrument_master()
    return build_symbol_lookup(master)

try:
    symbol_lookup = get_symbol_lookup()
except Exception as e:
    st.error(f"Could not download the Upstox instrument master: {e}")
    st.stop()

instrument_keys = {}
missing = []
for ticker in tickers_df["Ticker"]:
    key = resolve_instrument_key(ticker, symbol_lookup)
    if key:
        instrument_keys[ticker] = key
    else:
        missing.append(ticker)

if missing:
    st.warning(
        "Couldn't resolve an instrument key for: " + ", ".join(missing) +
        ". Check the spelling matches the NSE trading symbol exactly."
    )

# ---------------------------------------------------------------------------
# Previous day High/Low (cached for a few hours -- it only changes once a day)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=4 * 60 * 60, show_spinner="Fetching previous day High/Low...")
def fetch_all_prev_day(keys: dict, token: str):
    out = {}
    for ticker, ik in keys.items():
        try:
            result = get_prev_day_high_low(ik, token)
        except Exception as e:
            result = None
        out[ticker] = result
    return out

prev_day = fetch_all_prev_day(instrument_keys, access_token)

# ---------------------------------------------------------------------------
# Live price (NOT cached across reruns -- this is the thing we want fresh)
# ---------------------------------------------------------------------------
if manual_refresh or auto_refresh or "ltp_cache" not in st.session_state:
    try:
        ltp_map = get_ltp_batch(list(instrument_keys.values()), access_token)
        st.session_state["ltp_cache"] = ltp_map
        st.session_state["ltp_error"] = None
    except Exception as e:
        st.session_state["ltp_error"] = str(e)

ltp_map = st.session_state.get("ltp_cache", {})
if st.session_state.get("ltp_error"):
    st.error(f"Live price fetch failed: {st.session_state['ltp_error']}")

# ---------------------------------------------------------------------------
# Build the screener table
# ---------------------------------------------------------------------------
rows = []
for ticker, ik in instrument_keys.items():
    pd_hl = prev_day.get(ticker)
    if not pd_hl:
        rows.append({
            "Ticker": ticker, "LTP": None, "PrevHigh": None, "PrevLow": None,
            "High Onm": None, "High Decider": None, "Low Onm": None, "Low Decider": None,
            "Signal": "No prev-day data",
        })
        continue
    prev_high, prev_low = pd_hl
    tl = compute_levels(ticker, prev_high, prev_low)
    ltp = ltp_map.get(ik)
    signal = classify(ltp, tl)
    rows.append({
        "Ticker": ticker,
        "LTP": ltp,
        "PrevHigh": prev_high,
        "PrevLow": prev_low,
        "High Onm": tl.high_ladder.onm[0],
        "High Decider": tl.high_ladder.decider[0],
        "Low Onm": tl.low_ladder.onm[0],
        "Low Decider": tl.low_ladder.decider[0],
        "Signal": signal,
    })

df = pd.DataFrame(rows)

def highlight_signal(row):
    color = ""
    if row["Signal"] == "BREAKOUT above Decider":
        color = "background-color: #C6EFCE"
    elif row["Signal"] == "BREAKDOWN below Decider":
        color = "background-color: #FFC7CE"
    elif row["Signal"] in ("Above Onm (watch)", "Below Onm (watch)"):
        color = "background-color: #FFEB9C"
    return [color] * len(row)

st.subheader("Screener")
only_alerts = st.checkbox("Show only breakouts/breakdowns", value=False)
display_df = df if not only_alerts else df[df["Signal"].isin(
    ["BREAKOUT above Decider", "BREAKDOWN below Decider"]
)]

st.dataframe(
    display_df.style.apply(highlight_signal, axis=1).format(
        {c: "{:.2f}" for c in ["LTP", "PrevHigh", "PrevLow", "High Onm", "High Decider", "Low Onm", "Low Decider"]},
        na_rep="-",
    ),
    use_container_width=True,
    hide_index=True,
)

st.caption(
    f"Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')} — "
    "this is a technical price-level screener, not investment advice."
)

with st.expander("Full ladder (all 10 rungs) for a ticker"):
    pick = st.selectbox("Ticker", list(instrument_keys.keys()))
    pd_hl = prev_day.get(pick)
    if pd_hl:
        tl = compute_levels(pick, *pd_hl)
        ladder_df = pd.DataFrame({
            "Rung": list(range(1, 11)),
            "High-side Onm": tl.high_ladder.onm,
            "High-side Decider": tl.high_ladder.decider,
            "Low-side Onm": tl.low_ladder.onm,
            "Low-side Decider": tl.low_ladder.decider,
        })
        st.dataframe(ladder_df.style.format("{:.2f}"), hide_index=True, use_container_width=True)
    else:
        st.write("No previous-day data available for this ticker.")
