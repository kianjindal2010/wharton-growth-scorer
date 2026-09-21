from datetime import date
from pathlib import Path

import pytest

from growth_scorer.app import parse_as_of, parse_batch_items


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

    result = score_company("AAA", "US", date(2026, 9, 20))

    assert result["ticker"] == "AAA"
    assert result["scorecard"] == "general"
    assert Path(result["workbook_path"]).exists()
