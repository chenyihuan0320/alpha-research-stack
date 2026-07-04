"""Candidate evidence contract.

CandidateEvidence records reusable candidate-discovery outputs. It is not a
signal, recommendation, or final confidence object.
"""

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
class CandidateEvidence:
    candidate_id: str
    run_id: str
    market: str
    ticker: str
    candidate_date: str
    candidate_source: str
    candidate_direction: str
    candidate_score: float | None
    reasons: list[str] = field(default_factory=list)
    provider_evidence_ids: list[str] = field(default_factory=list)
    provider_evidence_domains: list[str] = field(default_factory=list)
    quality_flags: list[str] = field(default_factory=list)
    raw_payload: dict[str, Any] = field(default_factory=dict)
    gate_status: str = "block"
    allowed_next_steps: list[str] = field(default_factory=list)
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _normalize_value(asdict(self))

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CandidateEvidence":
        return cls(**dict(payload))
