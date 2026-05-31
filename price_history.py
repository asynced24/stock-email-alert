"""
price_history.py — Batch daily OHLCV history via yfinance, cached per day.

One pickle per calendar date under cache/. Downloads in chunks to avoid
per-ticker loops and rate limits.
"""
import os
from datetime import datetime

import pandas as pd
import yfinance as yf

CACHE_DIR  = "cache"
CHUNK_SIZE = 150


def _cache_path(date_str):
    return os.path.join(CACHE_DIR, f"history_{date_str}.pkl")


def closes_for(panel, ticker):
    """Return the Close Series for a ticker from a group_by='ticker' panel, or None."""
    try:
        s = panel[ticker]["Close"].dropna()
        return s if not s.empty else None
    except Exception:
        return None


def volumes_for(panel, ticker):
    """Return the Volume Series for a ticker, or None."""
    try:
        s = panel[ticker]["Volume"].dropna()
        return s if not s.empty else None
    except Exception:
        return None


def _download_chunk(tickers):
    df = yf.download(
        tickers, period="1y", interval="1d", group_by="ticker",
        auto_adjust=True, threads=True, progress=False,
    )
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    return df


def fetch_history(tickers, use_cache=True):
    """
    Download (or load cached) 1y daily history for the given tickers.
    Returns a wide DataFrame with MultiIndex columns (ticker, field).
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    path = _cache_path(date_str)

    if use_cache and os.path.exists(path):
        print(f"[History] Using cached history for {date_str}.")
        return pd.read_pickle(path)

    tickers = list(dict.fromkeys(tickers))
    chunks = [tickers[i:i + CHUNK_SIZE] for i in range(0, len(tickers), CHUNK_SIZE)]
    print(f"[History] Downloading {len(tickers)} tickers in {len(chunks)} chunks...")

    frames = []
    for i, chunk in enumerate(chunks, 1):
        try:
            frames.append(_download_chunk(chunk))
            print(f"  chunk {i}/{len(chunks)} OK ({len(chunk)} tickers)")
        except Exception as e:
            print(f"  chunk {i}/{len(chunks)} FAILED: {e}")

    if not frames:
        return pd.DataFrame()

    panel = pd.concat(frames, axis=1)
    panel.to_pickle(path)
    print(f"[History] Cached to {path}.")
    return panel
