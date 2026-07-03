"""Data quality gates for provider evidence and cross-source checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable


@dataclass(slots=True)
class DataQualityDecision:
    status: str
    reasons: list[str] = field(default_factory=list)
    blocked_fields: list[str] = field(default_factory=list)
    warning_fields: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reasons": list(self.reasons),
            "blocked_fields": list(self.blocked_fields),
            "warning_fields": list(self.warning_fields),
        }


def _flags(record_or_flags: Any) -> list[str]:
    if record_or_flags is None:
        return []
    if isinstance(record_or_flags, dict):
        values = record_or_flags.get("quality_flags", record_or_flags.get("flags", []))
    elif isinstance(record_or_flags, (list, tuple, set)):
        values = record_or_flags
    else:
        values = getattr(record_or_flags, "quality_flags", [])
    return [str(item) for item in values]


def _field_suffix(flag: str) -> str:
    return flag.split(":", 1)[1] if ":" in flag else flag


def _evaluate_flags(record_or_flags: Any, *, valuation: bool = False) -> DataQualityDecision:
    flags = _flags(record_or_flags)
    reasons: list[str] = []
    blocked_fields: list[str] = []
    warning_fields: list[str] = []
    if any(flag == "provider_error" or flag.startswith("provider_error:") for flag in flags):
        reasons.append("provider_error")
        blocked_fields.append("provider")
    if "pending_credentials" in flags or any(flag.startswith("needs_credentials") for flag in flags):
        return DataQualityDecision(
            status="pending_credentials",
            reasons=["Tushare credentials are missing"],
            blocked_fields=[],
            warning_fields=[],
        )

    for required in ("close", "date"):
        if f"missing_field:{required}" in flags or f"missing_field:{required}_parse" in flags:
            reasons.append(f"missing required field: {required}")
            blocked_fields.append(required)

    warning_prefixes = (
        "source_date_unverified:",
        "asof_mismatch:",
        "unit_unverified:",
        "adjustment_unverified:",
        "estimated_value:",
        "partial_coverage:",
    )
    for flag in flags:
        if flag == "missing_field:market_cap":
            warning_fields.append("market_cap")
            reasons.append("market_cap is missing")
        elif flag == "missing_field:fcf_yield":
            warning_fields.append("fcf_yield")
            reasons.append("fcf_yield is missing")
        elif flag.startswith(warning_prefixes):
            field = _field_suffix(flag)
            warning_fields.append(field)
            reasons.append(flag)

    if valuation and any(flag.startswith("asof_mismatch:") for flag in flags):
        reasons.append("valuation as-of mismatch blocks production strategy use")

    status = "block" if blocked_fields else ("warn" if warning_fields or reasons else "pass")
    return DataQualityDecision(
        status=status,
        reasons=sorted(set(reasons)),
        blocked_fields=sorted(set(blocked_fields)),
        warning_fields=sorted(set(warning_fields)),
    )


def evaluate_daily_bar_quality(record_or_flags: Any) -> DataQualityDecision:
    return _evaluate_flags(record_or_flags)


def evaluate_valuation_quality(record_or_flags: Any) -> DataQualityDecision:
    return _evaluate_flags(record_or_flags, valuation=True)


def _max_abs(values: Iterable[Any]) -> float:
    parsed: list[float] = []
    for value in values:
        try:
            if value is not None:
                parsed.append(abs(float(value)))
        except (TypeError, ValueError):
            continue
    return max(parsed) if parsed else 0.0


def evaluate_cross_source_comparison(comparison_payload: dict[str, Any]) -> DataQualityDecision:
    status = str(comparison_payload.get("status", ""))
    if status == "pending_credentials" or comparison_payload.get("pending_credentials"):
        return DataQualityDecision(
            status="pending_credentials",
            reasons=["Tushare credentials are missing"],
        )

    decision = _evaluate_flags(comparison_payload)
    reasons = list(decision.reasons)
    blocked_fields = list(decision.blocked_fields)
    warning_fields = list(decision.warning_fields)

    price_threshold_pct = float(comparison_payload.get("price_diff_threshold_pct", 1.0))
    volume_threshold_pct = float(comparison_payload.get("volume_diff_threshold_pct", 5.0))
    amount_threshold_pct = float(comparison_payload.get("amount_diff_threshold_pct", 5.0))
    valuation_threshold_pct = float(comparison_payload.get("valuation_diff_threshold_pct", 5.0))

    if _max_abs(comparison_payload.get("price_diff_pct", {}).values()) > price_threshold_pct:
        reasons.append("cross-source price difference exceeds threshold")
        blocked_fields.append("price")
    if _max_abs(comparison_payload.get("volume_diff_pct", {}).values()) > volume_threshold_pct:
        reasons.append("cross-source volume difference exceeds threshold")
        warning_fields.append("volume")
    if _max_abs(comparison_payload.get("amount_diff_pct", {}).values()) > amount_threshold_pct:
        reasons.append("cross-source amount difference exceeds threshold")
        warning_fields.append("amount")
    if _max_abs(comparison_payload.get("valuation_diff_pct", {}).values()) > valuation_threshold_pct:
        reasons.append("cross-source valuation difference exceeds threshold")
        warning_fields.append("valuation")

    final_status = "block" if blocked_fields else ("warn" if warning_fields or reasons else "pass")
    return DataQualityDecision(
        status=final_status,
        reasons=sorted(set(reasons)),
        blocked_fields=sorted(set(blocked_fields)),
        warning_fields=sorted(set(warning_fields)),
    )
