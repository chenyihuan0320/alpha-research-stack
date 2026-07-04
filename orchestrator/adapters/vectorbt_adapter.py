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


def can_send_to_vectorbt(daily_bar_quality: Any) -> bool:
    return VECTORBT_DOWNSTREAM_NAME in _allowed_downstream(daily_bar_quality)


def build_vectorbt_input(
    *,
    ticker: str,
    market: str,
    daily_bars: list[dict[str, Any]],
    event_dates: list[str],
    holding_period: int,
    quality_gate_status: str,
) -> VectorBTValidationInput:
    if not can_send_to_vectorbt(
        {
            "quality_gate_status": quality_gate_status,
            "allowed_downstream": ["vectorbt"] if quality_gate_status not in {"block", "pending_credentials"} else [],
        }
    ):
        raise ValueError("Daily bars are not allowed_downstream for vectorbt.")
    return VectorBTValidationInput(
        ticker=ticker,
        market=market,
        daily_bars=[dict(item) for item in daily_bars],
        event_dates=[str(item) for item in event_dates],
        holding_period=int(holding_period),
        quality_gate_status=quality_gate_status,
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
