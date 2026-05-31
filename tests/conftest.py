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
