"""
universe.py — Full US equity snapshot from StockAnalysis (free, no API key).

The screener page server-renders a JS object array. We isolate it, convert
JS->JSON, and return a DataFrame. On any failure, callers should fall back to
the S&P 500 list.
"""
import re
import json

import requests
import pandas as pd

from helpers import scraper_headers

SCREENER_URL = "https://stockanalysis.com/screener/"


def _extract_array_text(html):
    """Return the raw JS text of the inner data:[...] array, or None."""
    m = re.search(r"count:\d+,data:\[", html)
    if not m:
        return None
    start = m.end() - 1          # position of '['
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(html)):
        c = html[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                return html[start:i + 1]
    return None


def _js_array_to_json(arr_text):
    """Convert a JS object array to JSON text."""
    # Quote unquoted object keys:  {s:  ,n:  -> {"s": ,"n":
    txt = re.sub(r'([{,])\s*([A-Za-z_][A-Za-z0-9_]*)\s*:', r'\1"\2":', arr_text)
    # Fix leading-dot numbers:  :.5 -> :0.5  and  :-.5 -> :-0.5
    txt = re.sub(r':(-?)\.(\d)', r':\g<1>0.\2', txt)
    return txt


def parse_universe_html(html):
    """Parse screener HTML into a DataFrame. Raises ValueError if not parseable."""
    arr = _extract_array_text(html)
    if not arr:
        raise ValueError("could not locate data array in screener HTML")
    records = json.loads(_js_array_to_json(arr))
    rename = {
        "s": "symbol", "n": "name", "marketCap": "market_cap",
        "price": "price", "change": "change", "industry": "industry",
        "volume": "volume", "peRatio": "pe_ratio",
    }
    df = pd.DataFrame(records).rename(columns=rename)
    for col in rename.values():
        if col not in df.columns:
            df[col] = None
    return df[list(rename.values())]


def filter_by_market_cap(df, min_cap):
    """Return rows with market_cap >= min_cap (drops missing caps)."""
    cap = pd.to_numeric(df["market_cap"], errors="coerce")
    return df[cap >= min_cap].copy()


def fetch_universe():
    """
    Fetch the live full-market snapshot. Returns a DataFrame, or None on failure
    (caller falls back to the S&P 500 list).
    """
    try:
        resp = requests.get(SCREENER_URL, headers=scraper_headers(), timeout=30)
        resp.raise_for_status()
        df = parse_universe_html(resp.text)
        print(f"[Universe] Loaded {len(df)} US stocks from StockAnalysis.")
        return df
    except Exception as e:
        print(f"  [WARN] Universe fetch failed: {e}")
        return None
