"""
Section 1: Macro Data via FRED API.
Fetches all configured series plus the computed Yield Curve (DGS10 - DGS2).
Returns a list of row dicts for the PDF table.
"""
from datetime import datetime, timedelta

from fredapi import Fred

from config import FRED_API_KEY, FRED_SERIES
from helpers import safe_pct_change, format_pct, format_val, get_value_on_or_before, period_dates, PERIODS

# Yield curve is DGS10 - DGS2 (computed, not a FRED series)
YIELD_CURVE_META = ("Yield Curve (10Y Yield − 2Y Yield)", "Percentage Points (%pts)")


def _fetch_series(fred, series_id, start_date):
    """Fetch a FRED series from start_date to today. Returns pandas Series or None."""
    try:
        data = fred.get_series(
            series_id,
            observation_start=start_date.strftime("%Y-%m-%d"),
        )
        return data.dropna() if data is not None else None
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

    # We need 5+ years of history for the 5yr comparison
    fetch_start = datetime.now() - timedelta(days=2000)
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

    print(f"[Section 1] Done. {len(rows)} metrics fetched.")
    return rows
