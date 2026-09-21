from __future__ import annotations

import re


COUNTRY_CODES = {"US", "JP", "GB", "IN", "TW", "KR"}
SCORECARDS = {
    "auto", "general", "technology", "healthcare", "financial_platform", "industrial",
    "consumer", "energy_materials", "bank", "insurer", "biotech", "semiconductor",
    "memory_semiconductor",
}


def safe_name(ticker: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", ticker)


def validate_ticker_country(ticker: str, country: str) -> None:
    ticker = ticker.upper()
    valid = {
        "US": lambda value: not value.endswith((".T", ".L", ".NS", ".BO", ".TW", ".TWO", ".KS", ".KQ")),
        "JP": lambda value: value.endswith(".T"),
        "GB": lambda value: value.endswith(".L"),
        "IN": lambda value: value.endswith((".NS", ".BO")),
        "TW": lambda value: value.endswith((".TW", ".TWO")),
        "KR": lambda value: value.endswith((".KS", ".KQ")),
    }
    examples = {
        "US": "MSFT", "JP": "7203.T", "GB": "AZN.L", "IN": "TCS.NS",
        "TW": "2330.TW", "KR": "000660.KS",
    }
    if country not in valid or not valid[country](ticker):
        raise ValueError(
            f"Ticker {ticker} does not match country {country}. "
            f"Example: {examples.get(country, 'MSFT')}"
        )
