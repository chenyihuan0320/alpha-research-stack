"""Candidate-to-validation linkage models.

CandidateValidationLink records relationships between CandidateEvidence and
ValidationEvidence. It is not a signal, recommendation, or final confidence
object.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class CandidateValidationLink:
    link_id: str
    candidate_id: str
    validation_ids: list[str]
    ticker: str
    market: str
    candidate_date: str
    validation_window: str
    linkage_status: str
    quality_flags: list[str]
    notes: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CandidateValidationLink":
        data = dict(payload)
        data["validation_ids"] = [str(item) for item in data.get("validation_ids", [])]
        data["quality_flags"] = [str(item) for item in data.get("quality_flags", [])]
        return cls(**data)
