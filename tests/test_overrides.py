from datetime import date

import pandas as pd
import pytest

from growth_scorer.overrides import apply_overrides, discover_override, read_overrides


def test_verified_overrides_precede_yahoo_and_future_rows_are_blocked(tmp_path, snapshot_factory):
    path = tmp_path / "overrides.xlsx"
    pd.DataFrame(
        [
            {
                "Metric name": "ROIC",
                "Value": 0.22,
                "Unit": "%",
                "Reporting period": "2025",
                "Publication date": "2026-03-01",
                "Source URL": "https://example.test/filing",
                "Verified by": "Analyst A",
            },
            {
                "Metric name": "FCF margin",
                "Value": 0.99,
                "Unit": "%",
                "Reporting period": "2026",
                "Publication date": "2026-10-01",
                "Source URL": "https://example.test/future",
                "Verified by": "Analyst A",
            },
        ]
    ).to_excel(path, index=False)
    records, warnings = read_overrides(path, date(2026, 9, 20))
    snapshot = snapshot_factory("general")
    apply_overrides(snapshot, records, warnings)
    assert snapshot.metrics["roic"] == 0.22
    assert snapshot.metric_sources["roic"].startswith("verified override")
    assert snapshot.metrics["fcf_margin"] != 0.99
    assert any("after as-of" in warning for warning in snapshot.warnings)


def test_discover_override_uses_detected_scorecard_and_exact_ticker(tmp_path):
    scorecard_dir = tmp_path / "consumer"
    scorecard_dir.mkdir()
    expected = scorecard_dir / "NKE.xlsx"
    expected.touch()
    (scorecard_dir / "OTHER.xlsx").touch()
    assert discover_override(tmp_path, "NKE", "consumer") == expected.resolve()


def test_discover_override_rejects_ambiguous_matches(tmp_path):
    (tmp_path / "MSFT.csv").touch()
    (tmp_path / "technology_MSFT.xlsx").touch()
    with pytest.raises(ValueError, match="Multiple automatic override"):
        discover_override(tmp_path, "MSFT", "technology")
