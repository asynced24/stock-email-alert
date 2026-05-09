# ============================================================
# CONFIGURATION — Credentials are loaded from a .env file.
# Copy .env.example to .env and fill in your values.
# ============================================================
import os
from dotenv import load_dotenv

load_dotenv()

# ── FRED API Key ──────────────────────────────────────────────
FRED_API_KEY = os.getenv("FRED_API_KEY", "")

# ── StockAnalysis API Key ─────────────────────────────────────
# Get one at: https://stockanalysis.com/api/
# Leave unset to use free web-scraping fallback instead.
STOCKANALYSIS_API_KEY = os.getenv("STOCKANALYSIS_API_KEY") or None

# ── Email Configuration ───────────────────────────────────────
EMAIL_RECIPIENT    = os.getenv("EMAIL_RECIPIENT", "")
EMAIL_SENDER       = os.getenv("EMAIL_SENDER", "")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD", "")

# ── Report Output ─────────────────────────────────────────────
REPORT_OUTPUT_PATH = "stock_report.pdf"

# ── Scheduling ────────────────────────────────────────────────
REPORT_TIMEZONE = "America/New_York"
REPORT_HOUR     = 20   # 8 PM Eastern

# ── FRED Series: {series_id: (human_label, units)} ───────────
FRED_SERIES = {
    "WALCL":        ("Fed Total Assets",                     "USD Billions"),
    "RRPONTSYD":    ("Reverse Repo (Liquidity Drain)",       "USD Billions"),
    "WTREGEN":      ("Treasury General Account (TGA)",       "USD Billions"),
    "RESBALNS":     ("Reserve Balances at Fed",              "USD Billions"),
    "BOGMBASE":     ("Monetary Base",                        "USD Billions"),
    "FEDFUNDS":     ("Effective Fed Funds Rate",             "Percent (%)"),
    "DTWEXBGS":     ("US Dollar Index (Broad)",              "Index"),
    "DGS1":         ("1-Year Treasury Yield",                "Percent (%)"),
    "DGS2":         ("2-Year Treasury Yield",                "Percent (%)"),
    "DGS5":         ("5-Year Treasury Yield",                "Percent (%)"),
    "DGS10":        ("10-Year Treasury Yield",               "Percent (%)"),
    "DGS30":        ("30-Year Treasury Yield",               "Percent (%)"),
    # Yield Curve (DGS10 - DGS2) is computed separately below
    "BAMLH0A0HYM2": ("High Yield Spread",                   "Percent (%)"),
    "BAMLC0A0CM":   ("Investment Grade Spread",              "Percent (%)"),
    "TOTLL":        ("Total Bank Loans & Leases",            "USD Billions"),
    "BUSLOANS":     ("Commercial & Industrial Loans",        "USD Billions"),
    "DRTSCILM":     ("Tightening Lending Standards (Bus.)",  "Net Percent (%)"),
    "TOTALSL":      ("Total Consumer Credit",                "USD Billions"),
    "M2SL":         ("M2 Money Supply",                      "USD Billions"),
    "M2V":          ("Velocity of M2",                       "Ratio"),
    "GDP":          ("Nominal GDP",                          "USD Billions, Ann. Rate"),
    "GDPC1":        ("Real GDP (Inflation-Adjusted)",        "Chained 2017 USD Billions"),
    "INDPRO":       ("Industrial Production Index",          "Index 2017=100"),
    "TCU":          ("Capacity Utilization",                 "Percent of Capacity (%)"),
    "PCE":          ("Personal Consumption Expenditures",    "USD Billions"),
    "RSAFS":        ("Advance Retail Sales",                 "USD Millions"),
    "PI":           ("Personal Income",                      "USD Billions, Ann. Rate"),
    "UNRATE":       ("Unemployment Rate",                    "Percent (%)"),
    "PAYEMS":       ("Nonfarm Payrolls",                     "Thousands of Persons"),
    "ICSA":         ("Initial Jobless Claims (Weekly)",      "Thousands"),
    "AHETPI":       ("Average Hourly Earnings",              "USD per Hour"),
    "CPIAUCSL":     ("Headline CPI",                         "Index 1982-84=100"),
    "CPILFESL":     ("Core CPI (ex Food & Energy)",          "Index 1982-84=100"),
    "PCEPILFE":     ("Core PCE Price Index",                 "Index 2017=100"),
    "T5YIE":        ("5-Year Breakeven Inflation",           "Percent (%)"),
    "T10YIE":       ("10-Year Breakeven Inflation",          "Percent (%)"),
    "HOUST":        ("Housing Starts",                       "Thousands of Units, Ann."),
    "PERMIT":       ("Building Permits",                     "Thousands of Units, Ann."),
    "CSUSHPINSA":   ("Case-Shiller Home Price Index",        "Index Jan-2000=100"),
    "MORTGAGE30US": ("30-Year Fixed Mortgage Rate",          "Percent (%)"),
    "STLFSI4":      ("St. Louis Financial Stress Index",     "Index"),
}

# ── Yahoo Finance Commodity Tickers: {ticker: (label, units)} ─
COMMODITY_TICKERS = {
    "^VIX":     ("CBOE Volatility Index",            "Index (Points)"),
    "CL=F":     ("Oil - WTI Crude",                   "USD per Barrel"),
    "BZ=F":     ("Oil - Brent Crude",                "USD per Barrel"),
    "NG=F":     ("Natural Gas",                      "USD per MMBtu"),
    "RB=F":     ("Gasoline (RBOB)",                  "USD per Gallon"),
    "HO=F":     ("Heating Oil",                      "USD per Gallon"),
    "BTU":      ("Peabody Energy (Coal Proxy)",       "USD per Share"),
    "HG=F":     ("Copper",                           "USD per Pound"),
    "ALI=F":    ("Aluminum",                         "USD per Pound"),
    "FCX":      ("Freeport-McMoRan (Base Metals)",   "USD per Share"),
    "CLF":      ("Cleveland-Cliffs (Steel)",          "USD per Share"),
    "NUE":      ("Nucor (Steel)",                    "USD per Share"),
    "VALE":     ("Vale S.A. (Iron Ore Proxy)",        "USD per Share"),
    "ALB":      ("Albemarle (Lithium)",              "USD per Share"),
    "SQM":      ("SQM (Lithium)",                    "USD per Share"),
    "LBS=F":    ("Lumber",                           "USD per 1000 Bd Ft"),
    "VMC":      ("Vulcan Materials (Aggregates)",    "USD per Share"),
    "MLM":      ("Martin Marietta (Aggregates)",     "USD per Share"),
    "ZW=F":     ("Wheat",                            "USD per Bushel"),
    "ZC=F":     ("Corn",                             "USD per Bushel"),
    "ZS=F":     ("Soybeans",                         "USD per Bushel"),
    "ZL=F":     ("Soybean Oil",                      "USD per Pound"),
    "ZM=F":     ("Soybean Meal",                     "USD per Short Ton"),
    "ZR=F":     ("Rough Rice",                       "USD per 100 lbs"),
    "NTR":      ("Nutrien (Fertilizer)",             "USD per Share"),
    "MOS":      ("Mosaic (Fertilizer)",              "USD per Share"),
    "CF":       ("CF Industries (Fertilizer)",       "USD per Share"),
    "GC=F":     ("Gold",                             "USD per Troy Oz"),
    "SI=F":     ("Silver",                           "USD per Troy Oz"),
    "PL=F":     ("Platinum",                         "USD per Troy Oz"),
    "PA=F":     ("Palladium",                        "USD per Troy Oz"),
    "MP":       ("MP Materials (Rare Earth)",        "USD per Share"),
    "DOW":      ("Dow Inc. (Chemicals)",             "USD per Share"),
    "LYB":      ("LyondellBasell (Chemicals)",       "USD per Share"),
    "BDRY":     ("Breakwave Dry Bulk ETF (Shipping)",  "USD per Share"),
    "ZIM":      ("ZIM Integrated Shipping",          "USD per Share"),
}
