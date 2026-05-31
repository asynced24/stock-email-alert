import pandas as pd
from section1_macro import _index_rows_from_history


def test_index_rows_have_all_periods_and_label():
    idx = pd.date_range("2024-01-01", periods=400, freq="B")
    closes = pd.Series([100 + i for i in range(400)], index=idx)
    rows = _index_rows_from_history({"^GSPC": ("S&P 500", "Index")},
                                    lambda t: closes)
    r = rows[0]
    assert r["metric"].startswith("S&P 500")
    for p in ("5d", "1mo", "3mo", "6mo", "1yr", "5yr"):
        assert p in r
    # rising series -> 1mo change positive
    assert r["1mo"].startswith("+")


def test_index_rows_handle_missing_series():
    rows = _index_rows_from_history({"^RUT": ("Russell 2000", "Index")},
                                    lambda t: None)
    assert rows[0]["current"] == "NA"
    assert rows[0]["5d"] == "NA"
