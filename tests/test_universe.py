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
