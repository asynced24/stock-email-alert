"""
Section 2: Base Materials & Commodities via Yahoo Finance (yfinance).
Returns a list of row dicts for the PDF table.
"""
import yfinance as yf

from config import COMMODITY_TICKERS
from helpers import safe_pct_change, format_pct, format_val, get_value_on_or_before, period_dates, PERIODS


def fetch_materials_data():
    """
    Fetch all commodity/materials price data from Yahoo Finance.
    Returns: list of dicts with keys:
        commodity, current, 5d, 1mo, 6mo, 1yr, 5yr
    """
    print("[Section 2] Fetching commodity/materials data from Yahoo Finance...")
    dates = period_dates()
    rows = []

    for ticker, (label, units) in COMMODITY_TICKERS.items():
        print(f"  Fetching {ticker} ({label})...", end=" ", flush=True)
        try:
            t    = yf.Ticker(ticker)
            hist = t.history(period="6y", auto_adjust=True)

            if hist.empty:
                raise ValueError("empty history")

            # Normalize timezone so comparisons work
            if hist.index.tz is not None:
                hist.index = hist.index.tz_localize(None)

            # Build a Series of close prices indexed by date
            closes = hist["Close"]

            current_val = float(closes.iloc[-1])

            row = {
                "commodity": f"{label} [{units}]",
                "current":   format_val(current_val, 4),
            }
            for period in PERIODS:
                past_val = get_value_on_or_before(closes, dates[period])
                row[period] = format_pct(safe_pct_change(current_val, past_val))

            rows.append(row)
            print("OK")

        except Exception as e:
            print(f"FAILED ({e})")
            rows.append({
                "commodity": f"{label} [{units}]",
                "current":   "NA",
                **{p: "NA" for p in PERIODS},
            })

    print(f"[Section 2] Done. {len(rows)} commodities processed.")
    return rows
