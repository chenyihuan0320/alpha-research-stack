"""Minimal data contracts for Alpha Research Stack."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any


class Market(str, Enum):
    CN = "CN"
    HK = "HK"
    US = "US"


class QualityFlag(str, Enum):
    MISSING_FIELD = "missing_field"
    PARSE_ERROR = "parse_error"
    SOURCE_CONFLICT = "source_conflict"
    ESTIMATED_VALUE = "estimated_value"
    STALE_SOURCE = "stale_source"
    UNKNOWN_ADJUSTMENT = "unknown_adjustment"
    UNIT_UNVERIFIED = "unit_unverified"
    ADJUSTMENT_UNVERIFIED = "adjustment_unverified"
    PROVIDER_ERROR = "provider_error"
    ASOF_MISMATCH = "asof_mismatch"
    PARTIAL_COVERAGE = "partial_coverage"
    TICKER_MAPPING_UNVERIFIED = "ticker_mapping_unverified"
    CURRENCY_UNVERIFIED = "currency_unverified"


def _normalize_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, list):
        return [_normalize_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _normalize_value(item) for key, item in value.items()}
    return value


class DictSerializable:
    def to_dict(self) -> dict[str, Any]:
        return _normalize_value(asdict(self))


@dataclass(slots=True)
class SecurityMaster(DictSerializable):
    market: Market
    ticker: str
    name: str
    exchange: str | None
    currency: str | None
    sector: str | None
    industry: str | None
    source: str
    source_updated_at: datetime
    is_active: bool
    notes: str | None = None


@dataclass(slots=True)
class DailyBar(DictSerializable):
    market: Market
    ticker: str
    date: date
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    adj_close: float | None
    volume: float | None
    amount: float | None
    turnover: float | None
    source: str
    source_updated_at: datetime
    adjustment: str | None
    quality_flags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class FundamentalsSnapshot(DictSerializable):
    market: Market
    ticker: str
    period_end: date
    fiscal_period: str | None
    report_date: date | None
    revenue: float | None
    gross_profit: float | None
    operating_income: float | None
    net_income: float | None
    operating_cash_flow: float | None
    free_cash_flow: float | None
    total_assets: float | None
    total_liabilities: float | None
    total_equity: float | None
    debt: float | None
    shares_outstanding: float | None
    source: str
    source_updated_at: datetime
    quality_flags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ValuationSnapshot(DictSerializable):
    market: Market
    ticker: str
    date: date
    market_cap: float | None
    pe: float | None
    pb: float | None
    ps: float | None
    ev_ebitda: float | None
    dividend_yield: float | None
    fcf_yield: float | None
    source: str
    source_updated_at: datetime
    quality_flags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class EventRecord(DictSerializable):
    market: Market
    ticker: str
    event_date: date
    event_type: str
    title: str
    summary: str | None
    url: str | None
    source: str
    source_updated_at: datetime
    quality_flags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CandidateEvidence(DictSerializable):
    run_id: str
    market: Market
    ticker: str
    candidate_date: date
    source_strategy: str
    evidence_type: str
    evidence_payload: dict[str, Any]
    data_sources: list[str]
    quality_flags: list[str]
    created_at: datetime
