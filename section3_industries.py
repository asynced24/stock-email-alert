"""
Section 3: Industries.
Industry list comes from the universe snapshot (StockAnalysis-derived); period
changes and P/E are aggregated from the member stocks' yfinance history.
"""
import pandas as pd

from helpers import pct_change_over, format_pct
from price_history import closes_for

_S3_SESS = {"5d": 5, "1mo": 21, "3mo": 63, "6mo": 126, "1yr": 252, "3yr": 756, "5yr": 1260}


def aggregate_industries(universe_df, panel):
    """
    Group the universe by industry. For each industry return a row dict with:
      industry, pe (median member P/E), and cap-weighted average period changes
      (5d/1mo/3mo/6mo/1yr/3yr/5yr) from member stocks' history.
    """
    rows = []
    for industry, grp in universe_df.groupby("industry"):
        if not industry:
            continue
        # median P/E of positive member ratios
        pes = pd.to_numeric(grp["pe_ratio"], errors="coerce")
        pes = pes[pes > 0]
        row = {"industry": industry,
               "pe": f"{pes.median():.1f}" if not pes.empty else "NA"}
        # gather members that have history (weight = market cap)
        members = []
        for _, m in grp.iterrows():
            c = closes_for(panel, m["symbol"]) if panel is not None else None
            if c is not None:
                w = pd.to_numeric(pd.Series([m["market_cap"]]), errors="coerce").iloc[0]
                if pd.notna(w) and w > 0:
                    members.append((float(w), c))
        for p, n in _S3_SESS.items():
            num = den = 0.0
            for w, c in members:
                v = pct_change_over(c, n)
                if v != "NA":
                    num += w * v
                    den += w
            row[p] = format_pct(round(num / den, 2)) if den > 0 else "NA"
        rows.append(row)
    rows.sort(key=lambda r: r["industry"])
    return rows


def fetch_industries_data(universe_df=None, panel=None):
    """
    Build Section-3 industry rows. Returns [] if the universe is unavailable
    (caller should alert). Otherwise aggregates from members.
    """
    if universe_df is None or universe_df.empty:
        print("[Section 3] No universe available — industries section will be empty.")
        return []
    rows = aggregate_industries(universe_df, panel)
    print(f"[Section 3] Aggregated {len(rows)} industries from universe members.")
    return rows
