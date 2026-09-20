from datetime import date

import pytest

from growth_scorer.cli import _interactive_score_args, _validate_ticker_country, build_parser


def test_predict_alias_accepts_complete_noninteractive_command(monkeypatch):
    args = build_parser().parse_args(
        ["predict", "--ticker", "MSFT", "--country", "US", "--as-of", "2026-09-20", "--scorecard", "auto"]
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: (_ for _ in ()).throw(AssertionError("should not prompt")))
    resolved = _interactive_score_args(args)
    assert resolved.ticker == "MSFT"
    assert resolved.as_of == date(2026, 9, 20)


@pytest.mark.parametrize(
    "ticker,country",
    [("MSFT", "US"), ("7203.T", "JP"), ("AZN.L", "GB"), ("TCS.NS", "IN"), ("2330.TW", "TW"), ("000660.KS", "KR")],
)
def test_ticker_country_formats(ticker, country):
    _validate_ticker_country(ticker, country)


def test_mismatched_ticker_country_is_rejected():
    with pytest.raises(ValueError, match="does not match"):
        _validate_ticker_country("2330.TW", "US")


def test_predict_prompts_when_inputs_are_missing(monkeypatch):
    answers = iter(["2330.TW", "TW", "2026-09-20", "auto", ""])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    args = build_parser().parse_args(["predict"])
    resolved = _interactive_score_args(args)
    assert resolved.ticker == "2330.TW"
    assert resolved.country == "TW"
    assert resolved.as_of == date(2026, 9, 20)
