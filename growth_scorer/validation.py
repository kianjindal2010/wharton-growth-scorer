from __future__ import annotations

import re


COUNTRY_CODES = {"US", "JP", "GB", "IN", "TW", "KR"}
DEFAULT_MARKET_SUFFIXES = {
    "US": "", "JP": ".T", "GB": ".L", "IN": ".NS", "TW": ".TW", "KR": ".KS",
}
VALID_MARKET_SUFFIXES = {
    "US": (), "JP": (".T",), "GB": (".L",), "IN": (".NS", ".BO"),
    "TW": (".TW", ".TWO"), "KR": (".KS", ".KQ"),
}
KNOWN_INTERNATIONAL_SUFFIXES = tuple(
    suffix for suffixes in VALID_MARKET_SUFFIXES.values() for suffix in suffixes
)
SCORECARDS = {
    "auto", "general", "technology", "healthcare", "financial_platform", "industrial",
    "consumer", "energy_materials", "bank", "insurer", "biotech", "semiconductor",
    "memory_semiconductor",
    "software_cloud", "hardware_telecom", "pharmaceuticals", "medical_devices",
    "payments_fintech", "asset_management", "aerospace_defense", "transportation_logistics",
    "automotive", "capital_goods", "consumer_staples", "retail_discretionary",
    "media_education", "oil_gas", "utilities_renewables", "materials_mining",
}


def safe_name(ticker: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", ticker)


def normalize_ticker_for_country(ticker: str, country: str) -> str:
    """Add the default Yahoo market suffix when the analyst enters a bare ticker."""
    ticker = ticker.strip().upper()
    country = country.strip().upper()
    if not ticker:
        raise ValueError("Ticker cannot be blank")
    if country not in COUNTRY_CODES:
        raise ValueError(f"Unsupported country code: {country}")
    allowed = VALID_MARKET_SUFFIXES[country]
    if any(ticker.endswith(suffix) for suffix in allowed):
        return ticker
    if any(ticker.endswith(suffix) for suffix in KNOWN_INTERNATIONAL_SUFFIXES):
        raise ValueError(f"Ticker {ticker} already has a suffix for a different market")
    return ticker + DEFAULT_MARKET_SUFFIXES[country]


def infer_country_from_ticker(ticker: str) -> str:
    """Infer a supported market from an already formatted Yahoo Finance ticker."""
    ticker = ticker.strip().upper()
    if not ticker:
        raise ValueError("Ticker cannot be blank")
    suffix_markets = (
        ((".TWO", ".TW"), "TW"),
        ((".NS", ".BO"), "IN"),
        ((".KS", ".KQ"), "KR"),
        ((".T",), "JP"),
        ((".L",), "GB"),
    )
    for suffixes, country in suffix_markets:
        if ticker.endswith(suffixes):
            return country
    return "US"


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
