"""
screens.py — Pure screen functions over (universe_df, history panel).

No network. Each returns a list of row dicts ready for the PDF tables.
"""
import pandas as pd

from helpers import pct_change_over, format_pct, format_val
from price_history import closes_for, volumes_for

# trading-session offsets per lookback
SESS = {"5d": 5, "1mo": 21, "3mo": 63, "6mo": 126, "1yr": 252, "3yr": 756, "5yr": 1260}


def _cap_filtered(universe_df, min_cap):
    cap = pd.to_numeric(universe_df["market_cap"], errors="coerce")
    return universe_df[cap >= min_cap]


def _name_for(universe_df, symbol):
    hit = universe_df[universe_df["symbol"] == symbol]
    return hit["name"].iloc[0] if not hit.empty else symbol


def _base_row(universe_df, symbol, closes):
    return {
        "symbol":  symbol,
        "company": _name_for(universe_df, symbol),
        "price":   format_val(float(closes.iloc[-1]), 2),
        "5d":      format_pct(pct_change_over(closes, SESS["5d"])),
        "1mo":     format_pct(pct_change_over(closes, SESS["1mo"])),
        "3mo":     format_pct(pct_change_over(closes, SESS["3mo"])),
        "1yr":     format_pct(pct_change_over(closes, SESS["1yr"])),
    }


def near_ma(universe_df, panel, min_cap, pct=5.0):
    """Stocks whose latest price is within `pct`% of their 50- or 200-day MA."""
    out = []
    for symbol in _cap_filtered(universe_df, min_cap)["symbol"]:
        closes = closes_for(panel, symbol)
        if closes is None or len(closes) < 50:
            continue
        price = float(closes.iloc[-1])
        ma50  = float(closes.tail(50).mean())
        ma200 = float(closes.tail(200).mean()) if len(closes) >= 200 else None
        near50  = abs(price - ma50) / ma50 * 100 <= pct
        near200 = ma200 is not None and abs(price - ma200) / ma200 * 100 <= pct
        if near50 or near200:
            row = _base_row(universe_df, symbol, closes)
            row["ma_tag"] = "50D" if near50 else "200D"
            out.append(row)
    return out


def abnormal_volume(universe_df, panel, min_cap, mult=1.5):
    """Stocks whose latest volume exceeds `mult` x the trailing average."""
    out = []
    for symbol in _cap_filtered(universe_df, min_cap)["symbol"]:
        vols = volumes_for(panel, symbol)
        closes = closes_for(panel, symbol)
        if vols is None or closes is None or len(vols) < 20:
            continue
        today = float(vols.iloc[-1])
        avg   = float(vols.iloc[:-1].tail(30).mean())
        if avg > 0 and today >= mult * avg:
            row = _base_row(universe_df, symbol, closes)
            row["vol_ratio"] = f"{today / avg:.1f}x"
            out.append(row)
    return out


def momentum_pullback(universe_df, panel, min_cap):
    """Up >50% over the year AND down >10% over week, month, or 3-month.

    Requires ~10 months (200 sessions) of history for the yearly trend to be
    meaningful. Measures the yearly change over up to 252 sessions.
    """
    out = []
    for symbol in _cap_filtered(universe_df, min_cap)["symbol"]:
        closes = closes_for(panel, symbol)
        if closes is None or len(closes) < 200:   # need ~10mo of history for a yearly trend
            continue
        yr_sessions = min(SESS["1yr"], len(closes) - 1)
        yr = pct_change_over(closes, yr_sessions)
        if yr == "NA" or yr <= 50:
            continue
        pulls = [pct_change_over(closes, SESS[p]) for p in ("5d", "1mo", "3mo")]
        if any(p != "NA" and p <= -10 for p in pulls):
            out.append(_base_row(universe_df, symbol, closes))
    return out


def reversal_bounce(universe_df, panel, min_cap):
    """Down >20% over the year AND up >10% over the week or month (report Section 8)."""
    out = []
    for symbol in _cap_filtered(universe_df, min_cap)["symbol"]:
        closes = closes_for(panel, symbol)
        if closes is None or len(closes) < 200:
            continue
        yr_sessions = min(SESS["1yr"], len(closes) - 1)
        yr = pct_change_over(closes, yr_sessions)
        if yr == "NA" or yr > -20:
            continue
        ups = [pct_change_over(closes, SESS[p]) for p in ("5d", "1mo")]
        if any(u != "NA" and u >= 10 for u in ups):
            out.append(_base_row(universe_df, symbol, closes))
    return out


def long_term_pullback(universe_df, panel, min_cap, has_options=None):
    """
    Long-term winner pulling back, optionable (report Section 6):
      >0% over ~5yr AND >20% over 1yr AND < -10% over 3mo, optionable.
    `has_options` is an optional callable sym->bool so this module stays network-free;
    main.py supplies a yfinance-backed checker. Requires >=3yr of history so the
    5-year change is meaningful.
    """
    out = []
    for symbol in _cap_filtered(universe_df, min_cap)["symbol"]:
        closes = closes_for(panel, symbol)
        if closes is None or len(closes) < 756:   # ~3yr min
            continue
        lt = pct_change_over(closes, min(SESS["5yr"], len(closes) - 1))
        yr = pct_change_over(closes, SESS["1yr"])
        m3 = pct_change_over(closes, SESS["3mo"])
        if lt == "NA" or lt <= 0:
            continue
        if yr == "NA" or yr <= 20:
            continue
        if m3 == "NA" or m3 >= -10:
            continue
        if has_options is not None and not has_options(symbol):
            continue
        out.append(_base_row(universe_df, symbol, closes))
    return out
