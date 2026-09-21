from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pandas as pd

from .models import InputSnapshot, OverrideRecord, SourceRecord


REQUIRED_COLUMNS = {
    "metric name",
    "value",
    "unit",
    "reporting period",
    "publication date",
    "source url",
    "verified by",
}


def discover_override(root: Path | None, ticker: str, scorecard: str) -> Path | None:
    """Find one exact ticker-specific verified override after automatic classification."""
    if root is None or not root.exists():
        return None
    safe_ticker = "".join(character if character.isalnum() or character in "._-" else "_" for character in ticker)
    stems = {
        safe_ticker.lower(),
        f"{scorecard}_{safe_ticker}".lower(),
        f"{safe_ticker}_{scorecard}".lower(),
    }
    candidates: list[Path] = []
    search_directories = [root, root / scorecard]
    for directory in search_directories:
        if not directory.is_dir():
            continue
        for path in directory.iterdir():
            if path.is_file() and path.suffix.lower() in {".csv", ".xlsx"} and path.stem.lower() in stems:
                candidates.append(path)
    unique = sorted({path.resolve() for path in candidates}, key=lambda path: str(path).lower())
    if len(unique) > 1:
        names = ", ".join(str(path) for path in unique)
        raise ValueError(f"Multiple automatic override files match {ticker}: {names}")
    return unique[0] if unique else None


def read_overrides(path: Path, as_of: date) -> tuple[list[OverrideRecord], list[str]]:
    frame = pd.read_csv(path) if path.suffix.lower() == ".csv" else pd.read_excel(path)
    normalized = {str(column).strip().lower(): column for column in frame.columns}
    missing = REQUIRED_COLUMNS - set(normalized)
    if missing:
        raise ValueError(f"Override workbook is missing columns: {', '.join(sorted(missing))}")

    records: list[OverrideRecord] = []
    warnings: list[str] = []
    for row_number, (_, row) in enumerate(frame.iterrows(), start=2):
        verifier = row[normalized["verified by"]]
        if pd.isna(verifier) or not str(verifier).strip():
            warnings.append(f"Override row {row_number} ignored: Verified by is blank")
            continue
        publication = pd.to_datetime(row[normalized["publication date"]], errors="coerce")
        if pd.isna(publication):
            warnings.append(f"Override row {row_number} ignored: invalid publication date")
            continue
        if publication.date() > as_of:
            warnings.append(f"Override row {row_number} ignored: publication date is after as-of date")
            continue
        try:
            records.append(
                OverrideRecord(
                    metric_name=str(row[normalized["metric name"]]),
                    value=float(row[normalized["value"]]),
                    unit=None if pd.isna(row[normalized["unit"]]) else str(row[normalized["unit"]]),
                    reporting_period=None
                    if pd.isna(row[normalized["reporting period"]])
                    else str(row[normalized["reporting period"]]),
                    publication_date=publication.date(),
                    source_url=None
                    if pd.isna(row[normalized["source url"]])
                    else str(row[normalized["source url"]]),
                    verified_by=str(verifier).strip(),
                )
            )
        except (TypeError, ValueError) as exc:
            warnings.append(f"Override row {row_number} ignored: {exc}")
    return records, warnings


def apply_overrides(snapshot: InputSnapshot, records: list[OverrideRecord], warnings: list[str]) -> None:
    snapshot.warnings.extend(warnings)
    for record in records:
        snapshot.metrics[record.metric_name] = record.value
        snapshot.metric_sources[record.metric_name] = f"verified override: {record.verified_by}"
        snapshot.source_log.append(
            SourceRecord(
                source="Verified analyst override",
                retrieval_time=datetime.now().astimezone(),
                reporting_period=record.reporting_period,
                url=record.source_url,
                provenance=f"{record.metric_name}; verified by {record.verified_by}",
            )
        )

    m = snapshot.metrics
    if m.get("cet1_ratio") is not None and m.get("cet1_minimum") is not None:
        m["cet1_buffer"] = m["cet1_ratio"] - m["cet1_minimum"]
        snapshot.metric_sources["cet1_buffer"] = "calculated from verified CET1 ratio and minimum"
    if m.get("solvency_ratio") is not None and m.get("solvency_minimum") is not None:
        m["solvency_buffer"] = m["solvency_ratio"] - m["solvency_minimum"]
        snapshot.metric_sources["solvency_buffer"] = "calculated from verified solvency ratio and minimum"
