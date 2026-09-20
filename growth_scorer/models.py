from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


ScorecardName = Literal[
    "general", "technology", "healthcare", "financial_platform", "industrial", "consumer",
    "energy_materials", "bank", "insurer", "biotech", "semiconductor", "memory_semiconductor",
]


class SourceRecord(BaseModel):
    source: str
    retrieval_time: datetime
    reporting_period: str | None = None
    url: str | None = None
    provenance: str | None = None


class OverrideRecord(BaseModel):
    metric_name: str
    value: float
    unit: str | None = None
    reporting_period: str | None = None
    publication_date: date
    source_url: str | None = None
    verified_by: str

    @field_validator("metric_name")
    @classmethod
    def normalize_metric(cls, value: str) -> str:
        return value.strip().lower().replace(" ", "_").replace("-", "_")


class InputSnapshot(BaseModel):
    ticker: str
    country: str
    as_of: date
    retrieved_at: datetime
    company_name: str | None = None
    sector: str | None = None
    industry: str | None = None
    currency: str | None = None
    prices: list[dict[str, Any]] = Field(default_factory=list)
    benchmark_prices: list[dict[str, Any]] = Field(default_factory=list)
    fx_rates: list[dict[str, Any]] = Field(default_factory=list)
    news: list[dict[str, Any]] = Field(default_factory=list)
    statements: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    metrics: dict[str, float | None] = Field(default_factory=dict)
    metric_sources: dict[str, str] = Field(default_factory=dict)
    last_price_date: date | None = None
    latest_financial_date: date | None = None
    source_log: list[SourceRecord] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "InputSnapshot":
        return cls.model_validate_json(path.read_text(encoding="utf-8"))


class FactorResult(BaseModel):
    pillar: str
    metric: str
    label: str
    weight: float
    raw_value: float | None
    unit: str
    score: float
    contribution: float
    observed: bool
    source: str
    bad_anchor: float | None = None
    neutral_anchor: float | None = None
    excellent_anchor: float | None = None


class ScoreResult(BaseModel):
    ticker: str
    company_name: str | None
    country: str
    as_of: date
    scorecard: ScorecardName
    score: float
    verdict: str
    confidence: float
    rank: int | None = None
    comparable_count: int = 0
    risk_gates: list[str] = Field(default_factory=list)
    factors: list[FactorResult]
    pillar_scores: dict[str, float]
    warnings: list[str] = Field(default_factory=list)
    snapshot_path: str | None = None
    workbook_path: str | None = None
    json_path: str | None = None
