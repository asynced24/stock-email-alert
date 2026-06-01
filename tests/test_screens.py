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


# 5 years ago = 50, recent 600 sessions flat at 100 -> +100% over 5yr, price == MA.
_NEAR_MA_SERIES = [50.0] * 700 + [100.0] * 601   # len 1301 (>= 1261 for a 5yr change)


def test_near_ma_flags_price_within_5pct_and_5yr_gain(sample_universe):
    panel = _panel_from({"AAA": (_NEAR_MA_SERIES, [1] * len(_NEAR_MA_SERIES))})
    rows = screens.near_ma(sample_universe, panel, min_cap=2e9, window=50, pct=5.0)
    assert any(r["symbol"] == "AAA" for r in rows)
    r = next(r for r in rows if r["symbol"] == "AAA")
    assert r["ma"] == "100.00"          # MA value reported
    assert "6mo" in r and "5yr" in r    # new columns present
    assert r["5yr"].startswith("+")     # up over 5 years


def test_near_ma_200_window(sample_universe):
    panel = _panel_from({"AAA": (_NEAR_MA_SERIES, [1] * len(_NEAR_MA_SERIES))})
    rows = screens.near_ma(sample_universe, panel, min_cap=2e9, window=200, pct=5.0)
    assert any(r["symbol"] == "AAA" for r in rows)


def test_near_ma_excludes_weak_5yr(sample_universe):
    # Flat series -> ~0% over 5 years -> fails the >25% 5yr filter -> excluded.
    flat = [100.0] * 1301
    panel = _panel_from({"AAA": (flat, [1] * 1301)})
    rows = screens.near_ma(sample_universe, panel, min_cap=2e9, window=50, pct=5.0)
    assert all(r["symbol"] != "AAA" for r in rows)


def test_near_ma_excludes_small_cap(sample_universe):
    # CCC market cap is 1e9 < 2e9 floor; even if near MA it must be excluded
    panel = _panel_from({"CCC": (_NEAR_MA_SERIES, [1] * len(_NEAR_MA_SERIES))})
    rows = screens.near_ma(sample_universe, panel, min_cap=2e9, window=50, pct=5.0)
    assert all(r["symbol"] != "CCC" for r in rows)


def test_near_ma_works_on_realistic_5y_panel_length(sample_universe):
    # Regression: a real yfinance "5y" fetch returns ~1255 trading days, just UNDER
    # the 1260-session 5yr lookback. Before the clamp this blanked Section 9 (0 rows).
    series = [40.0] * 655 + [100.0] * 600   # len 1255; 5y-ago ~40 -> +150%; price == 50d MA
    assert len(series) == 1255
    panel = _panel_from({"AAA": (series, [1] * len(series))})
    rows = screens.near_ma(sample_universe, panel, min_cap=2e9, window=50)
    assert any(r["symbol"] == "AAA" for r in rows)        # must still screen
    assert next(r for r in rows if r["symbol"] == "AAA")["5yr"].startswith("+")


def test_momentum_pullback(sample_universe):
    # Needs a full year (>=253 sessions). yr-ago ~50, recent peak 120, now 100.
    closes = [50.0] * 200 + [120.0] * 59 + [100.0]   # len 260
    panel = _panel_from({"AAA": (closes, [1] * len(closes))})
    rows = screens.momentum_pullback(sample_universe, panel, min_cap=2e9)
    assert any(r["symbol"] == "AAA" for r in rows)


def test_momentum_pullback_skips_short_history(sample_universe):
    # Only ~200 sessions -> cannot establish a true 1-year trend -> excluded.
    closes = [50.0] * 150 + [120.0] * 49 + [100.0]   # len 200 < 253
    panel = _panel_from({"AAA": (closes, [1] * len(closes))})
    rows = screens.momentum_pullback(sample_universe, panel, min_cap=2e9)
    assert all(r["symbol"] != "AAA" for r in rows)


def test_reversal_bounce(sample_universe):
    # down >20% over the year but up >10% over the last 5 sessions (full year history).
    closes = [100.0] * 200 + [60.0] * 59 + [72.0]   # len 260; yr -28%, 5d +20%
    panel = _panel_from({"AAA": (closes, [1] * len(closes))})
    rows = screens.reversal_bounce(sample_universe, panel, min_cap=2e9)
    assert any(r["symbol"] == "AAA" for r in rows)


def _long_pullback_series():
    vals = [80.0] * 1260
    vals[0] = 50.0            # ~5yr ago
    vals[1260 - 253] = 70.0   # ~1yr ago
    vals[1260 - 64] = 110.0   # ~3mo ago
    vals[-1] = 95.0           # now
    return vals


def test_long_term_pullback_flags(sample_universe):
    panel = _panel_from({"AAA": (_long_pullback_series(), [1] * 1260)})
    rows = screens.long_term_pullback(sample_universe, panel, min_cap=2e9,
                                      has_options=lambda s: True)
    assert any(r["symbol"] == "AAA" for r in rows)


def test_long_term_pullback_requires_options(sample_universe):
    panel = _panel_from({"AAA": (_long_pullback_series(), [1] * 1260)})
    rows = screens.long_term_pullback(sample_universe, panel, min_cap=2e9,
                                      has_options=lambda s: False)
    assert all(r["symbol"] != "AAA" for r in rows)
