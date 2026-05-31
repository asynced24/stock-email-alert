"""
Section 1: Macro Data via FRED API.
Fetches all configured series plus the computed Yield Curve (DGS10 - DGS2).
Also prepends index rows (S&P 500, Dow, QQQ, Russell 2000, DXY) and
valuation rows (Shiller PE, Buffett Indicator) before the FRED series.
Returns a list of row dicts for the PDF table.
"""
from datetime import datetime, timedelta
import re

import requests
from bs4 import BeautifulSoup
from fredapi import Fred
import yfinance as yf

from config import FRED_API_KEY, FRED_SERIES, MACRO_INDEX_TICKERS
from helpers import (safe_pct_change, format_pct, format_val,
                     get_value_on_or_before, period_dates, PERIODS,
                     pct_change_over, scraper_headers)

# Yield curve is DGS10 - DGS2 (computed, not a FRED series)
YIELD_CURVE_META = ("Yield Curve (10Y Yield - 2Y Yield)", "Percentage Points (%pts)")

# Session counts used for index-row pct calculations
_S1_SESS = {"5d": 5, "1mo": 21, "3mo": 63, "6mo": 126, "1yr": 252, "5yr": 1260}


def _index_rows_from_history(index_map, closes_provider):
    """Build Section-1 index rows from a closes_provider(ticker) -> Series | None."""
    rows = []
    for ticker, (label, units) in index_map.items():
        closes = closes_provider(ticker)
        row = {
            "metric":  f"{label} [{units}]",
            "current": "NA" if closes is None else f"{float(closes.iloc[-1]):.2f}",
        }
        for p in ("5d", "1mo", "3mo", "6mo", "1yr", "5yr"):
            row[p] = ("NA" if closes is None
                      else format_pct(pct_change_over(closes, _S1_SESS[p])))
        rows.append(row)
    return rows


def _fetch_index_closes(ticker):
    """Fetch a 6-year close history for an equity/index ticker via yfinance."""
    try:
        h = yf.Ticker(ticker).history(period="6y", auto_adjust=True)
        if h.empty:
            return None
        if h.index.tz is not None:
            h.index = h.index.tz_localize(None)
        return h["Close"].dropna()
    except Exception:
        return None


def _scrape_multpl(url):
    """Return the current value as a float from a multpl.com page, or None."""
    try:
        r = requests.get(url, headers=scraper_headers(), timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        el = soup.find("div", {"id": "current"})
        if not el:
            return None
        m = re.search(r"[-+]?\d[\d,]*\.?\d*", el.get_text())
        return float(m.group().replace(",", "")) if m else None
    except Exception:
        return None


def _valuation_rows():
    """
    Shiller PE (scraped from multpl.com) and a Buffett Indicator placeholder.
    The Buffett value is computed later in main._inject_buffett from the universe
    market cap / GDP; it is approximate (the universe sums all listed names, so
    dual-class shares and foreign ADRs inflate it vs the classic Wilshire/GDP ratio).
    Period-change columns are always NA for these level metrics.
    """
    na = {p: "NA" for p in ("5d", "1mo", "3mo", "6mo", "1yr", "5yr")}
    shiller = _scrape_multpl("https://www.multpl.com/shiller-pe")
    return [
        {"metric": "Shiller PE [Ratio]",
         "current": "NA" if shiller is None else f"{shiller:.2f}", **na},
        {"metric": "Buffett Indicator (approx.) [%]", "current": "NA", **na},
    ]


def _fetch_series(fred, series_id, start_date):
    """
    Fetch a FRED series from start_date to today. Returns pandas Series or None.
    Handles cases where fredapi returns a RangeIndex instead of DatetimeIndex
    by fetching the series info to reconstruct a proper time index.
    """
    import pandas as pd

    def _as_datetime_series(data):
        """Return data only if it has a proper DatetimeIndex, else None."""
        if data is None:
            return None
        data = data.dropna()
        if data.empty:
            return None
        if isinstance(data.index, pd.DatetimeIndex):
            return data
        # fredapi sometimes returns RangeIndex — try to recover via series info
        try:
            info = fred.get_series_info(series_id)
            freq  = info.get("frequency_short", "D")
            start = info.get("observation_start")
            end   = info.get("observation_end")
            if start and end:
                idx = pd.date_range(start=start, end=end, freq=freq)
                if len(idx) == len(data):
                    data.index = idx
                    return data.dropna()
        except Exception:
            pass
        return None

    try:
        data = fred.get_series(
            series_id,
            observation_start=start_date.strftime("%Y-%m-%d"),
        )
        result = _as_datetime_series(data)
        if result is not None:
            return result
        # If the bounded fetch returned a bad index, retry without start date
        data = fred.get_series(series_id)
        return _as_datetime_series(data)
    except Exception as e:
        print(f"  [WARN] Could not fetch FRED series {series_id}: {e}")
        return None


def fetch_macro_data():
    """
    Fetch all FRED macro data.
    Returns: list of dicts with keys:
        metric, current, 5d, 1mo, 6mo, 1yr, 5yr
    """
    print("[Section 1] Fetching FRED macro data...")
    fred = Fred(api_key=FRED_API_KEY)

    # 2555 days ≈ 7 years; gives headroom for the 5yr comparison and for
    # licensed series (e.g. ICE BofA spreads) that FRED only distributes
    # for a rolling ~3-year window via the API.
    fetch_start = datetime.now() - timedelta(days=2555)
    dates = period_dates()

    # Fetch all series histories once (much more efficient than per-period calls)
    histories = {}
    for series_id in FRED_SERIES:
        print(f"  Fetching {series_id}...", end=" ", flush=True)
        histories[series_id] = _fetch_series(fred, series_id, fetch_start)
        print("OK" if histories[series_id] is not None else "FAILED")

    rows = []

    # Build rows for each configured series
    for series_id, (label, units) in FRED_SERIES.items():
        hist = histories.get(series_id)
        current_val = get_value_on_or_before(hist, dates["current"]) if hist is not None else None

        row = {
            "metric":  f"{label} [{units}]",
            "current": format_val(current_val, 4) if current_val is not None else "NA",
        }
        for period in PERIODS:
            past_val = get_value_on_or_before(hist, dates[period]) if hist is not None else None
            row[period] = format_pct(safe_pct_change(current_val, past_val))

        rows.append(row)

    # Computed row: Yield Curve = DGS10 - DGS2
    label, units = YIELD_CURVE_META
    dgs10_hist = histories.get("DGS10")
    dgs2_hist  = histories.get("DGS2")

    def yc_value(date):
        d10 = get_value_on_or_before(dgs10_hist, date) if dgs10_hist is not None else None
        d2  = get_value_on_or_before(dgs2_hist,  date) if dgs2_hist  is not None else None
        if d10 is None or d2 is None:
            return None
        return d10 - d2

    yc_current = yc_value(dates["current"])
    yc_row = {
        "metric":  f"{label} [{units}]",
        "current": f"{yc_current:.4f}" if yc_current is not None else "NA",
    }
    for period in PERIODS:
        yc_past = yc_value(dates[period])
        yc_row[period] = format_pct(safe_pct_change(yc_current, yc_past))

    rows.append(yc_row)

    # Prepend index + valuation rows ABOVE the FRED series
    print("[Section 1] Fetching index rows (yfinance)...")
    index_rows = _index_rows_from_history(MACRO_INDEX_TICKERS, _fetch_index_closes)
    print("[Section 1] Fetching valuation rows (multpl.com)...")
    valuation_rows = _valuation_rows()
    rows = index_rows + valuation_rows + rows

    print(f"[Section 1] Done. {len(rows)} metrics fetched.")
    return rows
