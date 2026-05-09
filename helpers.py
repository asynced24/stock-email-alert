"""
Shared utility functions used across all sections.
"""
from datetime import datetime, timedelta
import pytz


def safe_pct_change(current, past):
    """
    Calculate percentage change between current and past values.
    Returns a float or 'NA' string on any error/missing data.
    """
    try:
        if current is None or past is None:
            return "NA"
        current = float(current)
        past    = float(past)
        if past == 0:
            return "NA"
        return round(((current - past) / abs(past)) * 100, 2)
    except Exception:
        return "NA"


def format_pct(val):
    """Format a percentage value with sign for display in tables."""
    if val == "NA" or val is None:
        return "NA"
    try:
        return f"{float(val):+.2f}%"
    except Exception:
        return "NA"


def format_val(val, decimals=4):
    """Format a numeric value for display, or return 'NA'."""
    if val is None:
        return "NA"
    try:
        return f"{float(val):.{decimals}f}"
    except Exception:
        return "NA"


def get_value_on_or_before(series, target_date):
    """
    Given a pandas Series with DatetimeIndex, return the most recent
    value on or before target_date. Returns None if not found.
    Handles edge cases: non-DatetimeIndex (e.g. RangeIndex from fredapi),
    tz-aware vs naive timestamps, and empty/None series.
    """
    try:
        import pandas as pd
        if series is None or series.empty:
            return None

        # Some fredapi responses come back with RangeIndex instead of
        # DatetimeIndex when the series has no parseable date metadata.
        # In that case we can't do a time-based lookup.
        if not isinstance(series.index, pd.DatetimeIndex):
            return None

        target = pd.Timestamp(target_date).tz_localize(None)
        # Strip timezone from index so naive comparison works
        idx = series.index.tz_localize(None) if series.index.tz else series.index
        mask = idx <= target
        filtered = series[mask].dropna()
        if filtered.empty:
            return None
        return float(filtered.iloc[-1])
    except Exception:
        return None


def get_et_now():
    """Return the current datetime in US/Eastern timezone."""
    et = pytz.timezone("America/New_York")
    return datetime.now(et)


def period_dates():
    """Return a dict of {period_key: datetime} for the standard comparison periods."""
    now = datetime.now()
    return {
        "current": now,
        "5d":      now - timedelta(days=7),    # 7 calendar days to clear weekends
        "1mo":     now - timedelta(days=33),
        "6mo":     now - timedelta(days=185),
        "1yr":     now - timedelta(days=370),
        "5yr":     now - timedelta(days=1830),
    }


PERIOD_LABELS = {
    "5d":  "5 Day Change",
    "1mo": "1 Month Change",
    "6mo": "6 Month Change",
    "1yr": "1 Year Change",
    "5yr": "5 Year Change",
}

PERIODS = ["5d", "1mo", "6mo", "1yr", "5yr"]


def scraper_headers():
    """Return browser-like headers for web scraping."""
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",   # no 'br' — requests can't decode Brotli
        "Connection":      "keep-alive",
        "Cache-Control":   "no-cache",
    }
