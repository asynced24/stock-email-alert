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
