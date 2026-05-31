# Stock Report v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish v1 of the daily stock-market PDF report: screen the entire US market for free, add momentum / moving-average / abnormal-volume screens, fix formatting, and deliver Wed 8PM ET + Sat 8AM ET.

**Architecture:** Introduce a shared bulk data layer (`universe.py` → free StockAnalysis full-market snapshot; `price_history.py` → cached yfinance batch history; `screens.py` → pure screen functions). Sections become thin consumers. PDF builder gains a header page, a 3-month column, gradient cells, split tables, and a font-reset fix.

**Tech Stack:** Python, requests + BeautifulSoup (scrape), yfinance (history), pandas, fpdf2 (PDF), schedule + pytz (delivery), pytest (tests).

**Spec:** `docs/superpowers/specs/2026-05-30-stock-report-v1-design.md`

---

## File Structure

**Create:**
- `universe.py` — full US market snapshot from StockAnalysis + market-cap filters
- `price_history.py` — batch yfinance history with daily disk cache
- `screens.py` — pure screen functions (momentum, near-MA, volume, company movers)
- `mistakes.txt` — editable past-mistakes list (seeded with tickers)
- `tests/__init__.py`, `tests/conftest.py`, and one `tests/test_*.py` per module

**Modify:**
- `helpers.py` — add `3mo` period + `pct_change_over` helper
- `config.py` — schedule times, market-cap floors, indices, cache dir
- `pdf_builder.py` — font reset, 3mo column, header page, S1 index rows, S3/S4/S5 changes, gradient, new S6/S7/S8 tables
- `section1_macro.py` — prepend index rows, add 3mo
- `section2_materials.py` — add 3mo
- `section3_industries.py` — StockAnalysis industries source
- `section4_companies.py` — consume universe, split into 3 result sets
- `section5_earnings.py` — ≥$5B filter, drop EPS/Rev
- `main.py` — Wed/Sat ET schedule, wire new sections
- `requirements.txt` — add `pytest`
- `.gitignore` — add `cache/`

---

## Phase 0 — Test Infrastructure & Shared Helpers

### Task 0.1: Test harness + gitignore + deps

**Files:**
- Create: `tests/__init__.py` (empty), `tests/conftest.py`
- Modify: `requirements.txt`, `.gitignore`

- [ ] **Step 1: Add pytest to requirements**

Append to `requirements.txt`:
```
pytest
```

- [ ] **Step 2: Ignore cache + pytest artifacts**

Append to `.gitignore`:
```
cache/
.pytest_cache/
__pycache__/
```

- [ ] **Step 3: Create empty test package marker**

Create `tests/__init__.py` (empty file).

- [ ] **Step 4: Create conftest with sample fixtures**

Create `tests/conftest.py`:
```python
import pandas as pd
import pytest


@pytest.fixture
def sample_universe():
    """A tiny universe DataFrame mirroring universe.fetch_universe() output."""
    return pd.DataFrame([
        {"symbol": "AAA", "name": "Alpha Inc.",  "market_cap": 6e9, "price": 100.0,
         "change": 1.0, "industry": "Software",     "volume": 2_000_000, "pe_ratio": 20.0},
        {"symbol": "BBB", "name": "Beta Corp.",  "market_cap": 3e9, "price": 50.0,
         "change": -2.0, "industry": "Software",    "volume": 5_000_000, "pe_ratio": 15.0},
        {"symbol": "CCC", "name": "Gamma Ltd.",  "market_cap": 1e9, "price": 10.0,
         "change": 0.5, "industry": "Biotechnology","volume": 800_000,   "pe_ratio": 9.0},
    ])


@pytest.fixture
def sample_closes():
    """200+ trading days of synthetic closes for one ticker."""
    idx = pd.date_range("2025-01-01", periods=260, freq="B")
    # rising series from 50 -> 180
    vals = [50 + i * 0.5 for i in range(260)]
    return pd.Series(vals, index=idx)
```

- [ ] **Step 5: Verify pytest runs**

Run: `python -m pytest -q`
Expected: `no tests ran` (or collects 0) with exit 0 — harness works.

- [ ] **Step 6: Commit**

```bash
git add tests/__init__.py tests/conftest.py requirements.txt .gitignore
git commit -m "chore: add pytest harness, cache gitignore, sample fixtures"
```

---

### Task 0.2: Add `3mo` period and `pct_change_over` to helpers

**Files:**
- Modify: `helpers.py`
- Test: `tests/test_helpers.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_helpers.py`:
```python
import pandas as pd
from helpers import PERIODS, PERIOD_LABELS, period_dates, pct_change_over


def test_3mo_period_registered():
    assert "3mo" in PERIODS
    # 3mo sits between 1mo and 6mo
    assert PERIODS.index("3mo") == PERIODS.index("1mo") + 1
    assert PERIODS.index("3mo") < PERIODS.index("6mo")
    assert "3mo" in PERIOD_LABELS


def test_period_dates_has_3mo():
    d = period_dates()
    assert "3mo" in d
    # ~92 days back
    delta_days = (d["current"] - d["3mo"]).days
    assert 88 <= delta_days <= 100


def test_pct_change_over_basic():
    idx = pd.date_range("2025-01-01", periods=30, freq="B")
    s = pd.Series([100.0] * 29 + [110.0], index=idx)
    # most recent vs 5 business days back (both 100 except last) -> +10%
    assert round(pct_change_over(s, 5), 2) == 10.0


def test_pct_change_over_insufficient_data_returns_na():
    s = pd.Series([100.0], index=pd.date_range("2025-01-01", periods=1, freq="B"))
    assert pct_change_over(s, 50) == "NA"
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_helpers.py -q`
Expected: FAIL (ImportError: `pct_change_over`; `3mo` missing).

- [ ] **Step 3: Implement**

In `helpers.py`, update the period definitions and add the helper. Replace the
`period_dates`, `PERIOD_LABELS`, `PERIODS` block with:
```python
def period_dates():
    """Return {period_key: datetime} for the standard comparison periods."""
    now = datetime.now()
    return {
        "current": now,
        "5d":      now - timedelta(days=7),
        "1mo":     now - timedelta(days=33),
        "3mo":     now - timedelta(days=92),
        "6mo":     now - timedelta(days=185),
        "1yr":     now - timedelta(days=370),
        "5yr":     now - timedelta(days=1830),
    }


PERIOD_LABELS = {
    "5d":  "5 Day Change",
    "1mo": "1 Month Change",
    "3mo": "3 Month Change",
    "6mo": "6 Month Change",
    "1yr": "1 Year Change",
    "5yr": "5 Year Change",
}

PERIODS = ["5d", "1mo", "3mo", "6mo", "1yr", "5yr"]


def pct_change_over(closes, n_sessions):
    """
    Percent change of the most recent close vs the close n_sessions trading
    days earlier. Returns a float, or 'NA' if there isn't enough data.
    """
    try:
        closes = closes.dropna()
        if len(closes) <= n_sessions:
            return "NA"
        current = float(closes.iloc[-1])
        past    = float(closes.iloc[-1 - n_sessions])
        if past == 0:
            return "NA"
        return round(((current - past) / abs(past)) * 100, 2)
    except Exception:
        return "NA"
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_helpers.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add helpers.py tests/test_helpers.py
git commit -m "feat: add 3-month period and pct_change_over helper"
```

---

## Phase 1 — Bulk Data Layer

### Task 1.1: `universe.py` — parse the StockAnalysis snapshot

The screener page server-renders a JS object array:
`...count:5572,data:[{s:"NVDA",n:"NVIDIA Corporation",marketCap:5113921696007,price:211.14,change:-1.45,industry:"Semiconductors",volume:289387683,peRatio:32.33},...]`
This is JS, not JSON (unquoted keys, leading-dot numbers like `-.14`). Parse by isolating the
array, then converting JS→JSON.

**Files:**
- Create: `universe.py`
- Test: `tests/test_universe.py`

- [ ] **Step 1: Write failing test for the parser (offline, no network)**

Create `tests/test_universe.py`:
```python
import pandas as pd
from universe import parse_universe_html, filter_by_market_cap

SAMPLE = (
    'junk before {type:"data",data:{count:3,data:['
    '{s:"NVDA",n:"NVIDIA Corporation",marketCap:5113921696007,price:211.14,'
    'change:-1.45,industry:"Semiconductors",volume:289387683,peRatio:32.33},'
    '{s:"AAPL",n:"Apple Inc.",marketCap:4583336313360,price:312.06,change:-.14,'
    'industry:"Consumer Electronics",volume:70030122,peRatio:37.82},'
    '{s:"TINY",n:"Tiny Co",marketCap:900000000,price:5.0,change:.5,'
    'industry:"Software",volume:1000,peRatio:8.0}'
    ']}} junk after'
)


def test_parse_universe_returns_all_rows():
    df = parse_universe_html(SAMPLE)
    assert list(df["symbol"]) == ["NVDA", "AAPL", "TINY"]
    assert df.loc[df.symbol == "AAPL", "name"].iloc[0] == "Apple Inc."
    # leading-dot number parsed
    assert round(float(df.loc[df.symbol == "AAPL", "change"].iloc[0]), 2) == -0.14
    assert df.loc[df.symbol == "NVDA", "industry"].iloc[0] == "Semiconductors"


def test_filter_by_market_cap():
    df = parse_universe_html(SAMPLE)
    big = filter_by_market_cap(df, 2e9)
    assert set(big["symbol"]) == {"NVDA", "AAPL"}   # TINY (0.9B) dropped
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_universe.py -q`
Expected: FAIL (ImportError: `universe`).

- [ ] **Step 3: Implement `universe.py`**

Create `universe.py`:
```python
"""
universe.py — Full US equity snapshot from StockAnalysis (free, no API key).

The screener page server-renders a JS object array. We isolate it, convert
JS->JSON, and return a DataFrame. On any failure, callers should fall back to
the S&P 500 list.
"""
import re
import json

import requests
import pandas as pd

from helpers import scraper_headers

SCREENER_URL = "https://stockanalysis.com/screener/"


def _extract_array_text(html):
    """Return the raw JS text of the inner data:[...] array, or None."""
    m = re.search(r"count:\d+,data:\[", html)
    if not m:
        return None
    start = m.end() - 1          # position of '['
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(html)):
        c = html[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                return html[start:i + 1]
    return None


def _js_array_to_json(arr_text):
    """Convert a JS object array to JSON text."""
    # Quote unquoted object keys:  {s:  ,n:  -> {"s": ,"n":
    txt = re.sub(r'([{,])\s*([A-Za-z_][A-Za-z0-9_]*)\s*:', r'\1"\2":', arr_text)
    # Fix leading-dot numbers:  :.5 -> :0.5  and  :-.5 -> :-0.5
    txt = re.sub(r':(-?)\.(\d)', r':\g<1>0.\2', txt)
    return txt


def parse_universe_html(html):
    """Parse screener HTML into a DataFrame. Raises ValueError if not parseable."""
    arr = _extract_array_text(html)
    if not arr:
        raise ValueError("could not locate data array in screener HTML")
    records = json.loads(_js_array_to_json(arr))
    rename = {
        "s": "symbol", "n": "name", "marketCap": "market_cap",
        "price": "price", "change": "change", "industry": "industry",
        "volume": "volume", "peRatio": "pe_ratio",
    }
    df = pd.DataFrame(records).rename(columns=rename)
    for col in rename.values():
        if col not in df.columns:
            df[col] = None
    return df[list(rename.values())]


def filter_by_market_cap(df, min_cap):
    """Return rows with market_cap >= min_cap (drops missing caps)."""
    cap = pd.to_numeric(df["market_cap"], errors="coerce")
    return df[cap >= min_cap].copy()


def fetch_universe():
    """
    Fetch the live full-market snapshot. Returns a DataFrame, or None on failure
    (caller falls back to the S&P 500 list).
    """
    try:
        resp = requests.get(SCREENER_URL, headers=scraper_headers(), timeout=30)
        resp.raise_for_status()
        df = parse_universe_html(resp.text)
        print(f"[Universe] Loaded {len(df)} US stocks from StockAnalysis.")
        return df
    except Exception as e:
        print(f"  [WARN] Universe fetch failed: {e}")
        return None
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_universe.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Live smoke check (network)**

Run:
```bash
python -c "from universe import fetch_universe; df=fetch_universe(); print(df.shape); print(df.head(3).to_string())"
```
Expected: prints a shape with ~5000+ rows and real tickers. If it fails, the parser
needs adjusting to the current page shape before continuing.

- [ ] **Step 6: Commit**

```bash
git add universe.py tests/test_universe.py
git commit -m "feat: add free full-market universe snapshot from StockAnalysis"
```

---

### Task 1.2: `price_history.py` — cached batch history

**Files:**
- Create: `price_history.py`
- Test: `tests/test_price_history.py`

- [ ] **Step 1: Write failing test (cache logic, no network)**

Create `tests/test_price_history.py`:
```python
import pandas as pd
from price_history import closes_for, volumes_for


def _fake_panel():
    idx = pd.date_range("2025-01-01", periods=10, freq="B")
    # MultiIndex columns: (ticker, field)
    cols = pd.MultiIndex.from_tuples(
        [("AAA", "Close"), ("AAA", "Volume"), ("BBB", "Close"), ("BBB", "Volume")]
    )
    data = {
        ("AAA", "Close"):  range(10, 20),
        ("AAA", "Volume"): range(100, 110),
        ("BBB", "Close"):  range(20, 30),
        ("BBB", "Volume"): range(200, 210),
    }
    return pd.DataFrame(data, index=idx, columns=cols)


def test_closes_for_extracts_series():
    panel = _fake_panel()
    s = closes_for(panel, "AAA")
    assert list(s) == list(range(10, 20))


def test_volumes_for_extracts_series():
    panel = _fake_panel()
    s = volumes_for(panel, "BBB")
    assert list(s) == list(range(200, 210))


def test_closes_for_missing_ticker_returns_none():
    panel = _fake_panel()
    assert closes_for(panel, "ZZZ") is None
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_price_history.py -q`
Expected: FAIL (ImportError).

- [ ] **Step 3: Implement `price_history.py`**

Create `price_history.py`:
```python
"""
price_history.py — Batch daily OHLCV history via yfinance, cached per day.

One pickle per calendar date under cache/. Downloads in chunks to avoid
per-ticker loops and rate limits.
"""
import os
from datetime import datetime

import pandas as pd
import yfinance as yf

CACHE_DIR  = "cache"
CHUNK_SIZE = 150


def _cache_path(date_str):
    return os.path.join(CACHE_DIR, f"history_{date_str}.pkl")


def closes_for(panel, ticker):
    """Return the Close Series for a ticker from a group_by='ticker' panel, or None."""
    try:
        s = panel[ticker]["Close"].dropna()
        return s if not s.empty else None
    except Exception:
        return None


def volumes_for(panel, ticker):
    """Return the Volume Series for a ticker, or None."""
    try:
        s = panel[ticker]["Volume"].dropna()
        return s if not s.empty else None
    except Exception:
        return None


def _download_chunk(tickers):
    df = yf.download(
        tickers, period="1y", interval="1d", group_by="ticker",
        auto_adjust=True, threads=True, progress=False,
    )
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    return df


def fetch_history(tickers, use_cache=True):
    """
    Download (or load cached) 1y daily history for the given tickers.
    Returns a wide DataFrame with MultiIndex columns (ticker, field).
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    path = _cache_path(date_str)

    if use_cache and os.path.exists(path):
        print(f"[History] Using cached history for {date_str}.")
        return pd.read_pickle(path)

    tickers = list(dict.fromkeys(tickers))
    chunks = [tickers[i:i + CHUNK_SIZE] for i in range(0, len(tickers), CHUNK_SIZE)]
    print(f"[History] Downloading {len(tickers)} tickers in {len(chunks)} chunks...")

    frames = []
    for i, chunk in enumerate(chunks, 1):
        try:
            frames.append(_download_chunk(chunk))
            print(f"  chunk {i}/{len(chunks)} OK ({len(chunk)} tickers)")
        except Exception as e:
            print(f"  chunk {i}/{len(chunks)} FAILED: {e}")

    if not frames:
        return pd.DataFrame()

    panel = pd.concat(frames, axis=1)
    panel.to_pickle(path)
    print(f"[History] Cached to {path}.")
    return panel
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_price_history.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Live smoke check (small batch, network)**

Run:
```bash
python -c "from price_history import fetch_history, closes_for; p=fetch_history(['AAPL','MSFT'], use_cache=False); print(len(closes_for(p,'AAPL')), 'days AAPL')"
```
Expected: prints ~250 days.

- [ ] **Step 6: Commit**

```bash
git add price_history.py tests/test_price_history.py
git commit -m "feat: add cached batch price-history layer"
```

---

## Phase 2 — Screens

### Task 2.1: `screens.py` — pure screen functions

All functions take `(universe_df, panel)` where `panel` comes from `fetch_history`, and return
lists of row dicts. Market-cap floors are passed in by the caller.

**Files:**
- Create: `screens.py`
- Test: `tests/test_screens.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_screens.py`:
```python
import pandas as pd
import pytest
import screens


def _panel_from(series_by_ticker):
    """Build a group_by='ticker' panel from {ticker: (closes_list, vols_list)}."""
    frames = {}
    n = max(len(v[0]) for v in series_by_ticker.values())
    idx = pd.date_range("2024-06-01", periods=n, freq="B")
    cols, data = [], {}
    for tk, (closes, vols) in series_by_ticker.items():
        cols += [(tk, "Close"), (tk, "Volume")]
        data[(tk, "Close")]  = pd.Series(closes, index=idx[-len(closes):]).reindex(idx)
        data[(tk, "Volume")] = pd.Series(vols, index=idx[-len(vols):]).reindex(idx)
    return pd.DataFrame(data, index=idx, columns=pd.MultiIndex.from_tuples(cols))


def test_near_ma_flags_price_within_5pct(sample_universe):
    # AAA: 210 closes flat at 100 -> 50d & 200d MA == 100, price 100 -> within 5%
    panel = _panel_from({"AAA": ([100.0] * 210, [1] * 210)})
    rows = screens.near_ma(sample_universe, panel, min_cap=2e9, pct=5.0)
    assert any(r["symbol"] == "AAA" for r in rows)


def test_near_ma_excludes_small_cap(sample_universe):
    # CCC market cap is 1e9 < 2e9 floor; even if near MA it must be excluded
    panel = _panel_from({"CCC": ([10.0] * 210, [1] * 210)})
    rows = screens.near_ma(sample_universe, panel, min_cap=2e9, pct=5.0)
    assert all(r["symbol"] != "CCC" for r in rows)


def test_abnormal_volume_flags_spike(sample_universe):
    # last volume 10x the trailing average
    vols = [1000] * 209 + [10000]
    panel = _panel_from({"AAA": ([100.0] * 210, vols)})
    rows = screens.abnormal_volume(sample_universe, panel, min_cap=2e9, mult=1.5)
    assert any(r["symbol"] == "AAA" for r in rows)


def test_momentum_pullback(sample_universe):
    # up >50% over the year but down >10% over the last 5 sessions
    closes = [50.0] * 150 + [120.0] * 54 + [100.0]   # yr-ago ~50, recent peak 120, now 100
    panel = _panel_from({"AAA": (closes, [1] * len(closes))})
    rows = screens.momentum_pullback(sample_universe, panel, min_cap=2e9)
    assert any(r["symbol"] == "AAA" for r in rows)


def test_reversal_bounce(sample_universe):
    # down >15% over the year but up >5% over the last 5 sessions
    closes = [100.0] * 150 + [70.0] * 54 + [78.0]
    panel = _panel_from({"AAA": (closes, [1] * len(closes))})
    rows = screens.reversal_bounce(sample_universe, panel, min_cap=2e9)
    assert any(r["symbol"] == "AAA" for r in rows)
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_screens.py -q`
Expected: FAIL (ImportError: `screens`).

- [ ] **Step 3: Implement `screens.py`**

Create `screens.py`:
```python
"""
screens.py — Pure screen functions over (universe_df, history panel).

No network. Each returns a list of row dicts ready for the PDF tables.
"""
import pandas as pd

from helpers import pct_change_over, format_pct, format_val
from price_history import closes_for, volumes_for

# trading-session offsets per lookback
SESS = {"5d": 5, "1mo": 21, "3mo": 63, "1yr": 252}


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
    """Up >50% over the year AND down >10% over week, month, or 3-month."""
    out = []
    for symbol in _cap_filtered(universe_df, min_cap)["symbol"]:
        closes = closes_for(panel, symbol)
        if closes is None or len(closes) < 252:
            continue
        yr = pct_change_over(closes, SESS["1yr"])
        if yr == "NA" or yr <= 50:
            continue
        pulls = [pct_change_over(closes, SESS[p]) for p in ("5d", "1mo", "3mo")]
        if any(p != "NA" and p <= -10 for p in pulls):
            out.append(_base_row(universe_df, symbol, closes))
    return out


def reversal_bounce(universe_df, panel, min_cap):
    """Down >15% over the year AND up >5% over the week."""
    out = []
    for symbol in _cap_filtered(universe_df, min_cap)["symbol"]:
        closes = closes_for(panel, symbol)
        if closes is None or len(closes) < 252:
            continue
        yr = pct_change_over(closes, SESS["1yr"])
        wk = pct_change_over(closes, SESS["5d"])
        if yr != "NA" and yr <= -15 and wk != "NA" and wk >= 5:
            out.append(_base_row(universe_df, symbol, closes))
    return out
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_screens.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add screens.py tests/test_screens.py
git commit -m "feat: add pure screen functions (near-MA, volume, momentum, reversal)"
```

---

## Phase 3 — PDF Builder

### Task 3.1: Fix the font-reset bug

**Files:**
- Modify: `pdf_builder.py` (`ReportPDF.table`)
- Test: `tests/test_pdf_font.py`

- [ ] **Step 1: Write failing test**

The bug: after a page-break `draw_header()` (sets bold), body rows are drawn without
resetting to regular. Test asserts the body font style is regular after a multi-row render
that forces a page break.

Create `tests/test_pdf_font.py`:
```python
from pdf_builder import ReportPDF, FONT


def test_body_font_regular_after_page_break():
    pdf = ReportPDF("test-date")
    pdf.section_title("S")
    headers = ["A", "B"]
    widths  = [140, 140]
    rows = [[f"r{i}", "x"] for i in range(120)]   # enough rows to force >=1 page break
    pdf.table(headers, widths, rows)
    # After rendering, the active font must be the regular body face, not bold.
    assert pdf.font_style == ""        # "" = regular, "B" = bold
    assert pdf.font_family == FONT.lower()
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_pdf_font.py -q`
Expected: FAIL (`font_style == "B"` after the break-path header draw).

- [ ] **Step 3: Implement the fix**

In `pdf_builder.py::ReportPDF.table`, set the body font via a constant and reset it after
every `draw_header()`. Replace the body-font line and the page-break branch:
```python
        BODY_SIZE = 6.5   # was 6 — small bump for readability

        draw_header()
        self.set_font(FONT, "", BODY_SIZE)

        for row_idx, row in enumerate(rows):
            # Auto page break with repeated header
            if self.get_y() + row_h > PAGE_H - 14:
                self.add_page()
                draw_header()
                self.set_font(FONT, "", BODY_SIZE)   # <-- reset body font after header
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_pdf_font.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add pdf_builder.py tests/test_pdf_font.py
git commit -m "fix: reset body font after repeated table header on page breaks"
```

---

### Task 3.2: Gradient percentage cells

**Files:**
- Modify: `pdf_builder.py`
- Test: `tests/test_pdf_gradient.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_pdf_gradient.py`:
```python
from pdf_builder import pct_fill_color


def test_zero_change_is_white():
    assert pct_fill_color(0.0) == (255, 255, 255)


def test_strong_positive_is_darker_green_than_weak():
    weak = pct_fill_color(2.0)
    strong = pct_fill_color(25.0)
    # green channel stays high, red+blue drop more for stronger moves
    assert strong[0] < weak[0]
    assert strong[2] < weak[2]


def test_strong_negative_is_darker_red_than_weak():
    weak = pct_fill_color(-2.0)
    strong = pct_fill_color(-25.0)
    assert strong[1] < weak[1]      # less green => redder
    assert strong[2] < weak[2]


def test_clamps_beyond_range():
    assert pct_fill_color(999) == pct_fill_color(20)     # saturates at +-20%
    assert pct_fill_color(-999) == pct_fill_color(-20)
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_pdf_gradient.py -q`
Expected: FAIL (ImportError: `pct_fill_color`).

- [ ] **Step 3: Implement `pct_fill_color`**

Add to `pdf_builder.py` (near the color palette):
```python
def pct_fill_color(pct, saturate=20.0):
    """
    Map a percentage change to a cell background color.
    0% -> white; positive -> green (darker as magnitude grows);
    negative -> red (darker as magnitude grows). Saturates at +-`saturate`%.
    """
    try:
        v = float(pct)
    except (TypeError, ValueError):
        return (255, 255, 255)
    frac = max(-1.0, min(1.0, v / saturate))
    intensity = abs(frac)
    if frac > 0:   # green: keep G high, drop R and B
        r = int(255 - 175 * intensity)
        g = int(255 - 35 * intensity)
        b = int(255 - 175 * intensity)
    elif frac < 0:  # red: keep R high, drop G and B
        r = int(255 - 35 * intensity)
        g = int(255 - 175 * intensity)
        b = int(255 - 175 * intensity)
    else:
        return (255, 255, 255)
    return (r, g, b)
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_pdf_gradient.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Wire gradient into the table renderer**

In `ReportPDF.table`, add an optional `gradient_cols=None` param. For columns in
`gradient_cols`, set the cell fill from `pct_fill_color(value)` instead of the alternating
row color. Update the signature and the per-cell fill logic:
```python
    def table(self, headers, col_widths, rows, pct_cols=None, gradient_cols=None):
        if pct_cols is None:
            pct_cols = set()
        if gradient_cols is None:
            gradient_cols = set()
        ...
            for col_idx, (val, w) in enumerate(zip(row, col_widths)):
                val = _safe(val)
                # choose fill: gradient overrides alternating shading
                if col_idx in gradient_cols and val not in ("NA", "—", ""):
                    self.set_fill_color(*pct_fill_color(
                        val.replace("%", "").replace("+", "").strip()))
                else:
                    self.set_fill_color(*fill_color)
                ...
                self.cell(w, row_h, val, border=1, align=align, fill=True)
```
(Keep the existing text color-coding logic.)

- [ ] **Step 6: Run full PDF test suite**

Run: `python -m pytest tests/test_pdf_font.py tests/test_pdf_gradient.py -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add pdf_builder.py tests/test_pdf_gradient.py
git commit -m "feat: gradient red/green cells scaled by percentage magnitude"
```

---

### Task 3.3: Header page (mantra + past mistakes)

**Files:**
- Create: `mistakes.txt`
- Modify: `pdf_builder.py`, `config.py`
- Test: `tests/test_mistakes.py`

- [ ] **Step 1: Create the editable mistakes file**

Create `mistakes.txt`:
```
# Past trading mistakes — one ticker per line. Add a note after a space if you like.
CAR
AGI
UNH
TNZ
AEO
FVI
```

- [ ] **Step 2: Write failing test for the loader**

Create `tests/test_mistakes.py`:
```python
from config import load_mistakes


def test_load_mistakes_reads_tickers(tmp_path):
    f = tmp_path / "m.txt"
    f.write_text("# comment\nCAR\nAGI lost on earnings\n\nUNH\n")
    out = load_mistakes(str(f))
    assert out == ["CAR", "AGI lost on earnings", "UNH"]


def test_load_mistakes_missing_file_returns_empty():
    assert load_mistakes("does_not_exist_12345.txt") == []
```

- [ ] **Step 3: Run to verify failure**

Run: `python -m pytest tests/test_mistakes.py -q`
Expected: FAIL (ImportError: `load_mistakes`).

- [ ] **Step 4: Implement loader + constant**

Add to `config.py`:
```python
MANTRA = ["Filter", "Assess", "Risk", "Position", "Entrance", "Exit"]
MISTAKES_FILE = "mistakes.txt"


def load_mistakes(path=MISTAKES_FILE):
    """Read non-comment, non-empty lines from the mistakes file."""
    try:
        with open(path, encoding="utf-8") as f:
            return [ln.strip() for ln in f
                    if ln.strip() and not ln.strip().startswith("#")]
    except FileNotFoundError:
        return []
```

- [ ] **Step 5: Run to verify pass**

Run: `python -m pytest tests/test_mistakes.py -q`
Expected: PASS.

- [ ] **Step 6: Render the header page**

Add to `pdf_builder.py` and call it right after `_cover_page` in `build_pdf`:
```python
def _strategy_page(pdf, mantra, mistakes):
    pdf.add_page()
    pdf.set_font(FONT_B, "B", 18)
    pdf.set_text_color(*COLOR_SEC_TITLE)
    pdf.cell(USABLE, 12, "Trading Discipline", align="C")
    pdf.ln(16)

    pdf.set_font(FONT_B, "B", 13)
    pdf.set_text_color(*COLOR_NEUTRAL)
    pdf.cell(USABLE, 8, "Mantra", align="L")
    pdf.ln(9)
    pdf.set_font(FONT, "", 12)
    pdf.cell(USABLE, 8, _safe("  ->  ".join(mantra)), align="L")
    pdf.ln(16)

    pdf.set_font(FONT_B, "B", 13)
    pdf.cell(USABLE, 8, "Past Mistakes", align="L")
    pdf.ln(9)
    pdf.set_font(FONT, "", 11)
    if mistakes:
        for m in mistakes:
            pdf.cell(USABLE, 7, _safe(f"  - {m}"), align="L")
            pdf.ln(7)
    else:
        pdf.cell(USABLE, 7, "  (none recorded)", align="L")
        pdf.ln(7)
```
In `build_pdf`, add a parameter `mantra` and `mistakes` (defaulting via config) and call
`_strategy_page(pdf, mantra, mistakes)` after `_cover_page(pdf, report_date)`.

- [ ] **Step 7: Commit**

```bash
git add mistakes.txt config.py pdf_builder.py tests/test_mistakes.py
git commit -m "feat: strategy header page with mantra and past-mistakes list"
```

---

## Phase 4 — Section Rewiring

### Task 4.1: Section 1 — index rows + 3-month column

**Files:**
- Modify: `config.py` (index list), `section1_macro.py`, `pdf_builder.py` (S1 headers/widths/rows)
- Test: `tests/test_section1.py`

- [ ] **Step 1: Add index config**

Add to `config.py`:
```python
# Index/valuation rows shown ABOVE the FRED series in Section 1.
# yfinance-backed tickers:
MACRO_INDEX_TICKERS = {
    "^GSPC": ("S&P 500",       "Index"),
    "^DJI":  ("Dow Jones",     "Index"),
    "QQQ":   ("Invesco QQQ",   "USD/Share"),
    "^RUT":  ("Russell 2000",  "Index"),
    "DX-Y.NYB": ("US Dollar Index (DXY)", "Index"),
}
# Scraped valuation gauges (multpl.com): rendered as label -> (value, source)
MACRO_SCRAPED = ["Shiller PE", "Buffett Indicator"]
```

- [ ] **Step 2: Write failing test**

Create `tests/test_section1.py`:
```python
from section1_macro import _index_rows_from_history


def test_index_rows_have_3mo_and_label(monkeypatch):
    import pandas as pd
    idx = pd.date_range("2024-06-01", periods=260, freq="B")
    closes = pd.Series([100 + i for i in range(260)], index=idx)

    class FakePanel:
        def __getitem__(self, k): raise KeyError

    # inject a closes provider
    rows = _index_rows_from_history({"^GSPC": ("S&P 500", "Index")},
                                    lambda t: closes)
    r = rows[0]
    assert r["metric"].startswith("S&P 500")
    assert "3mo" in r and r["3mo"] != ""
```

- [ ] **Step 3: Run to verify failure**

Run: `python -m pytest tests/test_section1.py -q`
Expected: FAIL (ImportError).

- [ ] **Step 4: Implement index rows + thread 3mo through**

Add to `section1_macro.py`:
```python
from helpers import pct_change_over

_S1_SESS = {"5d": 5, "1mo": 21, "3mo": 63, "6mo": 126, "1yr": 252, "5yr": 1260}


def _index_rows_from_history(index_map, closes_provider):
    """Build Section-1 index rows from a closes_provider(ticker)->Series|None."""
    rows = []
    for ticker, (label, units) in index_map.items():
        closes = closes_provider(ticker)
        row = {"metric": f"{label} [{units}]",
               "current": "NA" if closes is None else f"{float(closes.iloc[-1]):.2f}"}
        for p in ("5d", "1mo", "3mo", "6mo", "1yr", "5yr"):
            row[p] = ("NA" if closes is None
                      else format_pct(pct_change_over(closes, _S1_SESS[p])))
        rows.append(row)
    return rows
```
Then in `fetch_macro_data`: also compute `row["3mo"]` for every FRED series (the period loop
already iterates `PERIODS`, which now includes `3mo` — no change needed there beyond the
helper update). Fetch index closes via `yfinance` and prepend `_index_rows_from_history(...)`
plus the two scraped gauges (Shiller PE, Buffett Indicator from multpl.com; "NA" on failure).

- [ ] **Step 5: Update PDF S1 layout for 8 columns**

In `pdf_builder.py`, update Section 1 headers/widths/rows to include the 3-month column:
```python
S1_HEADERS = ["Metric [Units]", "Current", "5 Day %", "1 Month %", "3 Month %",
              "6 Month %", "1 Year %", "5 Year %"]
S1_WIDTHS  = [90, 26, 21, 21, 21, 21, 21, 21]
_diff = USABLE - sum(S1_WIDTHS)
S1_WIDTHS[0] += _diff


def _s1_rows(data):
    return [[r["metric"], r["current"], r["5d"], r["1mo"], r["3mo"],
             r["6mo"], r["1yr"], r["5yr"]] for r in data]
```
Update `PCT_COLS_STD` to `{2, 3, 4, 5, 6, 7}` for the new 8-column standard tables.

- [ ] **Step 6: Run to verify pass**

Run: `python -m pytest tests/test_section1.py -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add config.py section1_macro.py pdf_builder.py tests/test_section1.py
git commit -m "feat: Section 1 index rows + 3-month column"
```

---

### Task 4.2: Section 2 — 3-month column

**Files:**
- Modify: `pdf_builder.py` (S2 headers/widths/rows)

- [ ] **Step 1: Update S2 layout**

Section 2 already builds rows over `PERIODS` (now includes `3mo`). Update the PDF layout to
mirror S1:
```python
S2_HEADERS = ["Commodity [Units]", "Current Price", "5 Day %", "1 Month %", "3 Month %",
              "6 Month %", "1 Year %", "5 Year %"]
S2_WIDTHS  = S1_WIDTHS[:]


def _s2_rows(data):
    return [[r["commodity"], r["current"], r["5d"], r["1mo"], r["3mo"],
             r["6mo"], r["1yr"], r["5yr"]] for r in data]
```

- [ ] **Step 2: Smoke test the build path**

Run:
```bash
python -c "import pdf_builder as p; print(len(p.S2_HEADERS), len(p.S2_WIDTHS))"
```
Expected: `8 8`.

- [ ] **Step 3: Commit**

```bash
git add pdf_builder.py
git commit -m "feat: Section 2 3-month column"
```

---

### Task 4.3: Section 3 — StockAnalysis industries, drop market cap, add 3-month

**Files:**
- Modify: `section3_industries.py`, `pdf_builder.py` (S3 layout)
- Test: `tests/test_section3.py`

- [ ] **Step 1: Write failing test (aggregation from universe)**

Create `tests/test_section3.py`:
```python
from section3_industries import aggregate_industries


def test_aggregate_groups_by_industry(sample_universe):
    rows = aggregate_industries(sample_universe)
    inds = {r["industry"] for r in rows}
    assert "Software" in inds and "Biotechnology" in inds
    # each row carries an average daily % change field
    soft = next(r for r in rows if r["industry"] == "Software")
    assert "change" in soft
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_section3.py -q`
Expected: FAIL (ImportError).

- [ ] **Step 3: Implement industry aggregation**

The universe snapshot already carries `industry` and per-name `change`. For 3-month and other
periods, the execution agent should map each industry to a representative ETF OR average the
member names' period changes from the history panel. Minimal v1: aggregate the snapshot's
day `change` by industry, and compute period changes by averaging member `pct_change_over`
from the panel.

Add to `section3_industries.py`:
```python
import pandas as pd
from helpers import format_pct, pct_change_over
from price_history import closes_for

_S3_SESS = {"5d": 5, "1mo": 21, "3mo": 63, "6mo": 126, "1yr": 252, "5yr": 1260}


def aggregate_industries(universe_df, panel=None):
    """
    Group the universe by industry. Returns row dicts with the average daily
    change and (if a panel is given) average period changes.
    """
    rows = []
    for industry, grp in universe_df.groupby("industry"):
        if not industry:
            continue
        day_change = pd.to_numeric(grp["change"], errors="coerce").mean()
        row = {"industry": industry, "change": format_pct(round(float(day_change), 2))}
        for p, n in _S3_SESS.items():
            if panel is None:
                row[p] = "NA"
                continue
            vals = []
            for sym in grp["symbol"]:
                c = closes_for(panel, sym)
                if c is not None:
                    v = pct_change_over(c, n)
                    if v != "NA":
                        vals.append(v)
            row[p] = format_pct(round(sum(vals) / len(vals), 2)) if vals else "NA"
        rows.append(row)
    rows.sort(key=lambda r: r["industry"])
    return rows
```
Update `fetch_industries_data()` to call `aggregate_industries(universe_df, panel)` instead of
the ETF loop (universe + panel passed in from `main.py`).

- [ ] **Step 4: Update S3 PDF layout (no Market Cap, add 3-month)**

In `pdf_builder.py`:
```python
S3_HEADERS = ["Industry", "5 Day %", "1 Month %", "3 Month %", "6 Month %", "1 Year %", "5 Year %"]
S3_WIDTHS  = [120, 27, 27, 27, 27, 27, 26]
_diff3 = USABLE - sum(S3_WIDTHS)
S3_WIDTHS[0] += _diff3
S3_PCT_COLS = {1, 2, 3, 4, 5, 6}


def _s3_rows(data):
    return [[r.get("industry", "—"), r.get("5d", "—"), r.get("1mo", "—"),
             r.get("3mo", "—"), r.get("6mo", "—"), r.get("1yr", "—"),
             r.get("5yr", "—")] for r in data]
```
Update the `build_pdf` Section-3 call to use `pct_cols=S3_PCT_COLS`.

- [ ] **Step 5: Run to verify pass**

Run: `python -m pytest tests/test_section3.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add section3_industries.py pdf_builder.py tests/test_section3.py
git commit -m "feat: Section 3 industries from StockAnalysis universe, drop market cap, add 3-month"
```

---

### Task 4.4: Section 4 — split into three tables + names + gradient

**Files:**
- Modify: `section4_companies.py`, `pdf_builder.py`, `main.py` (call shape)
- Test: `tests/test_section4.py`

- [ ] **Step 1: Write failing test for splitting**

Create `tests/test_section4.py`:
```python
import pandas as pd
from section4_companies import split_movers


def test_split_movers_buckets():
    enriched = [
        {"symbol": "AAA", "company": "Alpha", "5d_raw": 12.0, "1mo_raw": 5.0,  "vol_ratio": 0.8},
        {"symbol": "BBB", "company": "Beta",  "5d_raw": 3.0,  "1mo_raw": 25.0, "vol_ratio": 0.9},
        {"symbol": "CCC", "company": "Gamma", "5d_raw": 1.0,  "1mo_raw": 2.0,  "vol_ratio": 3.0},
    ]
    five, month, vol = split_movers(enriched)
    assert [r["symbol"] for r in five]  == ["AAA"]
    assert [r["symbol"] for r in month] == ["BBB"]
    assert [r["symbol"] for r in vol]   == ["CCC"]
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_section4.py -q`
Expected: FAIL (ImportError).

- [ ] **Step 3: Implement `split_movers`**

Add to `section4_companies.py`:
```python
def split_movers(enriched):
    """
    Split enriched rows into three buckets:
      >10% abs 5-day, >20% abs 1-month, volume spike (>1x avg).
    Each row goes to the first bucket it qualifies for (no duplicates).
    Returns (five_day, one_month, volume).
    """
    five, month, vol = [], [], []
    for r in enriched:
        f = r.get("5d_raw"); m = r.get("1mo_raw"); v = r.get("vol_ratio")
        if f is not None and abs(f) > 10:
            five.append(r)
        elif m is not None and abs(m) > 20:
            month.append(r)
        elif v is not None and v > 1.0:
            vol.append(r)
    for bucket, key in ((five, "5d_raw"), (month, "1mo_raw")):
        bucket.sort(key=lambda r: abs(r.get(key) or 0), reverse=True)
    vol.sort(key=lambda r: r.get("vol_ratio") or 0, reverse=True)
    return five, month, vol
```
Refactor `fetch_companies_data` to build `enriched` from the universe + panel (not a per-ticker
loop) and return `split_movers(enriched)` as a dict
`{"five_day": [...], "one_month": [...], "volume": [...]}`.

- [ ] **Step 4: Update PDF for three S4 tables with gradient**

In `pdf_builder.py`, add a 3-column-group renderer. New layout (with company name + 3-month):
```python
S4_HEADERS = ["Company", "Ticker", "Price", "5 Day %", "1 Month %", "3 Month %", "Vol x"]
S4_WIDTHS  = [110, 24, 24, 30, 30, 30, 33]
_diff4 = USABLE - sum(S4_WIDTHS)
S4_WIDTHS[0] += _diff4
S4_PCT_COLS = {3, 4, 5}
S4_GRADIENT_COLS = {3, 4, 5}


def _s4_rows(data):
    return [[r.get("company", "—"), r.get("symbol", r.get("ticker", "—")),
             r.get("price", "—"), r.get("5d", "—"), r.get("1mo", "—"),
             r.get("3mo", "—"), r.get("vol_ratio", "—")] for r in data]
```
In `build_pdf`, render three sub-titled tables for Section 4:
```python
    pdf.section_title("Section 4 - Companies of Interest")
    buckets = companies_data or {}
    for sub, title in (("five_day",  ">10% 5-Day Movers"),
                       ("one_month", ">20% 1-Month Movers"),
                       ("volume",    "Volume Spikes")):
        rows = buckets.get(sub, [])
        pdf.set_font(FONT_B, "B", 9); pdf.set_text_color(*COLOR_NEUTRAL)
        pdf.cell(USABLE, 7, _safe(title), align="L"); pdf.ln(8)
        if rows:
            pdf.table(S4_HEADERS, S4_WIDTHS, _s4_rows(rows),
                      pct_cols=S4_PCT_COLS, gradient_cols=S4_GRADIENT_COLS)
        else:
            pdf.no_data_notice()
```

- [ ] **Step 5: Run to verify pass**

Run: `python -m pytest tests/test_section4.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add section4_companies.py pdf_builder.py tests/test_section4.py
git commit -m "feat: split Section 4 into three movers tables with names + gradient"
```

---

### Task 4.5: Section 5 — earnings ≥$5B, drop EPS/Rev, widen Time

**Files:**
- Modify: `section5_earnings.py`, `pdf_builder.py` (S5 layout)
- Test: `tests/test_section5.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_section5.py`:
```python
from section5_earnings import filter_by_market_cap_5b


def test_drop_under_5b(sample_universe):
    rows = [
        {"symbol": "AAA", "company": "Alpha", "time": "amc"},   # 6e9 -> keep
        {"symbol": "BBB", "company": "Beta",  "time": "bmo"},   # 3e9 -> drop
        {"symbol": "CCC", "company": "Gamma", "time": "amc"},   # 1e9 -> drop
        {"symbol": "ZZZ", "company": "Zeta",  "time": "amc"},   # not in universe -> drop
    ]
    out = filter_by_market_cap_5b(rows, sample_universe, min_cap=5e9)
    assert [r["symbol"] for r in out] == ["AAA"]
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_section5.py -q`
Expected: FAIL (ImportError).

- [ ] **Step 3: Implement the filter**

Add to `section5_earnings.py`:
```python
import pandas as pd


def filter_by_market_cap_5b(rows, universe_df, min_cap=5e9):
    """Keep only earnings rows whose symbol has market cap >= min_cap in the universe."""
    caps = {r["symbol"]: c for r, c in zip(
        universe_df.to_dict("records"),
        pd.to_numeric(universe_df["market_cap"], errors="coerce"))}
    # build symbol->cap map robustly
    cap_map = dict(zip(universe_df["symbol"],
                       pd.to_numeric(universe_df["market_cap"], errors="coerce")))
    out = []
    for r in rows:
        cap = cap_map.get(r.get("symbol"))
        if cap is not None and cap >= min_cap:
            out.append(r)
    return out
```
Update `fetch_earnings_data` to accept `universe_df` and apply
`filter_by_market_cap_5b(rows, universe_df)` before returning. Keep the existing "next 5 days"
window logic.

- [ ] **Step 4: Update S5 PDF layout (drop EPS/Rev, widen Time)**

In `pdf_builder.py`:
```python
S5_HEADERS = ["Date", "Ticker", "Company", "Time", "Mkt Cap"]
S5_WIDTHS  = [40, 26, 150, 35, 30]
_diff5 = USABLE - sum(S5_WIDTHS)
S5_WIDTHS[2] += _diff5


def _s5_rows(data):
    return [[r.get("date", "—"), r.get("symbol", "—"), r.get("company", "—"),
             r.get("time", "—"), r.get("market_cap", "—")] for r in data]
```

- [ ] **Step 5: Run to verify pass**

Run: `python -m pytest tests/test_section5.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add section5_earnings.py pdf_builder.py tests/test_section5.py
git commit -m "feat: Section 5 earnings >=$5B only, drop EPS/Rev, widen Time"
```

---

### Task 4.6: Sections 6/7/8 — new screen tables in the PDF

**Files:**
- Modify: `pdf_builder.py` (new layouts + build_pdf calls)
- Test: `tests/test_pdf_new_sections.py`

- [ ] **Step 1: Write failing test for the row mappers**

Create `tests/test_pdf_new_sections.py`:
```python
from pdf_builder import _screen_rows


def test_screen_rows_maps_fields():
    data = [{"company": "Alpha", "symbol": "AAA", "price": "100.00",
             "5d": "+2.00%", "1mo": "-1.00%", "3mo": "+5.00%", "1yr": "+60.00%"}]
    rows = _screen_rows(data)
    assert rows[0][0] == "Alpha"
    assert rows[0][1] == "AAA"
    assert rows[0][-1] == "+60.00%"
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_pdf_new_sections.py -q`
Expected: FAIL (ImportError).

- [ ] **Step 3: Implement shared screen layout + section calls**

Add to `pdf_builder.py`:
```python
SCREEN_HEADERS = ["Company", "Ticker", "Price", "5 Day %", "1 Month %", "3 Month %", "1 Year %"]
SCREEN_WIDTHS  = [110, 24, 26, 30, 30, 30, 31]
_diffS = USABLE - sum(SCREEN_WIDTHS)
SCREEN_WIDTHS[0] += _diffS
SCREEN_PCT_COLS = {3, 4, 5, 6}
SCREEN_GRADIENT_COLS = {3, 4, 5, 6}


def _screen_rows(data):
    return [[r.get("company", "—"), r.get("symbol", "—"), r.get("price", "—"),
             r.get("5d", "—"), r.get("1mo", "—"), r.get("3mo", "—"),
             r.get("1yr", "—")] for r in data]


def _screen_section(pdf, title, subtables):
    """subtables: list of (subtitle, rows)."""
    pdf.section_title(title)
    any_rows = False
    for subtitle, rows in subtables:
        pdf.set_font(FONT_B, "B", 9); pdf.set_text_color(*COLOR_NEUTRAL)
        pdf.cell(USABLE, 7, _safe(subtitle), align="L"); pdf.ln(8)
        if rows:
            any_rows = True
            pdf.table(SCREEN_HEADERS, SCREEN_WIDTHS, _screen_rows(rows),
                      pct_cols=SCREEN_PCT_COLS, gradient_cols=SCREEN_GRADIENT_COLS)
        else:
            pdf.no_data_notice()
    return any_rows
```
Extend `build_pdf` signature with `momentum_data`, `near_ma_data`, `volume_data` (each a dict
or list), and after Section 5 add:
```python
    _screen_section(pdf, "Section 6 - Momentum", [
        ("Uptrend Pullback (up >50%/yr, down >10% wk/mo/3mo)",
         (momentum_data or {}).get("pullback", [])),
        ("Downtrend Bounce (down >15%/yr, up >5%/wk)",
         (momentum_data or {}).get("bounce", [])),
    ])
    _screen_section(pdf, "Section 7 - Near 50/200-Day Moving Average (within 5%, >=$2B)",
                    [("", near_ma_data or [])])
    _screen_section(pdf, "Section 8 - Abnormal Volume (>=$2B)",
                    [("", volume_data or [])])
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_pdf_new_sections.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add pdf_builder.py tests/test_pdf_new_sections.py
git commit -m "feat: add Section 6/7/8 momentum, near-MA, abnormal-volume tables"
```

---

## Phase 5 — Orchestration & Schedule

### Task 5.1: Wire the data layer + new sections into `main.py`

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Build the shared data once, pass to sections**

In `generate_and_send`, before the section calls, build the shared layer:
```python
    from universe import fetch_universe, filter_by_market_cap
    from price_history import fetch_history
    import screens
    from config import MIN_CAP_SCREENS, MIN_CAP_EARNINGS

    universe_df = fetch_universe()
    if universe_df is not None:
        screen_universe = filter_by_market_cap(universe_df, MIN_CAP_SCREENS)
        panel = fetch_history(list(screen_universe["symbol"]))
    else:
        screen_universe, panel = None, None
```
Wrap each in try/except like the existing sections.

- [ ] **Step 2: Compute the new screens (guarded)**

```python
    if universe_df is not None and panel is not None and not panel.empty:
        momentum_data = {
            "pullback": screens.momentum_pullback(universe_df, panel, MIN_CAP_SCREENS),
            "bounce":   screens.reversal_bounce(universe_df, panel, MIN_CAP_SCREENS),
        }
        near_ma_data = screens.near_ma(universe_df, panel, MIN_CAP_SCREENS)
        volume_data  = screens.abnormal_volume(universe_df, panel, MIN_CAP_SCREENS)
    else:
        momentum_data, near_ma_data, volume_data = {}, [], []
```

- [ ] **Step 3: Pass universe/panel into Sections 3/4/5 and new data into build_pdf**

Update the existing section calls to pass `universe_df`/`panel` where the refactors require
them, and extend the `build_pdf(...)` call with
`momentum_data=momentum_data, near_ma_data=near_ma_data, volume_data=volume_data,
mantra=MANTRA, mistakes=load_mistakes()`.

- [ ] **Step 4: Smoke test no-email full run**

Run: `python main.py --no-email`
Expected: completes, prints "[Universe] Loaded N", builds `stock_report.pdf`. Open the PDF and
confirm: strategy page present, 3-month columns, 3 S4 tables, S6/7/8 present, fonts consistent
across page breaks.

- [ ] **Step 5: Commit**

```bash
git add main.py
git commit -m "feat: wire universe/history/screens into the report pipeline"
```

---

### Task 5.2: Twice-weekly ET schedule (Wed 8PM, Sat 8AM)

**Files:**
- Modify: `config.py`, `main.py`
- Test: `tests/test_schedule.py`

- [ ] **Step 1: Add schedule + cap constants to config**

Add to `config.py`:
```python
# Delivery schedule (Eastern Time)
SEND_SCHEDULE = [("wednesday", "20:00"), ("saturday", "08:00")]

# Market-cap floors
MIN_CAP_SCREENS  = 2e9
MIN_CAP_EARNINGS = 5e9
```

- [ ] **Step 2: Write failing test for the due-check**

Create `tests/test_schedule.py`:
```python
from datetime import datetime
import pytz
from main import is_send_due


ET = pytz.timezone("America/New_York")


def test_wed_8pm_is_due():
    t = ET.localize(datetime(2026, 6, 3, 20, 0))   # Wednesday
    assert is_send_due(t, [("wednesday", "20:00"), ("saturday", "08:00")])


def test_sat_8am_is_due():
    t = ET.localize(datetime(2026, 6, 6, 8, 0))     # Saturday
    assert is_send_due(t, [("wednesday", "20:00"), ("saturday", "08:00")])


def test_wed_noon_not_due():
    t = ET.localize(datetime(2026, 6, 3, 12, 0))
    assert not is_send_due(t, [("wednesday", "20:00"), ("saturday", "08:00")])
```

- [ ] **Step 3: Run to verify failure**

Run: `python -m pytest tests/test_schedule.py -q`
Expected: FAIL (ImportError: `is_send_due`).

- [ ] **Step 4: Implement the ET-aware scheduler**

Replace `run_scheduler` (and add `is_send_due`) in `main.py`:
```python
def is_send_due(now_et, schedule_spec):
    """True if now_et (tz-aware ET) matches any (weekday_name, 'HH:MM') slot to the minute."""
    day = now_et.strftime("%A").lower()
    hhmm = now_et.strftime("%H:%M")
    return any(day == d and hhmm == t for d, t in schedule_spec)


def run_scheduler():
    """Poll once a minute; send when an ET schedule slot matches. Avoids double-sends."""
    from config import SEND_SCHEDULE
    tz = pytz.timezone(REPORT_TIMEZONE)
    print(f"[Scheduler] Active. Slots (ET): {SEND_SCHEDULE}. Ctrl+C to stop.")
    last_fired = None
    while True:
        now_et = datetime.now(tz)
        stamp = now_et.strftime("%Y-%m-%d %H:%M")
        if is_send_due(now_et, SEND_SCHEDULE) and stamp != last_fired:
            last_fired = stamp
            generate_and_send(send_email=True)
        time.sleep(20)
```
Remove the old `schedule.every().day.at(...)` usage and the now-unused `schedule` import if
nothing else needs it.

- [ ] **Step 5: Run to verify pass**

Run: `python -m pytest tests/test_schedule.py -q`
Expected: PASS (3 passed).

- [ ] **Step 6: Commit**

```bash
git add config.py main.py tests/test_schedule.py
git commit -m "feat: twice-weekly ET schedule (Wed 8PM, Sat 8AM)"
```

---

## Phase 6 — End-to-End Verification

### Task 6.1: Full suite + live report

- [ ] **Step 1: Run the whole test suite**

Run: `python -m pytest -q`
Expected: all green.

- [ ] **Step 2: Generate a real report**

Run: `python main.py --no-email`
Expected: `stock_report.pdf` builds. Manually verify against the spec checklist:
- Strategy page: mantra + the 6 mistake tickers
- S1: index rows on top, 3-month column, FRED note still accurate
- S2: 3-month column
- S3: industries (no market cap), 3-month column
- S4: three tables (>10% 5d / >20% 1mo / volume), company names, gradient shading
- S5: Date/Ticker/Company/Time/MktCap only, no sub-$5B names
- S6/S7/S8: present and populated (or graceful empty notice)
- Fonts consistent across all page breaks

- [ ] **Step 3: Verify a real email send (optional, needs creds)**

Run: `python main.py`
Expected: email arrives with the PDF attached.

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "test: full v1 verification pass"
```

---

## Self-Review Notes (spec coverage)

- Mantra + mistakes → Task 3.3 ✓
- 3-month column (S1/S2/S3) → Tasks 0.2, 4.1, 4.2, 4.3 ✓
- S1 index rows + FRED source note → Task 4.1 ✓
- S3 StockAnalysis + drop market cap → Task 4.3 ✓
- S4 split + names + gradient → Tasks 3.2, 4.4 ✓
- S5 ≥$5B + drop EPS/Rev + widen Time + next 5 days → Task 4.5 ✓
- Momentum / near-MA / abnormal-volume screens → Tasks 2.1, 4.6 ✓
- Full-market universe (free) → Task 1.1 ✓
- Font fix → Task 3.1 ✓
- Twice-weekly ET schedule → Task 5.2 ✓
- Reliability/fallback → universe `fetch_universe` returns None + guarded `main.py` ✓

**Open items deferred to the engineer (documented, not blocking):** exact "normal volume"
multiplier (defaulted 1.5×), multpl.com scrape parsing for Shiller PE / Buffett Indicator,
and whether to refine S3 industry period-changes via representative ETFs vs member averaging.
