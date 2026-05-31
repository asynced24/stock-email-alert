"""
Section 4: Companies of Interest, three independent tables:
  1. >10% 5-day movers
  2. >20% 1-month movers  (with 6-month and 1-year context columns)
  3. Volume spikes: peak volume over the last 3 days >= 2x the 2-week average
     volume, market cap >= $2B.
All sourced from the >=$2B universe + history panel. A stock may appear in more
than one table (the three criteria are evaluated independently).
"""
import pandas as pd

from helpers import pct_change_over, format_pct, format_val
from price_history import closes_for, volumes_for

VOL_MULT = 2.0   # peak-3-day volume must be >= 2x the 2-week average


def _cap_filtered(universe_df, min_cap):
    cap = pd.to_numeric(universe_df["market_cap"], errors="coerce")
    return universe_df[cap >= min_cap]


def _fmt_volume(v):
    """Compact volume formatting: 18,700,000 -> '18.7M'."""
    if v is None:
        return "-"
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "-"
    if v >= 1e9:
        return f"{v/1e9:.1f}B"
    if v >= 1e6:
        return f"{v/1e6:.1f}M"
    if v >= 1e3:
        return f"{v/1e3:.0f}K"
    return f"{v:.0f}"


def _volume_metrics(vols):
    """
    From a volume Series (DatetimeIndex), return:
      avg2wk    - mean daily volume over the 2 weeks (10 trading days) BEFORE the
                  last 3 days (the regular-volume baseline, excluding the spike window)
      spike     - peak volume over the last 3 days / avg2wk
      peak_vol  - highest single-day volume over the last 3 days
      peak_date - the date that peak volume was recorded (YYYY-MM-DD)
    Returns (None, None, None, None) if there isn't enough data.
    """
    if vols is None or len(vols) < 13:
        return None, None, None, None
    # 10 sessions ending just before the last 3 — so the spike doesn't inflate its own baseline
    avg2wk = float(vols.iloc[-13:-3].mean())
    last3 = vols.tail(3)
    peak_vol = float(last3.max())
    try:
        peak_date = last3.idxmax().strftime("%Y-%m-%d")
    except Exception:
        peak_date = "-"
    spike = (peak_vol / avg2wk) if avg2wk and avg2wk > 0 else None
    return avg2wk, spike, peak_vol, peak_date


def _enrich(universe_df, panel, min_cap):
    """Build per-stock dicts with formatted changes and volume metrics."""
    out = []
    for _, m in _cap_filtered(universe_df, min_cap).iterrows():
        closes = closes_for(panel, m["symbol"])
        if closes is None or len(closes) < 6:
            continue
        vols = volumes_for(panel, m["symbol"])
        chg5   = pct_change_over(closes, 5)
        chg1mo = pct_change_over(closes, 21)
        chg3mo = pct_change_over(closes, 63)
        chg6mo = pct_change_over(closes, 126)
        chg1yr = pct_change_over(closes, 252)
        avg2wk, spike, peak_vol, peak_date = _volume_metrics(vols)
        out.append({
            "symbol":   m["symbol"],
            "company":  m["name"],
            "price":    format_val(float(closes.iloc[-1]), 2),
            "5d_raw":   None if chg5   == "NA" else chg5,
            "1mo_raw":  None if chg1mo == "NA" else chg1mo,
            "5d":       format_pct(chg5),
            "1mo":      format_pct(chg1mo),
            "3mo":      format_pct(chg3mo),
            "6mo":      format_pct(chg6mo),
            "1yr":      format_pct(chg1yr),
            # volume metrics (raw + display)
            "spike":        spike,
            "avg2wk_disp":  _fmt_volume(avg2wk),
            "spike_disp":   f"{spike:.1f}x" if spike is not None else "-",
            "peakvol_disp": _fmt_volume(peak_vol),
            "peak_date":    peak_date or "-",
        })
    return out


def split_movers(enriched, vol_mult=VOL_MULT):
    """
    Three INDEPENDENT buckets (a stock can appear in more than one):
      five_day : |5-day change|  > 10%
      one_month: |1-month change| > 20%
      volume   : 3-day peak volume >= vol_mult x the 2-week average
    """
    five  = [r for r in enriched if r.get("5d_raw")  is not None and abs(r["5d_raw"])  > 10]
    month = [r for r in enriched if r.get("1mo_raw") is not None and abs(r["1mo_raw"]) > 20]
    vol   = [r for r in enriched if r.get("spike")   is not None and r["spike"] >= vol_mult]
    five.sort(key=lambda r: abs(r.get("5d_raw") or 0), reverse=True)
    month.sort(key=lambda r: abs(r.get("1mo_raw") or 0), reverse=True)
    vol.sort(key=lambda r: r.get("spike") or 0, reverse=True)
    return five, month, vol


def fetch_companies_data(universe_df=None, panel=None, min_cap=2e9):
    """
    Returns a dict with three lists: {"five_day", "one_month", "volume"}.
    Empty lists if the universe/panel is unavailable.
    """
    if universe_df is None or panel is None or getattr(panel, "empty", True):
        print("[Section 4] No universe/panel - companies section will be empty.")
        return {"five_day": [], "one_month": [], "volume": []}
    enriched = _enrich(universe_df, panel, min_cap)
    five, month, vol = split_movers(enriched)
    print(f"[Section 4] {len(five)} 5d movers, {len(month)} 1mo movers, {len(vol)} volume spikes.")
    return {"five_day": five, "one_month": month, "volume": vol}
