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
    idx = pd.date_range("2026-01-01", periods=15, freq="B")
    # baseline (10 sessions before the last 3) is flat at 1000; last 3 include a 5000 spike
    vals = [1000] * 12 + [1200, 5000, 1100]
    vols = pd.Series(vals, index=idx)
    avg2wk, spike, peak_vol, peak_date = _volume_metrics(vols)
    assert avg2wk == 1000                              # baseline excludes the spike window
    assert peak_vol == 5000
    assert peak_date == idx[13].strftime("%Y-%m-%d")   # the 5000 day
    assert spike == 5.0                                # 5000 / 1000, not diluted by the spike


def test_volume_metrics_insufficient_data():
    vols = pd.Series([1, 2, 3])
    assert _volume_metrics(vols) == (None, None, None, None)
