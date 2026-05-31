import pandas as pd
from section3_industries import aggregate_industries


def _panel_from(series_by_ticker):
    n = max(len(v) for v in series_by_ticker.values())
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    cols, data = [], {}
    for tk, closes in series_by_ticker.items():
        cols += [(tk, "Close"), (tk, "Volume")]
        data[(tk, "Close")]  = pd.Series(closes, index=idx[-len(closes):]).reindex(idx)
        data[(tk, "Volume")] = pd.Series([1] * len(closes), index=idx[-len(closes):]).reindex(idx)
    return pd.DataFrame(data, index=idx, columns=pd.MultiIndex.from_tuples(cols))


def test_aggregate_groups_by_industry(sample_universe):
    # AAA & BBB are Software; give them history. CCC (Biotech) has none.
    panel = _panel_from({
        "AAA": [100.0] * 260 + [130.0],   # up
        "BBB": [50.0] * 260 + [40.0],     # down
    })
    rows = aggregate_industries(sample_universe, panel)
    inds = {r["industry"] for r in rows}
    assert "Software" in inds and "Biotechnology" in inds
    soft = next(r for r in rows if r["industry"] == "Software")
    # has PE and all seven period keys
    assert "pe" in soft
    for p in ("5d", "1mo", "3mo", "6mo", "1yr", "3yr", "5yr"):
        assert p in soft
    # Software 5d change is computed (not NA) since members have history
    assert soft["5d"] != "NA"
    # Biotechnology has no panel members -> period values NA
    bio = next(r for r in rows if r["industry"] == "Biotechnology")
    assert bio["5d"] == "NA"
