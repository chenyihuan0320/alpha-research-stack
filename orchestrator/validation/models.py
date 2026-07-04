"""Validation evidence models.

ValidationEvidence records historical/event validation observations. It is not
a signal, recommendation, or final confidence score.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class ValidationEvidence:
    validation_id: str
    run_id: str
    market: str
    ticker: str
    event_date: str
    validation_source: str
    holding_period: int
    forward_return: float | None
    max_favorable_excursion: float | None
    max_adverse_excursion: float | None
    hit_take_profit: bool | None
    hit_stop_loss: bool | None
    provider_evidence_ids: list[str]
    panel_rows_used: int
    quality_flags: list[str]
    raw_payload: dict[str, Any]
    gate_status: str
    allowed_next_steps: list[str]
    notes: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ValidationEvidence":
        data = dict(payload)
        data["holding_period"] = int(data["holding_period"])
        data["panel_rows_used"] = int(data["panel_rows_used"])
        data["provider_evidence_ids"] = [str(item) for item in data.get("provider_evidence_ids", [])]
        data["quality_flags"] = [str(item) for item in data.get("quality_flags", [])]
        data["allowed_next_steps"] = [str(item) for item in data.get("allowed_next_steps", [])]
        data["raw_payload"] = dict(data.get("raw_payload", {}))
        return cls(**data)
