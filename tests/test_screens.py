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
    # AAA: 210 closes flat at 100 -> 50d MA == 100, price 100 -> within 5%
    panel = _panel_from({"AAA": ([100.0] * 210, [1] * 210)})
    rows = screens.near_ma(sample_universe, panel, min_cap=2e9, window=50, pct=5.0)
    assert any(r["symbol"] == "AAA" for r in rows)
    assert rows[0]["ma"] == "100.00"   # MA value reported


def test_near_ma_200_window(sample_universe):
    panel = _panel_from({"AAA": ([100.0] * 210, [1] * 210)})
    rows = screens.near_ma(sample_universe, panel, min_cap=2e9, window=200, pct=5.0)
    assert any(r["symbol"] == "AAA" for r in rows)


def test_near_ma_excludes_small_cap(sample_universe):
    # CCC market cap is 1e9 < 2e9 floor; even if near MA it must be excluded
    panel = _panel_from({"CCC": ([10.0] * 210, [1] * 210)})
    rows = screens.near_ma(sample_universe, panel, min_cap=2e9, window=50, pct=5.0)
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
