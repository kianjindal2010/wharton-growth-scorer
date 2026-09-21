from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

import numpy as np

from .config import COMMON_NEWS_SPECS, load_scorecards
from .classification import detect_classification
from .models import FactorResult, InputSnapshot, ScoreResult, ScorecardName
from .transforms import piecewise_score


REQUIRED_SPECIALIST_METRICS: dict[str, set[str]] = {
    name: set() for name in load_scorecards()
}

NON_FINANCIAL_SCORECARDS = set(REQUIRED_SPECIALIST_METRICS) - {"bank", "insurer", "biotech"}
def classify(snapshot: InputSnapshot, requested: str = "auto") -> ScorecardName:
    return detect_classification(snapshot, requested).scorecard


def _business_days_after(last_date: date | None, as_of: date) -> int | None:
    if last_date is None:
        return None
    if last_date >= as_of:
        return 0
    return int(np.busday_count(last_date.isoformat(), as_of.isoformat()))


def _month_age(period: date | None, as_of: date) -> int | None:
    if period is None:
        return None
    return (as_of.year - period.year) * 12 + as_of.month - period.month


def _risk_gates(snapshot: InputSnapshot, scorecard: ScorecardName) -> list[str]:
    m = snapshot.metrics
    gates: list[str] = []
    if m.get("book_equity") is not None and float(m["book_equity"]) < 0:
        gates.append("Negative book equity")
    if scorecard in NON_FINANCIAL_SCORECARDS:
        leverage = m.get("net_debt_ebitda")
        coverage = m.get("interest_coverage")
        if leverage is not None and coverage is not None and leverage > 6 and coverage < 1:
            gates.append("Net debt/EBITDA exceeds 6x while interest coverage is below 1x")
    if scorecard == "biotech":
        runway = m.get("cash_runway_months")
        if runway is not None and runway < 12:
            gates.append("Estimated cash runway is below 12 months")
    return gates


def score_snapshot(snapshot: InputSnapshot, requested_scorecard: str = "auto") -> ScoreResult:
    classification = detect_classification(snapshot, requested_scorecard)
    scorecard = classification.scorecard
    cards = load_scorecards()
    core_specs: list[dict[str, Any]] = cards[scorecard]
    if round(sum(float(spec["weight"]) for spec in core_specs), 8) != 100:
        raise ValueError(f"{scorecard} scorecard weights do not sum to 100")
    specs = [dict(spec, weight=float(spec["weight"]) * 0.95) for spec in core_specs]
    specs.extend(COMMON_NEWS_SPECS)

    factors: list[FactorResult] = []
    pillar_contrib: dict[str, float] = defaultdict(float)
    pillar_weight: dict[str, float] = defaultdict(float)
    observed_weight = 0.0
    warnings = list(snapshot.warnings)

    for spec in specs:
        metric = spec["metric"]
        raw = snapshot.metrics.get(metric)
        observed = raw is not None and np.isfinite(float(raw))
        if observed:
            observed_weight += float(spec["weight"])
        else:
            raw = None
            warnings.append(f"Missing metric: {metric}; neutral score of 50 applied")
        bad, neutral, excellent = map(float, spec["anchors"])
        transformed = piecewise_score(raw, bad, neutral, excellent)
        if observed and transformed in {0.0, 100.0}:
            low, high = sorted((bad, excellent))
            if float(raw) < low or float(raw) > high:
                warnings.append(f"Metric {metric} clipped at {int(transformed)}")
        contribution = transformed * float(spec["weight"]) / 100.0
        pillar_contrib[spec["pillar"]] += contribution
        pillar_weight[spec["pillar"]] += float(spec["weight"])
        factors.append(
            FactorResult(
                pillar=spec["pillar"],
                metric=metric,
                label=spec["label"],
                weight=float(spec["weight"]),
                raw_value=raw,
                unit=spec["unit"],
                score=round(transformed, 4),
                contribution=round(contribution, 4),
                observed=observed,
                source=snapshot.metric_sources.get(metric, "missing" if not observed else "calculated"),
                bad_anchor=bad,
                neutral_anchor=neutral,
                excellent_anchor=excellent,
            )
        )

    total = round(sum(
        factor.score * factor.weight / 100.0 for factor in factors
    ), 4)
    contribution_residual = round(total - sum(f.contribution for f in factors), 4)
    if factors and contribution_residual:
        factors[-1].contribution = round(factors[-1].contribution + contribution_residual, 4)
    confidence = round(observed_weight, 2)
    risk_gates = _risk_gates(snapshot, scorecard)
    stale_days = _business_days_after(snapshot.last_price_date, snapshot.as_of)
    statement_age = _month_age(snapshot.latest_financial_date, snapshot.as_of)
    insufficient_reasons: list[str] = []
    if stale_days is None:
        insufficient_reasons.append("No valid last price date")
    elif stale_days > 5:
        insufficient_reasons.append(f"Price is stale by {stale_days} business days")
    if statement_age is None:
        insufficient_reasons.append("No valid financial statement date")
    elif statement_age > 21:
        insufficient_reasons.append(f"Latest financial statements are {statement_age} months old")
    missing_required = sorted(
        metric
        for metric in REQUIRED_SPECIALIST_METRICS[scorecard]
        if snapshot.metrics.get(metric) is None
    )
    if missing_required:
        insufficient_reasons.append(
            "Required specialist metrics missing: " + ", ".join(missing_required)
        )
    warnings.extend(insufficient_reasons)

    if confidence < 70 or insufficient_reasons:
        verdict = "Insufficient Data"
        if confidence < 70:
            warnings.append(f"Data confidence {confidence:.1f}% is below the 70% minimum")
    elif risk_gates:
        verdict = "Reject"
    elif total >= 75:
        verdict = "Buy Candidate"
    elif total >= 60:
        verdict = "Watch"
    else:
        verdict = "Reject"

    pillar_scores = {
        pillar: round(100.0 * pillar_contrib[pillar] / pillar_weight[pillar], 2)
        for pillar in pillar_weight
    }
    return ScoreResult(
        ticker=snapshot.ticker,
        company_name=snapshot.company_name,
        country=snapshot.country,
        as_of=snapshot.as_of,
        scorecard=scorecard,
        classification_confidence=classification.confidence,
        classification_reason=classification.reason,
        score=total,
        verdict=verdict,
        confidence=confidence,
        risk_gates=risk_gates,
        factors=factors,
        pillar_scores=pillar_scores,
        warnings=list(dict.fromkeys(warnings)),
    )
