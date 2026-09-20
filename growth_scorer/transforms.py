from __future__ import annotations

import math


def piecewise_score(
    value: float | None,
    bad: float,
    neutral: float,
    excellent: float,
) -> float:
    """Map a value to 0..100 with clipping and two linear segments.

    Anchors may be ascending or descending. A missing/non-finite value receives 50.
    """
    if value is None or not math.isfinite(float(value)):
        return 50.0
    value = float(value)
    if bad == neutral or neutral == excellent:
        raise ValueError("Anchors must be distinct")

    ascending = excellent > bad
    if ascending:
        if value <= bad:
            return 0.0
        if value >= excellent:
            return 100.0
    else:
        if value >= bad:
            return 0.0
        if value <= excellent:
            return 100.0

    if (ascending and value <= neutral) or (not ascending and value >= neutral):
        return 50.0 * (value - bad) / (neutral - bad)
    return 50.0 + 50.0 * (value - neutral) / (excellent - neutral)


def safe_div(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    value = numerator / denominator
    return value if math.isfinite(value) else None


def signed_cagr(first: float | None, last: float | None, years: float) -> float | None:
    """CAGR only where a real economic interpretation exists."""
    if first is None or last is None or years <= 0 or first <= 0 or last < 0:
        return None
    return (last / first) ** (1.0 / years) - 1.0

