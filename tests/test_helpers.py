import pandas as pd
from helpers import PERIODS, PERIOD_LABELS, period_dates, pct_change_over, pct_change_ytd


def test_pct_change_ytd_uses_prior_year_close():
    idx = pd.date_range("2024-12-02", periods=40, freq="B")
    # 2024 closes = 100, 2025 closes = 80  ->  YTD from last 2024 close (100) is -20%
    vals = [100.0 if d.year == 2024 else 80.0 for d in idx]
    s = pd.Series(vals, index=idx)
    assert pct_change_ytd(s) == -20.0


def test_pct_change_ytd_no_prior_year_returns_na():
    idx = pd.date_range("2025-02-01", periods=10, freq="B")   # no previous-year close
    s = pd.Series([100.0] * 10, index=idx)
    assert pct_change_ytd(s) == "NA"


def test_3mo_period_registered():
    assert "3mo" in PERIODS
    # 3mo sits between 1mo and 6mo
    assert PERIODS.index("3mo") == PERIODS.index("1mo") + 1
    assert PERIODS.index("3mo") < PERIODS.index("6mo")
    assert "3mo" in PERIOD_LABELS


def test_period_dates_has_3mo():
    d = period_dates()
    assert "3mo" in d
    # ~92 days back
    delta_days = (d["current"] - d["3mo"]).days
    assert 88 <= delta_days <= 100


def test_pct_change_over_basic():
    idx = pd.date_range("2025-01-01", periods=30, freq="B")
    s = pd.Series([100.0] * 29 + [110.0], index=idx)
    # most recent vs 5 business days back (both 100 except last) -> +10%
    assert round(pct_change_over(s, 5), 2) == 10.0


def test_pct_change_over_insufficient_data_returns_na():
    s = pd.Series([100.0], index=pd.date_range("2025-01-01", periods=1, freq="B"))
    assert pct_change_over(s, 50) == "NA"
