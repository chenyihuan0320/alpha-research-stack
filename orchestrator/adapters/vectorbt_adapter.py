"""vectorbt adapter boundary skeleton.

This module intentionally does not import or call vectorbt. It only defines
the future validation input/output shape and gate checks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


VECTORBT_DOWNSTREAM_NAME = "vectorbt"


@dataclass(slots=True)
class VectorBTValidationInput:
    ticker: str
    market: str
    daily_bars: list[dict[str, Any]]
    event_dates: list[str]
    holding_period: int
    quality_gate_status: str


@dataclass(slots=True)
class VectorBTValidationResult:
    ticker: str
    market: str
    status: str
    metrics: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    raw_payload: dict[str, Any] = field(default_factory=dict)


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
            "ticker",
            "market",
            "data_domain",
            "normalized_payload",
            "quality_gate_status",
            "gate_status",
            "allowed_downstream",
        )
        if hasattr(value, key)
    }


def can_send_to_vectorbt(daily_bar_quality: Any) -> bool:
    return VECTORBT_DOWNSTREAM_NAME in _allowed_downstream(daily_bar_quality)


def build_vectorbt_input(
    evidence: Any,
    *,
    event_dates: list[str] | None = None,
    holding_period: int = 5,
) -> VectorBTValidationInput:
    data = _evidence_dict(evidence)
    if data.get("data_domain") != "daily_bar":
        raise ValueError("vectorbt adapter only accepts daily_bar ProviderEvidence.")
    if not can_send_to_vectorbt(data):
        raise ValueError("Daily bars are not allowed_downstream for vectorbt.")
    payload = data.get("normalized_payload", {})
    daily_bars = payload.get("daily_bars", []) if isinstance(payload, dict) else []
    return VectorBTValidationInput(
        ticker=str(data["ticker"]),
        market=str(data["market"]),
        daily_bars=[dict(item) for item in daily_bars],
        event_dates=[str(item) for item in (event_dates or [])],
        holding_period=int(holding_period),
        quality_gate_status=str(data.get("gate_status") or data.get("quality_gate_status") or ""),
    )


def parse_vectorbt_result(payload: dict[str, Any]) -> VectorBTValidationResult:
    return VectorBTValidationResult(
        ticker=str(payload.get("ticker", "")),
        market=str(payload.get("market", "")),
        status=str(payload.get("status", "")),
        metrics=dict(payload.get("metrics", {})),
        warnings=[str(item) for item in payload.get("warnings", [])],
        raw_payload=dict(payload),
    )
