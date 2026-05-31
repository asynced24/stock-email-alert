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


def test_filter_handles_no_universe():
    rows = [{"symbol": "AAA", "company": "Alpha", "time": "amc"}]
    # When universe is None, do not crash; return rows unchanged (caller decides)
    assert filter_by_market_cap_5b(rows, None, min_cap=5e9) == rows
