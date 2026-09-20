import pytest

from growth_scorer.backtest import _summary


def test_backtest_summary_excludes_insufficient_data():
    records = [
        {"score": 80, "verdict": "Buy Candidate", "usd_return": 0.20, "usd_excess_return": 0.10},
        {"score": 65, "verdict": "Watch", "usd_return": 0.10, "usd_excess_return": 0.02},
        {"score": 50, "verdict": "Reject", "usd_return": -0.10, "usd_excess_return": -0.15},
        {"score": 90, "verdict": "Insufficient Data", "usd_return": 0.80, "usd_excess_return": 0.70},
    ]
    summary = _summary(records)
    assert summary["companies"] == 4
    assert summary["actionable_companies"] == 3
    assert summary["insufficient_data_companies"] == 1
    assert summary["buy_mean_usd_return"] == pytest.approx(0.20)
    assert summary["directional_hit_rate"] == 1.0
