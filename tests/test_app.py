from datetime import date
from pathlib import Path

import pytest

from growth_scorer.app import parse_as_of, parse_batch_items
from growth_scorer.validation import infer_country_from_ticker, normalize_ticker_for_country


def test_parse_as_of_accepts_iso_date():
    assert parse_as_of("2026-09-20") == date(2026, 9, 20)


def test_parse_as_of_rejects_invalid_date():
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        parse_as_of("20/09/2026")


def test_parse_batch_items_normalizes_and_forces_automatic_scorecard():
    items = parse_batch_items([
        {"ticker": "msft", "country": "us"},
        {"ticker": "2330.tw", "country": "tw"},
    ])
    assert items[0].ticker == "MSFT"
    assert items[0].scorecard == "auto"
    assert items[1].country == "TW"


@pytest.mark.parametrize(
    "ticker,country,expected",
    [
        ("MSFT", "US", "MSFT"),
        ("7203", "JP", "7203.T"),
        ("AZN", "GB", "AZN.L"),
        ("RELIANCE", "IN", "RELIANCE.NS"),
        ("2330", "TW", "2330.TW"),
        ("000660", "KR", "000660.KS"),
        ("RELIANCE.NS", "IN", "RELIANCE.NS"),
        ("500325.BO", "IN", "500325.BO"),
    ],
)
def test_market_suffix_is_added_automatically(ticker, country, expected):
    assert normalize_ticker_for_country(ticker, country) == expected


def test_wrong_existing_market_suffix_is_rejected():
    with pytest.raises(ValueError, match="different market"):
        normalize_ticker_for_country("2330.TW", "IN")


def test_batch_parser_infers_mixed_countries_from_formatted_tickers():
    items = parse_batch_items([
        {"ticker": "MSFT"},
        {"ticker": "TCS.NS"},
        {"ticker": "2330.TW"},
        {"ticker": "000660.KS"},
        {"ticker": "035420.KQ"},
    ])
    assert [item.country for item in items] == ["US", "IN", "TW", "KR", "KR"]


@pytest.mark.parametrize(
    "ticker,expected",
    [("MSFT", "US"), ("7203.T", "JP"), ("AZN.L", "GB"), ("TCS.NS", "IN"),
     ("2330.TW", "TW"), ("000660.KS", "KR"), ("035420.KQ", "KR")],
)
def test_country_is_inferred_from_yahoo_ticker(ticker, expected):
    assert infer_country_from_ticker(ticker) == expected


def test_frontend_batch_is_limited_to_one_hundred_companies():
    with pytest.raises(ValueError, match="at most 100"):
        parse_batch_items([{"ticker": f"TEST{i}"} for i in range(101)])


def test_parse_batch_items_requires_a_company():
    with pytest.raises(ValueError, match="at least one"):
        parse_batch_items([])


def test_frontend_single_workflow_creates_excel_report(tmp_path, snapshot_factory, monkeypatch):
    monkeypatch.setattr("growth_scorer.app.USER_DATA_ROOT", tmp_path)
    monkeypatch.setattr(
        "growth_scorer.app.build_snapshot",
        lambda ticker, country, as_of: snapshot_factory(
            "general", 2, ticker=ticker, country=country, as_of=as_of
        ),
    )
    from growth_scorer.app import score_company

    result = score_company("tcs", "in", date(2026, 9, 20))

    assert result["ticker"] == "TCS.NS"
    assert result["scorecard"] == "general"
    assert Path(result["workbook_path"]).exists()
