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


DETAILED_PROFILES: dict[str, tuple[str, dict[str, float]]] = {
    "software_cloud": ("technology", {
        "gross_margin": 1.35, "fcf_margin": 1.25, "revenue_cagr_3y": 1.35,
        "latest_revenue_growth": 1.30, "rd_to_revenue": 1.30, "price_to_sales": 1.20,
        "current_ratio": 0.55, "cash_to_debt": 0.70,
    }),
    "hardware_telecom": ("technology", {
        "roic": 1.25, "fcf_margin": 1.20, "cash_conversion": 1.20,
        "net_debt_ebitda": 1.30, "interest_coverage": 1.25, "rd_to_revenue": 0.75,
        "price_to_sales": 0.70,
    }),
    "pharmaceuticals": ("healthcare", {
        "gross_margin": 1.20, "operating_margin": 1.20, "rd_to_revenue": 1.45,
        "rd_growth": 1.35, "fcf_margin": 1.20, "price_to_sales": 1.15,
        "current_ratio": 0.75,
    }),
    "medical_devices": ("healthcare", {
        "roic": 1.35, "gross_margin": 1.25, "cash_conversion": 1.20,
        "fcf_margin": 1.25, "rd_to_revenue": 0.85, "rd_growth": 0.70,
        "net_debt_ebitda": 1.15,
    }),
    "payments_fintech": ("financial_platform", {
        "operating_margin": 1.35, "fcf_margin": 1.35, "cash_conversion": 1.20,
        "revenue_cagr_3y": 1.35, "latest_revenue_growth": 1.30,
        "price_to_book": 0.55, "debt_to_equity": 0.80,
    }),
    "asset_management": ("financial_platform", {
        "roe": 1.35, "operating_margin": 1.25, "earnings_yield": 1.30,
        "shareholder_yield": 1.40, "revenue_cagr_3y": 0.85,
        "current_ratio": 0.55, "cash_to_debt": 0.75,
    }),
    "aerospace_defense": ("industrial", {
        "roic": 1.25, "operating_margin": 1.20, "revenue_cagr_3y": 1.25,
        "latest_revenue_growth": 1.25, "fcf_margin": 1.25,
        "inventory_days_change": 1.20, "asset_turnover": 0.80,
    }),
    "transportation_logistics": ("industrial", {
        "asset_turnover": 1.50, "operating_margin": 1.25, "cash_conversion": 1.20,
        "capex_to_sales": 1.35, "net_debt_ebitda": 1.25,
        "inventory_days_change": 0.45,
    }),
    "automotive": ("industrial", {
        "inventory_days_change": 1.50, "capex_to_sales": 1.40, "cash_to_debt": 1.25,
        "operating_margin": 1.30, "latest_revenue_growth": 1.20,
        "asset_turnover": 1.15,
    }),
    "capital_goods": ("industrial", {
        "roic": 1.35, "asset_turnover": 1.35, "inventory_days_change": 1.30,
        "cash_conversion": 1.25, "operating_margin_stability": 1.20,
        "capex_to_sales": 1.15,
    }),
    "consumer_staples": ("consumer", {
        "operating_margin_stability": 1.45, "cash_conversion": 1.30,
        "fcf_margin": 1.25, "shareholder_yield": 1.35, "inventory_turnover": 1.20,
        "revenue_cagr_3y": 0.75, "latest_revenue_growth": 0.75,
    }),
    "retail_discretionary": ("consumer", {
        "inventory_turnover": 1.50, "inventory_days_change": 1.45,
        "asset_turnover": 1.35, "latest_revenue_growth": 1.30,
        "gross_margin": 1.20, "price_to_sales": 1.20,
    }),
    "media_education": ("consumer", {
        "gross_margin": 1.35, "operating_margin": 1.30, "revenue_cagr_3y": 1.35,
        "latest_revenue_growth": 1.30, "price_to_sales": 1.25,
        "inventory_turnover": 0.0, "inventory_days_change": 0.0,
        "asset_turnover": 0.80,
    }),
    "oil_gas": ("energy_materials", {
        "fcf_margin": 1.35, "shareholder_yield": 1.55, "net_debt_ebitda": 1.35,
        "capex_to_sales": 1.35, "incremental_roic": 1.20,
        "revenue_cagr_3y": 0.70,
    }),
    "utilities_renewables": ("energy_materials", {
        "interest_coverage": 1.55, "net_debt_ebitda": 1.45, "capex_to_sales": 1.40,
        "cash_conversion": 1.25, "fcf_margin": 1.20,
        "revenue_acceleration": 0.65, "incremental_roic": 0.75,
    }),
    "materials_mining": ("energy_materials", {
        "roic": 1.35, "revenue_acceleration": 1.40, "incremental_roic": 1.40,
        "cash_to_debt": 1.25, "capex_to_sales": 1.25,
        "shareholder_yield": 1.25,
    }),
}


AUTOMATED_SPECIALISTS: dict[str, list[tuple[str, str, float]]] = {
    "bank": [
        ("Profitability", "roe", 12), ("Profitability", "roa", 10),
        ("Profitability", "net_margin", 8), ("Growth", "tangible_book_cagr_3y", 8),
        ("Growth", "revenue_cagr_3y", 6), ("Growth", "eps_cagr_3y", 6),
        ("Growth", "asset_growth", 5), ("Valuation", "earnings_yield", 8),
        ("Valuation", "price_to_tangible_book", 7), ("Valuation", "dividend_yield", 5),
        ("Balance-sheet resilience", "equity_to_assets", 10),
        ("Market risk", "usd_volatility", 4), ("Market risk", "max_drawdown", 4),
        ("Market risk", "downside_beta", 2), ("Momentum", "relative_return_12m", 3),
        ("Momentum", "relative_return_6m", 2),
    ],
    "insurer": [
        ("Profitability", "roe", 10), ("Profitability", "net_margin", 8),
        ("Profitability", "investment_income_stability", 7),
        ("Growth", "book_value_cagr_3y", 8), ("Growth", "premium_growth", 5),
        ("Growth", "revenue_cagr_3y", 4), ("Growth", "eps_cagr_3y", 3),
        ("Valuation", "earnings_yield", 8), ("Valuation", "price_to_book", 8),
        ("Valuation", "dividend_yield", 4),
        ("Balance-sheet resilience", "equity_to_assets", 12),
        ("Balance-sheet resilience", "debt_to_equity", 8),
        ("Market risk", "usd_volatility", 4), ("Market risk", "max_drawdown", 4),
        ("Market risk", "downside_beta", 2), ("Momentum", "relative_return_12m", 3),
        ("Momentum", "relative_return_6m", 2),
    ],
    "memory_semiconductor": [
        ("Memory cycle", "latest_revenue_growth", 7), ("Memory cycle", "revenue_acceleration", 6),
        ("Memory cycle", "gross_margin_trend", 6), ("Memory cycle", "inventory_days_change", 6),
        ("Quality", "gross_margin", 6), ("Quality", "operating_margin", 5),
        ("Quality", "fcf_margin", 5), ("Quality", "cash_conversion", 4),
        ("Growth", "revenue_cagr_3y", 6), ("Growth", "eps_cagr_3y", 5),
        ("Growth", "fcf_cagr_3y", 4), ("Valuation", "price_to_sales", 4),
        ("Valuation", "fcf_yield", 4), ("Valuation", "ebit_ev", 4),
        ("Valuation", "earnings_yield", 3), ("Financial strength", "net_debt_ebitda", 4),
        ("Financial strength", "cash_to_debt", 3), ("Financial strength", "current_ratio", 3),
        ("Innovation", "rd_to_revenue", 3), ("Innovation", "revenue_growth_to_capex", 2),
        ("Momentum", "relative_return_12m", 3), ("Momentum", "relative_return_6m", 2),
        ("Market risk", "usd_volatility", 3), ("Market risk", "max_drawdown", 2),
    ],
}


EXTRA_METRIC_SPECS: dict[str, dict[str, Any]] = {
    "net_margin": {"label": "Net margin", "unit": "%", "anchors": [-0.05, 0.10, 0.25]},
    "equity_to_assets": {"label": "Equity / assets", "unit": "%", "anchors": [0.03, 0.10, 0.20]},
    "asset_growth": {"label": "Latest asset growth", "unit": "%", "anchors": [-0.05, 0.05, 0.15]},
}


def _automated_specialist_cards(cards: dict[str, Any]) -> None:
    catalog = {spec["metric"]: spec for specs in cards.values() for spec in specs}
    for name, definitions in AUTOMATED_SPECIALISTS.items():
        generated: list[dict[str, Any]] = []
        for pillar, metric, weight in definitions:
            source = EXTRA_METRIC_SPECS.get(metric) or catalog[metric]
            generated.append({
                "pillar": pillar, "metric": metric, "label": source["label"],
                "weight": float(weight), "unit": source["unit"], "anchors": list(source["anchors"]),
            })
        cards[name] = generated


def _detailed_cards(cards: dict[str, Any]) -> None:
    for name, (base, multipliers) in DETAILED_PROFILES.items():
        generated = []
        for original in cards[base]:
            multiplier = multipliers.get(original["metric"], 1.0)
            if multiplier <= 0:
                continue
            spec = dict(original)
            spec["anchors"] = list(original["anchors"])
            spec["weight"] = float(original["weight"]) * multiplier
            generated.append(spec)
        total = sum(spec["weight"] for spec in generated)
        for spec in generated:
            spec["weight"] = round(spec["weight"] * 100.0 / total, 8)
        generated[-1]["weight"] = round(
            generated[-1]["weight"] + 100.0 - sum(spec["weight"] for spec in generated), 8
        )
        cards[name] = generated


def load_scorecards() -> dict[str, Any]:
    path = files("growth_scorer").joinpath("scorecards.yaml")
    with path.open("r", encoding="utf-8") as handle:
        cards = yaml.safe_load(handle)
    _automated_specialist_cards(cards)
    _detailed_cards(cards)
    return cards
