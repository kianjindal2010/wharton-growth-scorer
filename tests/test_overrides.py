from datetime import date

import pandas as pd

from growth_scorer.overrides import apply_overrides, read_overrides


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

