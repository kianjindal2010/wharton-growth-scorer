from datetime import date

import numpy as np
import pandas as pd
import pytest

from growth_scorer.data import _adjusted_close, _clean_frame, _to_usd
from growth_scorer.config import COUNTRIES


def test_future_statement_period_is_excluded():
    frame = pd.DataFrame(
        {pd.Timestamp("2025-12-31"): [1], pd.Timestamp("2026-12-31"): [2]},
        index=["Total Revenue"],
    )
    cleaned = _clean_frame(frame, date(2026, 9, 20))
    assert list(cleaned.columns) == [pd.Timestamp("2025-12-31")]


@pytest.mark.parametrize(
    "mode,rate,expected",
    [
        ("divide", 150.0, 1.0),  # JPY
        ("divide", 83.0, 150 / 83),  # INR
        ("divide", 32.0, 150 / 32),  # TWD
        ("multiply", 1.25, 187.5),  # GBP
    ],
)
def test_currency_conversion_modes(mode, rate, expected):
    index = pd.date_range("2026-01-01", periods=2)
    local = pd.Series([150.0, 150.0], index=index)
    fx = pd.Series([rate, rate], index=index)
    assert _to_usd(local, fx, mode).iloc[-1] == pytest.approx(expected)


def test_adjusted_prices_absorb_stock_split():
    frame = pd.DataFrame(
        {"Close": [100.0, 50.0], "Adj Close": [50.0, 50.0], "Stock Splits": [0.0, 2.0]},
        index=pd.date_range("2026-01-01", periods=2),
    )
    returns = _adjusted_close(frame).pct_change().dropna()
    assert returns.iloc[0] == 0


def test_short_history_does_not_crash():
    frame = pd.DataFrame({"Adj Close": [100.0]}, index=[pd.Timestamp("2026-01-01")])
    assert len(_adjusted_close(frame)) == 1


def test_korean_market_configuration_uses_krw_and_kospi():
    assert COUNTRIES["KR"]["currency"] == "KRW"
    assert COUNTRIES["KR"]["benchmark"] == "^KS11"
    assert COUNTRIES["KR"]["fx_mode"] == "divide"
