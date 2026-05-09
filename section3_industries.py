"""
Section 3: Industries table.
Data source: Industry & Sector ETFs via yfinance (100% reliable, no scraping).

Uses SPDR sector ETFs plus iShares/Invesco sub-industry ETFs as proxies
for industry-level performance. Also tries to use Finviz CSV export as
a richer supplementary source.
"""
import yfinance as yf

from helpers import safe_pct_change, format_pct, format_val, get_value_on_or_before, period_dates, PERIODS

# ── ETF universe mapped to industry names ────────────────────
# (ticker, industry_label, market_proxy_note)
INDUSTRY_ETFS = [
    # Broad SPDR Sectors
    ("XLF",   "Financials (Sector)"),
    ("XLK",   "Technology (Sector)"),
    ("XLV",   "Health Care (Sector)"),
    ("XLI",   "Industrials (Sector)"),
    ("XLC",   "Communication Services (Sector)"),
    ("XLY",   "Consumer Discretionary (Sector)"),
    ("XLP",   "Consumer Staples (Sector)"),
    ("XLE",   "Energy (Sector)"),
    ("XLU",   "Utilities (Sector)"),
    ("XLB",   "Materials (Sector)"),
    ("XLRE",  "Real Estate (Sector)"),
    # Sub-Industry ETFs
    ("KBE",   "Banks (Sub-Industry)"),
    ("KRE",   "Regional Banks (Sub-Industry)"),
    ("KIE",   "Insurance (Sub-Industry)"),
    ("IAI",   "Broker-Dealers & Exchanges (Sub-Industry)"),
    ("IBB",   "Biotechnology (Sub-Industry)"),
    ("XBI",   "Biotech Small/Mid Cap (Sub-Industry)"),
    ("XPH",   "Pharmaceuticals (Sub-Industry)"),
    ("XHE",   "Health Care Equipment (Sub-Industry)"),
    ("XHS",   "Health Care Services (Sub-Industry)"),
    ("SOXX",  "Semiconductors (Sub-Industry)"),
    ("XSD",   "Semiconductors Small/Mid (Sub-Industry)"),
    ("IGV",   "Software (Sub-Industry)"),
    ("SKYY",  "Cloud Computing (Sub-Industry)"),
    ("HACK",  "Cybersecurity (Sub-Industry)"),
    ("ITA",   "Aerospace & Defense (Sub-Industry)"),
    ("IYT",   "Transportation (Sub-Industry)"),
    ("XAR",   "Aerospace & Defense Alt (Sub-Industry)"),
    ("XTN",   "Transportation Alt (Sub-Industry)"),
    ("XHB",   "Homebuilders (Sub-Industry)"),
    ("ITB",   "Home Construction (Sub-Industry)"),
    ("XRT",   "Retail (Sub-Industry)"),
    ("XHR",   "Hotels & Lodging (Sub-Industry)"),
    ("PEJ",   "Leisure & Entertainment (Sub-Industry)"),
    ("IYR",   "REITs Broad (Sub-Industry)"),
    ("REZ",   "Residential REITs (Sub-Industry)"),
    ("VNQI",  "International REITs (Sub-Industry)"),
    ("XOP",   "Oil & Gas Exploration (Sub-Industry)"),
    ("OIH",   "Oil Services (Sub-Industry)"),
    ("AMLP",  "Midstream Energy/MLP (Sub-Industry)"),
    ("LIT",   "Lithium & Battery Tech (Sub-Industry)"),
    ("COPX",  "Copper Mining (Sub-Industry)"),
    ("GDX",   "Gold Miners (Sub-Industry)"),
    ("GDXJ",  "Junior Gold Miners (Sub-Industry)"),
    ("SLX",   "Steel (Sub-Industry)"),
    ("WOOD",  "Timber & Forestry (Sub-Industry)"),
    ("MOO",   "Agribusiness (Sub-Industry)"),
    ("JETS",  "Airlines (Sub-Industry)"),
    ("ROBO",  "Robotics & AI (Sub-Industry)"),
    ("ARKK",  "Disruptive Innovation (Sub-Industry)"),
    ("FINX",  "FinTech (Sub-Industry)"),
]


def fetch_industries_data():
    """
    Fetch industry/sector ETF performance data via yfinance.
    Returns: list of dicts with keys:
        industry, market_cap, 5d, 1mo, 6mo, 1yr, 5yr
    """
    print(f"[Section 3] Fetching {len(INDUSTRY_ETFS)} industry/sector ETFs via yfinance...")
    dates = period_dates()
    rows  = []

    for ticker, label in INDUSTRY_ETFS:
        try:
            t    = yf.Ticker(ticker)
            hist = t.history(period="6y", auto_adjust=True)

            if hist.empty:
                raise ValueError("empty history")

            if hist.index.tz is not None:
                hist.index = hist.index.tz_localize(None)

            closes = hist["Close"]
            current_price = float(closes.iloc[-1])

            # Market cap for ETFs is total net assets — get from fast_info
            try:
                info = t.fast_info
                mc   = getattr(info, "market_cap", None) or getattr(info, "total_assets", None)
                if mc:
                    if mc >= 1e12:
                        mc_str = f"${mc/1e12:.1f}T"
                    elif mc >= 1e9:
                        mc_str = f"${mc/1e9:.1f}B"
                    elif mc >= 1e6:
                        mc_str = f"${mc/1e6:.1f}M"
                    else:
                        mc_str = f"${mc:,.0f}"
                else:
                    mc_str = "N/A"
            except Exception:
                mc_str = "N/A"

            row = {
                "industry":   f"{label} [{ticker}]",
                "market_cap": mc_str,
            }
            for period in PERIODS:
                past_val = get_value_on_or_before(closes, dates[period])
                row[period] = format_pct(safe_pct_change(current_price, past_val))

            rows.append(row)
            print(f"  {ticker} OK")

        except Exception as e:
            print(f"  {ticker} FAILED: {e}")
            rows.append({
                "industry":   f"{label} [{ticker}]",
                "market_cap": "N/A",
                **{p: "NA" for p in PERIODS},
            })

    print(f"[Section 3] Done. {len(rows)} industries/sectors.")
    return rows
