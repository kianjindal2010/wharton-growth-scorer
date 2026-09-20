from __future__ import annotations

import math
import re
from datetime import date, datetime, timezone
from typing import Any

import yfinance as yf


POSITIVE_PHRASES = {
    "beats estimates": 1.0, "beat estimates": 1.0, "raises guidance": 1.0,
    "raised guidance": 1.0, "record revenue": 0.8, "record profit": 0.9,
    "earnings surprise": 0.7, "wins contract": 0.7, "regulatory approval": 1.0,
    "share buyback": 0.5, "dividend increase": 0.5, "upgraded to": 0.6,
}
NEGATIVE_PHRASES = {
    "misses estimates": -1.0, "missed estimates": -1.0, "cuts guidance": -1.0,
    "cut guidance": -1.0, "profit warning": -1.0, "regulatory investigation": -0.9,
    "data breach": -0.9, "credit downgrade": -0.8, "dividend cut": -0.8,
    "going concern": -1.0, "chapter 11": -1.0, "secondary offering": -0.6,
}
TOKEN_WEIGHTS = {
    "beat": 0.45, "beats": 0.45, "growth": 0.25, "surge": 0.45, "surges": 0.45,
    "record": 0.35, "strong": 0.30, "approval": 0.45, "approved": 0.45,
    "upgrade": 0.35, "upgraded": 0.35, "outperform": 0.35, "profit": 0.18,
    "expands": 0.22, "launch": 0.15, "partnership": 0.15, "contract": 0.18,
    "miss": -0.45, "misses": -0.45, "decline": -0.25, "falls": -0.30,
    "weak": -0.30, "downgrade": -0.35, "downgraded": -0.35, "underperform": -0.35,
    "investigation": -0.45, "lawsuit": -0.35, "recall": -0.50, "breach": -0.50,
    "warning": -0.40, "loss": -0.22, "layoffs": -0.25, "fraud": -0.80,
    "bankruptcy": -1.0, "dilution": -0.45, "offering": -0.15,
}
NEGATIONS = {"not", "no", "never", "without", "fails", "failed"}
INTENSIFIERS = {"very": 1.25, "sharply": 1.35, "significantly": 1.25, "slightly": 0.70}
HIGH_QUALITY = ("reuters", "associated press", "bloomberg", "financial times", "wall street journal")
MEDIUM_QUALITY = ("cnbc", "marketwatch", "barron's", "fortune", "business insider", "the motley fool")


def _content(item: dict[str, Any]) -> dict[str, Any]:
    nested = item.get("content")
    return nested if isinstance(nested, dict) else item


def _published(content: dict[str, Any]) -> datetime | None:
    raw = content.get("pubDate") or content.get("displayTime") or content.get("providerPublishTime")
    if isinstance(raw, (int, float)):
        return datetime.fromtimestamp(raw, tz=timezone.utc)
    if isinstance(raw, str):
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _provider(content: dict[str, Any]) -> str:
    provider = content.get("provider")
    if isinstance(provider, dict):
        return str(provider.get("displayName") or "")
    return str(provider or content.get("publisher") or "")


def _url(content: dict[str, Any]) -> str | None:
    for field in ("canonicalUrl", "clickThroughUrl"):
        value = content.get(field)
        if isinstance(value, dict) and value.get("url"):
            return str(value["url"])
    value = content.get("link")
    return str(value) if value else None


def sentiment_score(text: str) -> float:
    clean = re.sub(r"\s+", " ", text.lower()).strip()
    total = sum(weight for phrase, weight in {**POSITIVE_PHRASES, **NEGATIVE_PHRASES}.items() if phrase in clean)
    tokens = re.findall(r"[a-z']+", clean)
    for index, token in enumerate(tokens):
        weight = TOKEN_WEIGHTS.get(token)
        if weight is None:
            continue
        previous = tokens[max(0, index - 2):index]
        if any(word in NEGATIONS for word in previous):
            weight *= -0.8
        if index and tokens[index - 1] in INTENSIFIERS:
            weight *= INTENSIFIERS[tokens[index - 1]]
        total += weight
    return float(math.tanh(total / 2.5))


def _source_quality(provider: str) -> float:
    name = provider.lower()
    if any(source in name for source in HIGH_QUALITY):
        return 1.0
    if any(source in name for source in MEDIUM_QUALITY):
        return 0.82
    return 0.65


def analyze_news(items: list[dict[str, Any]], as_of: date, ticker: str, company_name: str | None = None) -> tuple[dict[str, float | None], list[dict[str, Any]]]:
    as_of_dt = datetime.combine(as_of, datetime.max.time(), tzinfo=timezone.utc)
    company_tokens = {
        token for token in re.findall(r"[a-z0-9]+", (company_name or "").lower())
        if len(token) >= 4 and token not in {"corporation", "company", "limited", "holdings"}
    }
    ticker_token = ticker.split(".")[0].lower()
    seen: set[str] = set()
    analyzed: list[dict[str, Any]] = []
    for raw_item in items:
        content = _content(raw_item)
        published = _published(content)
        if published is None:
            continue
        published = published.astimezone(timezone.utc)
        age_days = (as_of_dt - published).total_seconds() / 86400
        if age_days < 0 or age_days > 90:
            continue
        title = str(content.get("title") or "").strip()
        summary = str(content.get("summary") or content.get("description") or "").strip()
        normalized = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()
        if not title or normalized in seen:
            continue
        seen.add(normalized)
        searchable = f"{title} {summary}".lower()
        title_lower = title.lower()
        relevance = 0.0
        if ticker_token and re.search(rf"\b{re.escape(ticker_token)}\b", title_lower):
            relevance = 1.0
        elif any(re.search(rf"\b{re.escape(token)}\b", title_lower) for token in company_tokens):
            relevance = 1.0
        elif any(re.search(rf"\b{re.escape(token)}\b", searchable) for token in company_tokens):
            relevance = 0.75
        if relevance == 0.0:
            continue
        provider = _provider(content)
        quality = _source_quality(provider)
        recency = math.exp(-math.log(2) * age_days / 14.0)
        polarity = sentiment_score(f"{title}. {summary}")
        weight = relevance * quality * recency
        analyzed.append({
            "published_at": published.isoformat(), "title": title, "summary": summary,
            "provider": provider, "url": _url(content), "age_days": round(age_days, 2),
            "sentiment": round(polarity, 4), "relevance": round(relevance, 4),
            "source_quality": round(quality, 4), "recency_weight": round(recency, 4),
            "combined_weight": round(weight, 4),
        })

    def weighted(window: int) -> float | None:
        selected = [item for item in analyzed if item["age_days"] <= window]
        denominator = sum(item["combined_weight"] for item in selected)
        if denominator == 0:
            return None
        return sum(item["sentiment"] * item["combined_weight"] for item in selected) / denominator

    sentiment_30 = weighted(30)
    sentiment_90 = weighted(90)
    coverage_weight = sum(item["combined_weight"] for item in analyzed if item["age_days"] <= 30)
    metrics = {
        "news_sentiment_30d": sentiment_30,
        "news_sentiment_trend": None if sentiment_30 is None or sentiment_90 is None else sentiment_30 - sentiment_90,
        "news_quality_coverage": min(coverage_weight / 4.0, 1.0) if analyzed else None,
        "news_count_30d": float(sum(item["age_days"] <= 30 for item in analyzed)),
        "news_count_90d": float(len(analyzed)),
    }
    return metrics, analyzed


def fetch_news_metrics(ticker: yf.Ticker, as_of: date, ticker_symbol: str, company_name: str | None = None) -> tuple[dict[str, float | None], list[dict[str, Any]], list[str]]:
    try:
        items = ticker.news or []
    except Exception as exc:
        return {}, [], [f"Yahoo Finance news retrieval failed: {exc}"]
    metrics, analyzed = analyze_news(items, as_of, ticker_symbol, company_name)
    warnings: list[str] = []
    if not analyzed:
        warnings.append("No Yahoo Finance news with a publication time on or before the as-of date was available; news factors remain neutral")
    return metrics, analyzed, warnings
