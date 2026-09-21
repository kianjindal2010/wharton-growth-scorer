from __future__ import annotations

from datetime import date, datetime

import pytest

from growth_scorer.config import COMMON_NEWS_SPECS, load_scorecards
from growth_scorer.models import InputSnapshot


def metrics_at(scorecard: str, anchor_index: int = 1) -> dict[str, float]:
    metrics = {
        spec["metric"]: float(spec["anchors"][anchor_index])
        for spec in load_scorecards()[scorecard]
    }
    metrics.update({
        spec["metric"]: float(spec["anchors"][anchor_index])
        for spec in COMMON_NEWS_SPECS
    })
    metrics.update({"book_equity": 100.0, "operating_income": 10.0, "free_cash_flow": 10.0})
    return metrics


@pytest.fixture
def snapshot_factory():
    def factory(scorecard: str = "general", anchor_index: int = 1, **changes):
        industries = {
            "general": "Conglomerates",
            "bank": "Banks - Diversified",
            "insurer": "Insurance - Property & Casualty",
            "biotech": "Biotechnology",
            "semiconductor": "Semiconductors",
            "memory_semiconductor": "Semiconductors - Memory Chips",
            "technology": "Software - Infrastructure",
            "healthcare": "Medical Devices",
            "financial_platform": "Capital Markets",
            "industrial": "Specialty Industrial Machinery",
            "consumer": "Household & Personal Products",
            "energy_materials": "Oil & Gas Integrated",
        }
        sectors = {
            "general": "Other",
            "bank": "Financial Services",
            "insurer": "Financial Services",
            "biotech": "Healthcare",
            "semiconductor": "Technology",
            "memory_semiconductor": "Technology",
            "technology": "Technology",
            "healthcare": "Healthcare",
            "financial_platform": "Financial Services",
            "industrial": "Industrials",
            "consumer": "Consumer Defensive",
            "energy_materials": "Energy",
        }
        metrics = metrics_at(scorecard, anchor_index)
        if scorecard == "biotech":
            metrics["operating_income"] = -10.0
            metrics["free_cash_flow"] = -20.0
        metrics.update(changes.pop("metric_changes", {}))
        return InputSnapshot(
            ticker=changes.pop("ticker", "TEST"),
            country=changes.pop("country", "US"),
            as_of=changes.pop("as_of", date(2026, 9, 20)),
            retrieved_at=changes.pop("retrieved_at", datetime(2026, 9, 20, 12, 0, 0)),
            company_name="Synthetic Company",
            sector=changes.pop("sector", sectors.get(scorecard, "Other")),
            industry=changes.pop("industry", industries.get(scorecard, "Conglomerates")),
            currency="USD",
            metrics=metrics,
            metric_sources={key: "synthetic" for key in metrics},
            last_price_date=changes.pop("last_price_date", date(2026, 9, 18)),
            latest_financial_date=changes.pop("latest_financial_date", date(2026, 6, 30)),
            **changes,
        )

    return factory
