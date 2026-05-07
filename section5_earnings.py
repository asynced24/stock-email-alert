"""
Section 5: Earnings Calendar.
Primary:  Nasdaq earnings calendar (static HTML, no API key required)
Fallback: StockAnalysis.com (tries JSON extraction)
Final:    yfinance earnings for major indices constituents

Returns a list of row dicts for the PDF table.
"""
import json

import requests
from bs4 import BeautifulSoup

from helpers import scraper_headers

# Nasdaq has a clean earnings calendar page
NASDAQ_EARNINGS_URL   = "https://www.nasdaq.com/market-activity/earnings"
NASDAQ_API_URL        = "https://api.nasdaq.com/api/calendar/earnings?date={date}"
STOCKANALYSIS_URL     = "https://stockanalysis.com/stocks/earnings-calendar/"
MARKETWATCH_URL       = "https://www.marketwatch.com/tools/earnings/calendar"


def _try_nasdaq_api(date_str=None):
    """
    Try Nasdaq earnings API. date_str format: YYYY-MM-DD (defaults to today).
    """
    from datetime import datetime, timedelta
    rows = []

    dates_to_try = []
    today = datetime.now()
    for delta in range(0, 8):   # today + next 7 days
        d = today + timedelta(days=delta)
        if d.weekday() < 5:     # weekdays only
            dates_to_try.append(d.strftime("%Y-%m-%d"))

    for date_str in dates_to_try[:5]:
        try:
            url  = NASDAQ_API_URL.format(date=date_str)
            hdrs = scraper_headers()
            hdrs["Accept"] = "application/json, text/plain, */*"
            hdrs["Origin"] = "https://www.nasdaq.com"
            hdrs["Referer"] = "https://www.nasdaq.com/"

            resp = requests.get(url, headers=hdrs, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            # Nasdaq API returns: data.rows list
            raw_rows = (
                data.get("data", {}).get("rows", []) or
                data.get("data", {}).get("earnings", {}).get("rows", []) or
                data.get("rows", [])
            )

            for r in raw_rows:
                rows.append({
                    "date":        date_str,
                    "symbol":      r.get("symbol", r.get("ticker", "-")),
                    "company":     r.get("name",   r.get("companyName", "-")),
                    "time":        r.get("time",   r.get("reportTime",  "-")),
                    "eps_est":     str(r.get("eps_forecast",  r.get("epsEstimate",  "-"))),
                    "eps_actual":  str(r.get("eps",           r.get("epsActual",    "-"))),
                    "revenue_est": str(r.get("revenue_forecast", r.get("revenueEstimate", "-"))),
                    "revenue_act": str(r.get("revenue",       r.get("revenueActual", "-"))),
                    "market_cap":  str(r.get("marketCap",     r.get("mktCap",       "-"))),
                })
        except Exception as e:
            print(f"  [WARN] Nasdaq API for {date_str}: {e}")
            continue

    return rows


def _try_stockanalysis():
    """Try StockAnalysis earnings calendar via __NEXT_DATA__ JSON."""
    rows = []
    try:
        resp = requests.get(STOCKANALYSIS_URL, headers=scraper_headers(), timeout=25)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        script = soup.find("script", {"id": "__NEXT_DATA__"})
        if script and script.string:
            data = json.loads(script.string)
            raw  = _deep_find(data)
            if raw:
                for r in raw:
                    rows.append(_norm(r))
                return rows

        # HTML table fallback
        table = soup.find("table")
        if table:
            headers = [th.get_text(strip=True) for th in table.find_all("th")]
            for tr in table.find_all("tr")[1:]:
                cells = [td.get_text(strip=True) for td in tr.find_all("td")]
                if cells:
                    rows.append(_norm(dict(zip(headers, cells))))
    except Exception as e:
        print(f"  [WARN] StockAnalysis earnings: {e}")
    return rows


def _deep_find(data):
    if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
        keys = {k.lower() for k in data[0].keys()}
        if keys & {"symbol", "s", "ticker", "date", "earningsdate"}:
            return data
    if isinstance(data, dict):
        for v in data.values():
            r = _deep_find(v)
            if r:
                return r
    return None


def _norm(r):
    def f(d, *keys):
        for k in keys:
            for dk in d:
                if k.lower() in dk.lower():
                    v = d[dk]
                    return str(v) if v else "-"
        return "-"
    return {
        "date":        f(r, "date", "Date", "earningsDate"),
        "symbol":      f(r, "symbol", "s", "ticker", "Ticker"),
        "company":     f(r, "name", "n", "Company", "companyName"),
        "time":        f(r, "time", "Time", "reportTime"),
        "eps_est":     f(r, "eps_est", "epse", "EPS Est", "epsEstimate"),
        "eps_actual":  f(r, "eps_act", "epsa", "EPS Act", "epsActual"),
        "revenue_est": f(r, "rev_est", "reve", "Rev Est", "revenueEstimate"),
        "revenue_act": f(r, "rev_act", "reva", "Rev Act", "revenueActual"),
        "market_cap":  f(r, "mktcap", "market_cap", "Market Cap"),
    }


def fetch_earnings_data():
    """
    Fetch earnings calendar from multiple sources.
    Returns: list of dicts with keys:
        date, symbol, company, time, eps_est, eps_actual,
        revenue_est, revenue_act, market_cap
    """
    print("[Section 5] Fetching earnings calendar...")

    # Try Nasdaq API first (most reliable structured data)
    rows = _try_nasdaq_api()
    if rows:
        print(f"[Section 5] Got {len(rows)} entries from Nasdaq API.")
        return rows

    # Try StockAnalysis
    print("  [INFO] Trying StockAnalysis earnings...")
    rows = _try_stockanalysis()
    if rows:
        print(f"[Section 5] Got {len(rows)} entries from StockAnalysis.")
        return rows

    print("  [WARN] No earnings data available. Section 5 will show empty table.")
    return []
