# Stock Market Report — v1 Design Spec

**Date:** 2026-05-30
**Author:** Aryan (brainstormed with Claude)
**Status:** Approved for planning
**Repo:** `stock_report/`

---

## 1. Goal

Finish v1 of the daily stock-market PDF report. The program already fetches macro,
commodity, industry, company, and earnings data and emails a PDF. v1 reworks the data
layer so it can screen the **entire US market for free**, adds new momentum / moving-average
/ volume screens, fixes formatting bugs, and changes the delivery schedule.

Every change in this spec traces to the ideas in `Stock Market Program.docx`.

---

## 2. Delivery Schedule (changed)

- **Was:** daily at 8:00 PM ET.
- **Now:** twice weekly, same report content both times:
  - **Wednesday 8:00 PM ET** (mid-week reading)
  - **Saturday 8:00 AM ET** (weekend prep; reflects Friday's close)
- Timezone must be handled explicitly (America/New_York), independent of machine local time.
- On-demand run (`python main.py`) and `--no-email` still work.

---

## 3. Feasibility (proven during design, not assumed)

| Capability | Verdict | Evidence (run 2026-05-30) |
|---|---|---|
| Full US universe + name + market cap + industry, free | ✅ | StockAnalysis screener page server-renders `count:5572` stocks with `s, n, marketCap, price, change, industry, volume, peRatio` in one no-auth request |
| History for 50/200-day MA + multi-period % change | ✅ | `yfinance.download([...], period='1y')` batch: 10 tickers in 5.3s, 251 trading days each |
| FRED macro / commodities / PDF / email | ✅ | Existing working code, unchanged model |

**Risk:** the StockAnalysis universe is a scrape, not a contracted API. If their page
changes, the universe pull breaks. It must degrade gracefully (fall back to S&P 500 list),
never send wrong numbers silently.

---

## 4. Architecture — shared bulk data layer (the core change)

Today each section loops yfinance one ticker at a time (fine for ~550 names, impossible for
the full market). v1 introduces three shared modules that every market screen consumes:

### `universe.py`
- Single request to the StockAnalysis screener; parse the server-rendered `data:[...]` array.
- Returns a DataFrame: `symbol, name, market_cap, price, change, industry, volume, pe_ratio`
  for all ~5,500 US stocks.
- Helper `filter_by_market_cap(df, min_cap)` for the `$2B` / `$5B` floors.
- **Fallback:** if the scrape fails/changes shape, fall back to the existing S&P 500
  Wikipedia list (names only) so downstream screens still run.

### `price_history.py`
- `yfinance.download(...)` in **chunks of ~150 tickers**, `period='1y'`, `auto_adjust=True`,
  `threads=True`, `group_by='ticker'`.
- Input universe pre-filtered to market cap ≥ $2B (keeps the batch count ~30 chunks).
- **Daily disk cache** (parquet or pickle, keyed by date) under `cache/` so reruns in the
  same day don't re-download. Cache is `.gitignore`d.
- Returns per-ticker close + volume series for downstream math.

### `screens.py`
Pure functions over `(universe_df, history)`. No network. Each returns a list of row dicts:
- `companies_5d` — abs(5-day) > 10%
- `companies_1mo` — abs(1-month) > 20%
- `volume_spikes` — today's volume above the ticker's normal range, market cap ≥ $2B
- `momentum_pullback` — up > 50% over 1yr **AND** down > 10% over week/month/3-month
- `reversal_bounce` — down > 15% over 1yr **AND** up > 5% over the week
- `near_ma` — within 5% of 50-day **or** 200-day MA, market cap ≥ $2B
- `earnings_filtered` — earnings in next 5 days, market cap ≥ $5B only

Sections 1 (FRED) and 2 (commodities) keep their existing small fixed-list fetches.

---

## 5. Report Structure

| Page/Section | Content |
|---|---|
| Cover | Title, generated timestamp, recipient |
| **Header page (new)** | Mantra: **Filter → Assess → Risk → Position → Entrance → Exit**. Past Mistakes (tickers): **CAR, AGI, UNH, TNZ, AEO, FVI**. Loaded from an editable file so lessons can be annotated later. |
| S1 Macro | + index rows, + 3-month column, font fix |
| S2 Materials | + 3-month column, font fix |
| S3 Industries | StockAnalysis source, drop Market Cap, + 3-month, font fix |
| S4 Companies | Split into 3 tables, names, gradient cells, font fix |
| S5 Earnings | Expand Time, drop EPS/Rev, ≥$5B filter, next 5 days, font fix |
| **S6 Momentum (new)** | Pullback-in-uptrend + bounce-in-downtrend tables |
| **S7 Near MA (new)** | Within 5% of 50/200-day MA, ≥$2B |
| **S8 Abnormal Volume (new)** | Above normal volume range, ≥$2B |

---

## 6. Per-Section Requirements

### Header page (new)
- Mantra line, formatted prominently.
- Past Mistakes list from `mistakes.txt` (or a `MISTAKES` config list), seeded with
  `CAR, AGI, UNH, TNZ, AEO, FVI`. Editable without code changes.

### Section 1 — Macro
- Add a **3-Month %** column (between 1-Month and 6-Month).
- Add these as the **first rows**, above the FRED series:
  **S&P 500 (^GSPC), Dow (^DJI), QQQ, Russell 2000 (^RUT), Shiller PE, Buffett Indicator, DXY (DX-Y.NYB).**
  - Indices/ETFs via yfinance. Shiller PE + Buffett Indicator scraped from multpl.com
    (graceful "NA" if scrape fails).
- Font fix (see §7).
- Note: M2, CPI, jobless claims, consumer credit already come from FRED
  (`M2SL, CPIAUCSL, ICSA, TOTALSL`). No source change needed.

### Section 2 — Materials
- Add **3-Month %** column. Font fix.

### Section 3 — Industries
- **Replace ETF proxies** with industry data derived from the StockAnalysis universe
  (aggregate by `industry`, or scrape StockAnalysis' industries page).
- **Drop** the Market Cap column; **add 3-Month %**. Font fix.

### Section 4 — Companies of Interest
- **Split** the single table into **three** labeled tables:
  1. **>10% 5-day movers**
  2. **>20% 1-month movers**
  3. **Volume spikes**
- Show **company name** (from universe), not just symbol.
- **Gradient cells:** red/green intensity scales with magnitude of % change
  (bigger move = darker cell). Font fix.

### Section 5 — Earnings Calendar
- **Expand** the Time column (currently cramped).
- **Delete** all EPS and Revenue columns.
- **Exclude** companies under **$5B** market cap (join earnings symbols to universe market cap).
- Keep the **next 5 days** of earnings. Font fix.

### Section 6 — Momentum (new)
- Table A: up > 50% / 1yr **AND** down > 10% over week **or** month **or** 3-month.
- Table B: down > 15% / 1yr **AND** up > 5% over the week.

### Section 7 — Near Moving Average (new)
- Stocks within **5%** of their **50-day** or **200-day** MA. Market cap ≥ **$2B**.

### Section 8 — Abnormal Volume (new)
- Stocks trading **above their normal volume range**. Market cap ≥ **$2B**.
  ("Normal range" = e.g. today's volume vs trailing average + threshold; define precisely
  in the plan.)

---

## 7. Font Bug (root-caused)

In `pdf_builder.py::ReportPDF.table`, when a table spans multiple pages the page-break branch
calls `draw_header()` (which sets **bold** font) but **never resets the body font** before
drawing the next rows. Result: page 1 of a table renders in regular weight, continuation
pages render bold — the inconsistency seen on every long table.

**Fix:** reset the body font (`set_font(FONT, "", size)`) immediately after every
`draw_header()` call, including the page-break path. Bump body size slightly for readability.
**Verify by generating the PDF and visually confirming consistent fonts across page breaks.**

---

## 8. Reliability / Fallback Behavior

- Keep `main.py`'s per-section `try/except`: one failed screen → that table is empty, **email
  still sends**. Never block the email on a single failure.
- Universe scrape failure → fall back to S&P 500 list; screens needing the full market show a
  "limited universe today" note rather than wrong data.
- Multpl.com scrape failure → Shiller PE / Buffett Indicator show "NA".

---

## 9. Config Changes

- Schedule: Wednesday 20:00 ET and Saturday 08:00 ET (replace single daily time).
- New: `cache/` dir (gitignored), `mistakes.txt` (or `MISTAKES` list in config).
- Market-cap floors as named constants: `MIN_CAP_SCREENS = 2e9`, `MIN_CAP_EARNINGS = 5e9`.
- New period key `3mo` added to `helpers.PERIODS` / `PERIOD_LABELS`.

---

## 10. Out of Scope for v1

- Intraday / real-time data.
- Options-chain analytics beyond the existing has-options flag.
- Backtesting the screens.
- Per-mistake written lessons (placeholder tickers only for now).

---

## 11. Open Items for the Execution Agent

- Decide exact "normal volume range" definition for S7/S8 (e.g. >1.5× 30-day average).
- Confirm Shiller PE / Buffett Indicator scrape source still parses (multpl.com).
- Confirm StockAnalysis industries aggregation vs. dedicated industries-page scrape.
- Tune chunk size / add polite delay if yfinance rate-limits on the full $2B universe.
