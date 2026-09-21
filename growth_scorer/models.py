from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


ScorecardName = Literal[
    "general", "technology", "healthcare", "financial_platform", "industrial", "consumer",
    "energy_materials", "bank", "insurer", "biotech", "semiconductor", "memory_semiconductor",
    "software_cloud", "hardware_telecom", "pharmaceuticals", "medical_devices",
    "payments_fintech", "asset_management", "aerospace_defense", "transportation_logistics",
    "automotive", "capital_goods", "consumer_staples", "retail_discretionary",
    "media_education", "oil_gas", "utilities_renewables", "materials_mining",
]


class SourceRecord(BaseModel):
    source: str
    retrieval_time: datetime
    reporting_period: str | None = None
    url: str | None = None


class InputSnapshot(BaseModel):
    ticker: str
    country: str
    as_of: date
    retrieved_at: datetime
    company_name: str | None = None
    sector: str | None = None
    sector_key: str | None = None
    industry: str | None = None
    industry_key: str | None = None
    business_summary: str | None = None
    quote_type: str | None = None
    exchange: str | None = None
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
    classification_confidence: str = ""
    classification_reason: str = ""
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
