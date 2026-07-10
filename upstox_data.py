"""
Thin wrapper around the Upstox v2 REST API used by the screener.

Docs referenced (July 2026):
- Historical candle (day interval): GET /v2/historical-candle/{instrument_key}/day/{to}/{from}
- LTP quotes:                       GET /v2/market-quote/ltp?instrument_key=a,b,c
- Instrument master (NSE):          https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz

No secrets are hardcoded here. The access token is supplied at call time by the
Streamlit app (typed in by the user each trading day, or read from st.secrets
if you choose to store it there for a private/personal deployment).
"""
from __future__ import annotations

import gzip
import io
import json
from datetime import datetime, timedelta, timezone
from typing import Iterable

IST = timezone(timedelta(hours=5, minutes=30))

import requests

BASE_URL = "https://api.upstox.com/v2"
INSTRUMENT_MASTER_URL = "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"

# Known index instrument keys (these aren't in the equity instrument master the
# same way stocks are, so they're pinned here). Confirm/adjust against
# Upstox's own docs if they ever change these.
KNOWN_INDEX_KEYS = {
    "NIFTY": "NSE_INDEX|Nifty 50",
    "NIFTY 50": "NSE_INDEX|Nifty 50",
    "BANKNIFTY": "NSE_INDEX|Nifty Bank",
    "NIFTY BANK": "NSE_INDEX|Nifty Bank",
}


def _headers(access_token: str) -> dict:
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}",
    }


def load_instrument_master() -> list[dict]:
    """Download & parse Upstox's NSE instrument master (gzipped JSON).

    Cache this yourself (e.g. via st.cache_data with a TTL of a few hours) --
    it's a multi-MB file and only needs refreshing once a day.
    """
    resp = requests.get(INSTRUMENT_MASTER_URL, timeout=30)
    resp.raise_for_status()
    with gzip.GzipFile(fileobj=io.BytesIO(resp.content)) as f:
        data = json.load(f)
    return data


def build_symbol_lookup(instrument_master: list[dict]) -> dict:
    """Map trading_symbol -> instrument_key for NSE_EQ instruments."""
    lookup = {}
    for row in instrument_master:
        if row.get("instrument_type") == "EQ" and row.get("segment") == "NSE_EQ":
            sym = row.get("trading_symbol", "").upper().strip()
            if sym:
                lookup[sym] = row.get("instrument_key")
    return lookup


def resolve_instrument_key(ticker: str, symbol_lookup: dict) -> str | None:
    """Resolve a ticker name (e.g. 'RELIANCE', 'NIFTY') to an Upstox instrument_key."""
    t = ticker.upper().strip()
    if t in KNOWN_INDEX_KEYS:
        return KNOWN_INDEX_KEYS[t]
    return symbol_lookup.get(t)


def get_prev_day_high_low(instrument_key: str, access_token: str) -> tuple[float, float, str] | None:
    """Return (prev_high, prev_low, prev_date) for the most recent COMPLETE
    trading day at or before yesterday (IST calendar date).

    Rather than trying to detect whether today's candle happens to be present
    in the response (fragile -- depends on exactly when Upstox posts it), we
    cap the API request itself at yesterday's date. That makes it structurally
    impossible for today's candle to appear at all, so the last entry in the
    sorted response is always unambiguously "yesterday" -- or, across a
    weekend/holiday, the last trading day before that, which is exactly what
    "previous day" should mean anyway.

    prev_date is returned too so the UI can show exactly which calendar date
    the levels are based on -- useful for verifying this is behaving correctly.
    """
    now_ist = datetime.now(IST)
    to_date = (now_ist - timedelta(days=1)).strftime("%Y-%m-%d")   # yesterday, IST
    from_date = (now_ist - timedelta(days=15)).strftime("%Y-%m-%d")  # comfortably covers long weekends/holidays
    url = f"{BASE_URL}/historical-candle/{instrument_key}/day/{to_date}/{from_date}"
    resp = requests.get(url, headers=_headers(access_token), timeout=15)
    resp.raise_for_status()
    payload = resp.json()
    candles = payload.get("data", {}).get("candles", [])
    if not candles:
        return None
    # Upstox returns candles newest-first: [timestamp, open, high, low, close, volume, oi]
    candles_sorted = sorted(candles, key=lambda c: c[0])  # oldest -> newest
    prev_candle = candles_sorted[-1]
    prev_high, prev_low = prev_candle[2], prev_candle[3]
    prev_date = prev_candle[0][:10]
    return prev_high, prev_low, prev_date


def get_ltp_batch(instrument_keys: Iterable[str], access_token: str) -> dict:
    """Return {instrument_key: last_traded_price} for up to 500 instrument keys."""
    keys = [k for k in instrument_keys if k]
    if not keys:
        return {}
    url = f"{BASE_URL}/market-quote/ltp"
    out = {}
    # Upstox allows ~500 per call; chunk defensively at 200.
    for i in range(0, len(keys), 200):
        chunk = keys[i : i + 200]
        resp = requests.get(
            url,
            headers=_headers(access_token),
            params={"instrument_key": ",".join(chunk)},
            timeout=15,
        )
        resp.raise_for_status()
        payload = resp.json()
        for _, v in payload.get("data", {}).items():
            ik = v.get("instrument_token") or v.get("instrument_key")
            ltp = v.get("last_price")
            if ik is not None:
                out[ik] = ltp
    return out
