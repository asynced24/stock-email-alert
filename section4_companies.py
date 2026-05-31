"""
Section 4: Companies of Interest, split into three tables:
  1. >10% 5-day movers
  2. >20% 1-month movers
  3. Volume spikes (>=1.5x trailing-30d avg volume), >=$2B market cap.
All sourced from the >=$2B universe + history panel.
"""
import pandas as pd

from helpers import pct_change_over, format_pct, format_val
from price_history import closes_for, volumes_for

VOL_MULT = 1.5


def _cap_filtered(universe_df, min_cap):
    cap = pd.to_numeric(universe_df["market_cap"], errors="coerce")
    return universe_df[cap >= min_cap]


def _enrich(universe_df, panel, min_cap):
    """Build per-stock dicts with raw + formatted changes and a volume ratio."""
    out = []
    for _, m in _cap_filtered(universe_df, min_cap).iterrows():
        closes = closes_for(panel, m["symbol"])
        if closes is None or len(closes) < 6:
            continue
        vols = volumes_for(panel, m["symbol"])
        chg5  = pct_change_over(closes, 5)
        chg1mo = pct_change_over(closes, 21)
        chg3mo = pct_change_over(closes, 63)
        vol_ratio = None
        if vols is not None and len(vols) >= 20:
            avg = float(vols.iloc[:-1].tail(30).mean())
            if avg > 0:
                vol_ratio = float(vols.iloc[-1]) / avg
        out.append({
            "symbol":   m["symbol"],
            "company":  m["name"],
            "price":    format_val(float(closes.iloc[-1]), 2),
            "5d_raw":   None if chg5 == "NA" else chg5,
            "1mo_raw":  None if chg1mo == "NA" else chg1mo,
            "5d":       format_pct(chg5),
            "1mo":      format_pct(chg1mo),
            "3mo":      format_pct(chg3mo),
            "vol_ratio": vol_ratio,
        })
    return out


def split_movers(enriched, vol_mult=VOL_MULT):
    """
    Split into (five_day, one_month, volume) buckets. Each row goes to the first
    bucket it qualifies for: |5d|>10, then |1mo|>20, then vol_ratio>=vol_mult.
    """
    five, month, vol = [], [], []
    for r in enriched:
        f = r.get("5d_raw"); m = r.get("1mo_raw"); v = r.get("vol_ratio")
        if f is not None and abs(f) > 10:
            five.append(r)
        elif m is not None and abs(m) > 20:
            month.append(r)
        elif v is not None and v >= vol_mult:
            vol.append(r)
    five.sort(key=lambda r: abs(r.get("5d_raw") or 0), reverse=True)
    month.sort(key=lambda r: abs(r.get("1mo_raw") or 0), reverse=True)
    vol.sort(key=lambda r: r.get("vol_ratio") or 0, reverse=True)
    return five, month, vol


def _fmt_vol(r):
    v = r.get("vol_ratio")
    return f"{v:.1f}x" if v is not None else "-"


def fetch_companies_data(universe_df=None, panel=None, min_cap=2e9):
    """
    Returns a dict with three lists: {"five_day", "one_month", "volume"}.
    Empty lists if the universe/panel is unavailable.
    """
    if universe_df is None or panel is None or getattr(panel, "empty", True):
        print("[Section 4] No universe/panel — companies section will be empty.")
        return {"five_day": [], "one_month": [], "volume": []}
    enriched = _enrich(universe_df, panel, min_cap)
    five, month, vol = split_movers(enriched)
    for r in vol:
        r["vol_disp"] = _fmt_vol(r)
    print(f"[Section 4] {len(five)} 5d movers, {len(month)} 1mo movers, {len(vol)} volume spikes.")
    return {"five_day": five, "one_month": month, "volume": vol}
