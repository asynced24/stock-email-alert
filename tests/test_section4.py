import pandas as pd
from section4_companies import split_movers, _volume_metrics


def test_split_movers_buckets_independent():
    enriched = [
        {"symbol": "AAA", "5d_raw": 12.0, "1mo_raw": 25.0, "spike": 0.8},  # 5d AND 1mo
        {"symbol": "BBB", "5d_raw": 3.0,  "1mo_raw": 25.0, "spike": 0.9},  # 1mo only
        {"symbol": "CCC", "5d_raw": 1.0,  "1mo_raw": 2.0,  "spike": 3.0},  # volume only
        {"symbol": "DDD", "5d_raw": 1.0,  "1mo_raw": 2.0,  "spike": 1.5},  # below 2x -> none
    ]
    five, month, vol = split_movers(enriched)
    assert [r["symbol"] for r in five]  == ["AAA"]
    assert set(r["symbol"] for r in month) == {"AAA", "BBB"}   # AAA qualifies for both
    assert [r["symbol"] for r in vol]   == ["CCC"]             # DDD (1.5x) below 2x


def test_volume_metrics():
    idx = pd.date_range("2026-01-01", periods=12, freq="B")
    # 10-day window avg ~1000; last 3 days include a 5000 spike on the middle day
    vals = [1000] * 9 + [1200, 5000, 1100]
    vols = pd.Series(vals, index=idx)
    avg2wk, spike, peak_vol, peak_date = _volume_metrics(vols)
    assert peak_vol == 5000
    assert peak_date == idx[10].strftime("%Y-%m-%d")   # the 5000 day
    assert spike > 2.0                                 # 5000 / ~1.6k avg


def test_volume_metrics_insufficient_data():
    vols = pd.Series([1, 2, 3])
    assert _volume_metrics(vols) == (None, None, None, None)
