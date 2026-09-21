from datetime import date

import pytest

from growth_scorer.engine import classify, score_snapshot
from growth_scorer.config import load_scorecards


@pytest.mark.parametrize("scorecard", sorted(load_scorecards()))
def test_synthetic_scorecards_are_complete_and_sum(scorecard, snapshot_factory):
    snapshot = snapshot_factory(scorecard, anchor_index=2)
    requested = scorecard
    assert classify(snapshot, requested) == scorecard
    result = score_snapshot(snapshot, requested)
    assert result.score == pytest.approx(100)
    assert result.confidence == 100
    assert result.verdict == "Buy Candidate"
    assert sum(item.contribution for item in result.factors) == pytest.approx(result.score)


@pytest.mark.parametrize(
    "industry,industry_key,summary,expected",
    [
        ("Software - Infrastructure", "software-infrastructure", "Cloud software platform", "software_cloud"),
        ("Medical Devices", "medical-devices", "Makes surgical systems", "medical_devices"),
        ("Capital Markets", "capital-markets", "Operates an exchange", "asset_management"),
        ("Aerospace & Defense", "aerospace-defense", "Aircraft systems", "aerospace_defense"),
        ("Internet Retail", "internet-retail", "Online retailer", "retail_discretionary"),
        ("Specialty Chemicals", "specialty-chemicals", "Chemical producer", "materials_mining"),
        ("Semiconductors", "semiconductors", "Produces DRAM, NAND and HBM", "memory_semiconductor"),
        ("Semiconductor Equipment & Materials", "semiconductor-equipment-materials", "Lithography", "semiconductor"),
    ],
)
def test_detailed_industry_detection(industry, industry_key, summary, expected, snapshot_factory):
    snapshot = snapshot_factory(
        "general", industry=industry, industry_key=industry_key, business_summary=summary,
    )
    assert classify(snapshot) == expected


def test_classification_reason_is_recorded(snapshot_factory):
    snapshot = snapshot_factory(
        "general", industry="Internet Retail", industry_key="internet-retail",
    )
    result = score_snapshot(snapshot)
    assert result.scorecard == "retail_discretionary"
    assert result.classification_confidence == "high"
    assert "internet retail" in result.classification_reason.lower()


def test_missing_metrics_keep_neutral_weight_but_reduce_confidence(snapshot_factory):
    snapshot = snapshot_factory("general", anchor_index=2)
    for key in list(snapshot.metrics)[:12]:
        snapshot.metrics[key] = None
    result = score_snapshot(snapshot, "general")
    assert result.confidence < 70
    assert result.verdict == "Insufficient Data"
    missing = [factor for factor in result.factors if not factor.observed]
    assert missing and all(factor.score == 50 for factor in missing)


@pytest.mark.parametrize(
    "scorecard,changes,gate_text",
    [
        ("general", {"book_equity": -1}, "Negative book equity"),
        ("general", {"net_debt_ebitda": 7, "interest_coverage": 0.5}, "Net debt/EBITDA"),
        ("bank", {"book_equity": -1}, "Negative book equity"),
        ("insurer", {"book_equity": -1}, "Negative book equity"),
        ("biotech", {"cash_runway_months": 11}, "runway"),
    ],
)
def test_risk_gates_take_precedence_over_high_score(scorecard, changes, gate_text, snapshot_factory):
    result = score_snapshot(snapshot_factory(scorecard, 2, metric_changes=changes), scorecard)
    assert result.score >= 75
    assert result.verdict == "Reject"
    assert gate_text.lower() in " ".join(result.risk_gates).lower()


def test_stale_price_and_old_statements_force_insufficient(snapshot_factory):
    snapshot = snapshot_factory(
        "general",
        2,
        last_price_date=date(2026, 9, 1),
        latest_financial_date=date(2024, 1, 1),
    )
    result = score_snapshot(snapshot)
    assert result.verdict == "Insufficient Data"
    assert any("stale" in warning for warning in result.warnings)
    assert any("months old" in warning for warning in result.warnings)


@pytest.mark.parametrize(
    "score,expected",
    [(100, "Buy Candidate"), (50, "Reject")],
)
def test_simple_verdict_ranges(score, expected, snapshot_factory):
    anchor = 2 if score == 100 else 1
    result = score_snapshot(snapshot_factory("general", anchor), "general")
    assert result.verdict == expected


def _metrics_for_uniform_score(target):
    values = {}
    for spec in load_scorecards()["general"]:
        bad, neutral, excellent = spec["anchors"]
        if target <= 50:
            value = bad + (neutral - bad) * target / 50
        else:
            value = neutral + (excellent - neutral) * (target - 50) / 50
        values[spec["metric"]] = value
    values.update({"book_equity": 100, "operating_income": 10, "free_cash_flow": 10})
    from growth_scorer.config import COMMON_NEWS_SPECS
    for spec in COMMON_NEWS_SPECS:
        bad, neutral, excellent = spec["anchors"]
        if target <= 50:
            values[spec["metric"]] = bad + (neutral - bad) * target / 50
        else:
            values[spec["metric"]] = neutral + (excellent - neutral) * (target - 50) / 50
    return values


@pytest.mark.parametrize(
    "target,verdict",
    [(59.9, "Reject"), (60.0, "Watch"), (74.99, "Watch"), (75.0, "Buy Candidate")],
)
def test_exact_verdict_boundaries(target, verdict, snapshot_factory):
    snapshot = snapshot_factory("general", metric_changes=_metrics_for_uniform_score(target))
    result = score_snapshot(snapshot, "general")
    assert result.score == pytest.approx(target, abs=0.01)
    assert result.verdict == verdict


def test_missing_statement_date_is_insufficient(snapshot_factory):
    result = score_snapshot(snapshot_factory("general", 2, latest_financial_date=None))
    assert result.verdict == "Insufficient Data"
    assert "No valid financial statement date" in result.warnings


def test_bank_model_uses_only_automated_metrics(snapshot_factory):
    snapshot = snapshot_factory("bank", 2)
    snapshot.metrics["equity_to_assets"] = None
    result = score_snapshot(snapshot, "bank")
    assert result.confidence >= 70
    assert not any("Required specialist metrics missing" in warning for warning in result.warnings)
    factor = next(item for item in result.factors if item.metric == "equity_to_assets")
    assert factor.score == 50
