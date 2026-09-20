from __future__ import annotations

from importlib.resources import files
from typing import Any

import yaml


COUNTRIES: dict[str, dict[str, str | None]] = {
    "US": {"currency": "USD", "benchmark": "^GSPC", "fx": None, "fx_mode": "none"},
    "JP": {"currency": "JPY", "benchmark": "^N225", "fx": "JPY=X", "fx_mode": "divide"},
    "GB": {"currency": "GBP", "benchmark": "^FTSE", "fx": "GBPUSD=X", "fx_mode": "multiply"},
    "IN": {"currency": "INR", "benchmark": "^NSEI", "fx": "INR=X", "fx_mode": "divide"},
    "TW": {"currency": "TWD", "benchmark": "^TWII", "fx": "TWD=X", "fx_mode": "divide"},
    "KR": {"currency": "KRW", "benchmark": "^KS11", "fx": "KRW=X", "fx_mode": "divide"},
}


COMMON_NEWS_SPECS: list[dict[str, Any]] = [
    {"pillar": "News sentiment", "metric": "news_sentiment_30d", "label": "Weighted 30-day news sentiment", "weight": 3.0, "unit": "score", "anchors": [-0.35, 0.0, 0.35]},
    {"pillar": "News sentiment", "metric": "news_sentiment_trend", "label": "30-day versus 90-day sentiment trend", "weight": 1.0, "unit": "score", "anchors": [-0.25, 0.0, 0.25]},
    {"pillar": "News sentiment", "metric": "news_quality_coverage", "label": "Quality-adjusted news coverage", "weight": 1.0, "unit": "score", "anchors": [0.0, 0.50, 1.0]},
]


def load_scorecards() -> dict[str, Any]:
    path = files("growth_scorer").joinpath("scorecards.yaml")
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)
