"""Evidence models for provider-level data quality records."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any


def _normalize_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, list):
        return [_normalize_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _normalize_value(item) for key, item in value.items()}
    return value


@dataclass(slots=True)
class ProviderEvidence:
    evidence_id: str
    run_id: str
    market: str
    ticker: str
    data_domain: str
    provider: str
    provider_ticker: str
    source_updated_at: datetime
    observed_at: datetime
    normalized_payload: dict[str, Any]
    raw_field_mapping: dict[str, Any]
    quality_flags: list[str] = field(default_factory=list)
    cross_source_status: str = "unchecked"
    gate_status: str = "block"
    allowed_downstream: list[str] = field(default_factory=list)
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _normalize_value(asdict(self))

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ProviderEvidence":
        data = dict(payload)
        for field_name in ("source_updated_at", "observed_at"):
            value = data.get(field_name)
            if isinstance(value, str):
                data[field_name] = datetime.fromisoformat(value)
        return cls(**data)
