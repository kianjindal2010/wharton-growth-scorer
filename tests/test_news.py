from datetime import date

import pytest

from growth_scorer.news import analyze_news, sentiment_score


def _item(title, published, provider="Reuters", summary=""):
    return {
        "content": {
            "title": title,
            "summary": summary,
            "pubDate": published,
            "provider": {"displayName": provider},
            "canonicalUrl": {"url": "https://example.com/story"},
        }
    }


def test_finance_sentiment_distinguishes_positive_and_negative_events():
    assert sentiment_score("Company beats estimates and raises guidance") > 0.5
    assert sentiment_score("Company misses estimates and cuts guidance amid investigation") < -0.5


def test_news_analysis_excludes_future_and_old_items_and_deduplicates():
    items = [
        _item("Acme beats estimates and raises guidance", "2026-09-18T10:00:00Z"),
        _item("Acme beats estimates and raises guidance", "2026-09-18T10:00:00Z"),
        _item("Acme faces data breach", "2026-09-25T10:00:00Z"),
        _item("Acme old story", "2026-05-01T10:00:00Z"),
    ]
    metrics, analyzed = analyze_news(items, date(2026, 9, 20), "ACME", "Acme Corporation")
    assert len(analyzed) == 1
    assert metrics["news_sentiment_30d"] > 0
    assert metrics["news_count_30d"] == 1


def test_news_source_quality_and_recency_affect_weight():
    items = [
        _item("Acme growth accelerates", "2026-09-19T10:00:00Z", "Reuters"),
        _item("Acme shares gain", "2026-08-25T10:00:00Z", "Unknown Blog"),
    ]
    _, analyzed = analyze_news(items, date(2026, 9, 20), "ACME", "Acme Corporation")
    assert analyzed[0]["combined_weight"] > analyzed[1]["combined_weight"]


def test_no_eligible_news_returns_missing_sentiment():
    metrics, analyzed = analyze_news([], date(2026, 9, 20), "ACME", "Acme Corporation")
    assert analyzed == []
    assert metrics["news_sentiment_30d"] is None
    assert metrics["news_sentiment_trend"] is None
