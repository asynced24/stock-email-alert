"""
Section 4: Companies of Interest.
Scans the S&P 500 (from Wikipedia static HTML) plus Russell 1000 proxies
using yfinance to apply the filter:
  - |5-day change|  > 10%, OR
  - |1-month change| > 20%, OR
  - Volume > average daily volume (vol ratio > 1.0)

Also tries Finviz CSV export as a supplementary source.
Results are sorted by absolute 5-day change (biggest movers first).
"""
import io
import time

import requests
import pandas as pd
import yfinance as yf
from bs4 import BeautifulSoup

from helpers import scraper_headers, safe_pct_change, format_pct

REQUEST_DELAY = 0.15   # seconds between yfinance calls

# ── S&P 500 from Wikipedia ────────────────────────────────────
SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

# ── Additional high-liquidity tickers to always include ───────
EXTRA_TICKERS = [
    # Mega caps not always in S&P 500 at all times
    "BRK-B", "V", "MA", "JPM", "BAC", "WFC", "GS", "MS",
    "AMZN", "GOOGL", "META", "NVDA", "TSLA", "MSFT", "AAPL",
    # Large ETFs (to catch sector moves)
    "SPY", "QQQ", "IWM", "DIA",
    # Popular single-stock movers
    "GME", "AMC", "COIN", "MSTR", "PLTR", "HOOD",
]


def _get_sp500_tickers():
    """Fetch S&P 500 tickers from Wikipedia. Returns list of ticker strings."""
    tickers = []
    try:
        resp = requests.get(SP500_URL, headers=scraper_headers(), timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        table = soup.find("table", {"id": "constituents"})
        if not table:
            # Fallback: find table with 'Symbol' column
            for tbl in soup.find_all("table"):
                headers = [th.get_text(strip=True) for th in tbl.find_all("th")]
                if "Symbol" in headers or "Ticker" in headers:
                    table = tbl
                    break

        if table:
            for tr in table.find_all("tr")[1:]:
                cells = tr.find_all("td")
                if cells:
                    ticker = cells[0].get_text(strip=True).replace(".", "-")
                    if ticker:
                        tickers.append(ticker)

        print(f"  S&P 500: loaded {len(tickers)} tickers from Wikipedia.")
    except Exception as e:
        print(f"  [WARN] Could not fetch S&P 500 from Wikipedia: {e}")

    return tickers


def _enrich(ticker):
    """
    Get 5d/1mo change, volume ratio, options flag, and basic info via yfinance.
    Returns dict or None on failure.
    """
    try:
        t    = yf.Ticker(ticker)
        hist = t.history(period="40d", auto_adjust=True)

        if hist.empty or len(hist) < 5:
            return None

        if hist.index.tz is not None:
            hist.index = hist.index.tz_localize(None)

        closes = hist["Close"]
        vols   = hist["Volume"]

        current_price = float(closes.iloc[-1])

        idx_5d = max(0, len(closes) - 6)
        chg5d  = safe_pct_change(current_price, float(closes.iloc[idx_5d]))
        chg1mo = safe_pct_change(current_price, float(closes.iloc[0]))

        today_vol = float(vols.iloc[-1])
        avg_vol   = float(vols.mean()) if len(vols) > 0 else 1
        vol_ratio = today_vol / avg_vol if avg_vol > 0 else 0

        # Get company name and PE from fast_info
        try:
            info     = t.fast_info
            company  = getattr(info, "company_name", None) or ticker
            pe_raw   = getattr(info, "trailing_pe", None)
            pe       = f"{float(pe_raw):.2f}" if pe_raw else "N/A"
            mc_raw   = getattr(info, "market_cap", None)
            if mc_raw:
                if mc_raw >= 1e12:   mc_str = f"${mc_raw/1e12:.2f}T"
                elif mc_raw >= 1e9:  mc_str = f"${mc_raw/1e9:.2f}B"
                elif mc_raw >= 1e6:  mc_str = f"${mc_raw/1e6:.2f}M"
                else:                mc_str = f"${mc_raw:,.0f}"
            else:
                mc_str = "N/A"
        except Exception:
            company = ticker
            pe      = "N/A"
            mc_str  = "N/A"

        try:
            has_options = "Yes" if t.options else "No"
        except Exception:
            has_options = "No"

        return {
            "company":     company,
            "market_cap":  mc_str,
            "price":       f"${current_price:.2f}",
            "pe":          pe,
            "has_options": has_options,
            "5d_raw":      chg5d  if chg5d  != "NA" else None,
            "1mo_raw":     chg1mo if chg1mo != "NA" else None,
            "5d":          format_pct(chg5d),
            "1mo":         format_pct(chg1mo),
            "vol_ratio":   vol_ratio,
        }
    except Exception:
        return None


def _passes_filter(d):
    try:
        if d.get("5d_raw")  is not None and abs(float(d["5d_raw"]))  > 10:
            return True
        if d.get("1mo_raw") is not None and abs(float(d["1mo_raw"])) > 20:
            return True
        if d.get("vol_ratio") is not None and float(d["vol_ratio"]) > 1.0:
            return True
    except Exception:
        pass
    return False


def fetch_companies_data(industry_rows=None, max_tickers=600):
    """
    Scan the S&P 500 + extra tickers and apply the Companies of Interest filter.

    Args:
        industry_rows: unused (kept for API compatibility)
        max_tickers:   cap on how many tickers to check

    Returns: list of row dicts with keys:
        company, ticker, market_cap, price, pe, has_options, 5d, 1mo
    """
    print("[Section 4] Fetching Companies of Interest (S&P 500 + extras via yfinance)...")

    sp500 = _get_sp500_tickers()
    all_tickers = list(dict.fromkeys(sp500 + EXTRA_TICKERS))[:max_tickers]

    print(f"  Scanning {len(all_tickers)} tickers...")
    qualified = []

    for i, ticker in enumerate(all_tickers):
        if i % 100 == 0 and i > 0:
            print(f"  Progress: {i}/{len(all_tickers)} checked, {len(qualified)} qualified")

        data = _enrich(ticker)
        if data is None:
            continue

        if _passes_filter(data):
            qualified.append({
                "company":     data["company"],
                "ticker":      ticker,
                "market_cap":  data["market_cap"],
                "price":       data["price"],
                "pe":          data["pe"],
                "has_options": data["has_options"],
                "5d":          data["5d"],
                "1mo":         data["1mo"],
            })

        time.sleep(REQUEST_DELAY)

    # Sort by absolute 5-day change
    def sort_key(r):
        try:
            return abs(float(r["5d"].replace("%", "").replace("+", "")))
        except Exception:
            return 0

    qualified.sort(key=sort_key, reverse=True)
    print(f"[Section 4] Done. {len(qualified)} companies of interest found.")
    return qualified
