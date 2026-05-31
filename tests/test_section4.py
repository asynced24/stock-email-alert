from section4_companies import split_movers


def test_split_movers_buckets():
    enriched = [
        {"symbol": "AAA", "company": "Alpha", "5d_raw": 12.0, "1mo_raw": 5.0,  "vol_ratio": 0.8},
        {"symbol": "BBB", "company": "Beta",  "5d_raw": 3.0,  "1mo_raw": 25.0, "vol_ratio": 0.9},
        {"symbol": "CCC", "company": "Gamma", "5d_raw": 1.0,  "1mo_raw": 2.0,  "vol_ratio": 3.0},
        {"symbol": "DDD", "company": "Delta", "5d_raw": 1.0,  "1mo_raw": 2.0,  "vol_ratio": 1.2},
    ]
    five, month, vol = split_movers(enriched)
    assert [r["symbol"] for r in five]  == ["AAA"]
    assert [r["symbol"] for r in month] == ["BBB"]
    assert [r["symbol"] for r in vol]   == ["CCC"]   # DDD (1.2x) below 1.5x threshold -> excluded
