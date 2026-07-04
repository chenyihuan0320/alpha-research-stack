"""AlphaSift adapter boundary skeleton.

This module intentionally does not import or call AlphaSift. It only defines
the data contract boundary that future provider evidence must pass through.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


ALPHASIFT_DOWNSTREAM_NAMES = {"alphasift", "alphasift_exploratory"}


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


def _allowed_downstream(value: Any) -> list[str]:
    if isinstance(value, dict):
        items = value.get("allowed_downstream", [])
    else:
        items = getattr(value, "allowed_downstream", [])
    return [str(item) for item in (items or [])]


def _evidence_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if hasattr(value, "to_dict"):
        return dict(value.to_dict())
    return {
        key: getattr(value, key)
        for key in (
            "evidence_id",
            "run_id",
            "market",
            "ticker",
            "data_domain",
            "source_updated_at",
            "observed_at",
            "normalized_payload",
            "raw_field_mapping",
            "quality_flags",
            "gate_status",
            "allowed_downstream",
        )
        if hasattr(value, key)
    }


def _candidate_date_from_evidence(evidence: dict[str, Any]) -> str:
    value = evidence.get("observed_at") or evidence.get("source_updated_at") or ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value)
    if "T" in text:
        return text.split("T", 1)[0]
    return text[:10]


def can_send_to_alphasift(evidence: Any) -> bool:
    return bool(ALPHASIFT_DOWNSTREAM_NAMES & set(_allowed_downstream(evidence)))


def build_alphasift_input(evidence: Any) -> AlphaSiftCandidateInput:
    data = _evidence_dict(evidence)
    if data.get("data_domain") != "daily_bar":
        raise ValueError("AlphaSift adapter only accepts daily_bar ProviderEvidence.")
    if not can_send_to_alphasift(data):
        raise ValueError("Evidence is not allowed_downstream for AlphaSift.")
    return AlphaSiftCandidateInput(
        run_id=str(data["run_id"]),
        market=str(data["market"]),
        ticker=str(data["ticker"]),
        candidate_date=_candidate_date_from_evidence(data),
        provider_evidence=data,
        quality_gate_status=str(data.get("gate_status", "")),
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
