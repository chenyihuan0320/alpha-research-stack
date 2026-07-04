"""AlphaSift adapter boundary skeleton.

This module intentionally does not import or call AlphaSift. It only defines
the data contract boundary that future provider evidence must pass through.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


BLOCKING_GATE_STATUSES = {"block", "pending_credentials"}


@dataclass(slots=True)
class AlphaSiftCandidateInput:
    run_id: str
    market: str
    ticker: str
    candidate_date: str
    provider_evidence: dict[str, Any]
    quality_gate_status: str


@dataclass(slots=True)
class AlphaSiftCandidateOutput:
    run_id: str
    market: str
    ticker: str
    candidate_date: str
    candidate_score: float | None
    reasons: list[str] = field(default_factory=list)
    raw_payload: dict[str, Any] = field(default_factory=dict)
    quality_flags: list[str] = field(default_factory=list)


def _gate_status(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("quality_gate_status") or value.get("gate_status") or "")
    return str(getattr(value, "quality_gate_status", getattr(value, "gate_status", "")))


def can_send_to_alphasift(evidence: Any) -> bool:
    return _gate_status(evidence) not in BLOCKING_GATE_STATUSES


def build_alphasift_input(evidence: dict[str, Any]) -> AlphaSiftCandidateInput:
    if not can_send_to_alphasift(evidence):
        raise ValueError("Evidence blocked by data_quality_gate and cannot be sent to AlphaSift.")
    return AlphaSiftCandidateInput(
        run_id=str(evidence["run_id"]),
        market=str(evidence["market"]),
        ticker=str(evidence["ticker"]),
        candidate_date=str(evidence["candidate_date"]),
        provider_evidence=dict(evidence.get("provider_evidence", {})),
        quality_gate_status=str(evidence.get("quality_gate_status", "")),
    )


def parse_alphasift_output(payload: dict[str, Any]) -> AlphaSiftCandidateOutput:
    return AlphaSiftCandidateOutput(
        run_id=str(payload.get("run_id", "")),
        market=str(payload.get("market", "")),
        ticker=str(payload.get("ticker", "")),
        candidate_date=str(payload.get("candidate_date", "")),
        candidate_score=payload.get("candidate_score"),
        reasons=[str(item) for item in payload.get("reasons", [])],
        raw_payload=dict(payload),
        quality_flags=[str(item) for item in payload.get("quality_flags", [])],
    )
