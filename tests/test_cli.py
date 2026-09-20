from datetime import date

from growth_scorer.cli import _interactive_score_args, build_parser


def test_predict_alias_accepts_complete_noninteractive_command(monkeypatch):
    args = build_parser().parse_args(
        ["predict", "--ticker", "MSFT", "--country", "US", "--as-of", "2026-09-20", "--scorecard", "auto"]
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: (_ for _ in ()).throw(AssertionError("should not prompt")))
    resolved = _interactive_score_args(args)
    assert resolved.ticker == "MSFT"
    assert resolved.as_of == date(2026, 9, 20)


def test_predict_prompts_when_inputs_are_missing(monkeypatch):
    answers = iter(["2330.TW", "TW", "2026-09-20", "auto", ""])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    args = build_parser().parse_args(["predict"])
    resolved = _interactive_score_args(args)
    assert resolved.ticker == "2330.TW"
    assert resolved.country == "TW"
    assert resolved.as_of == date(2026, 9, 20)
