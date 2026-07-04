"""Domain-level quality gates for ProviderEvidence."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class DomainGateDecision:
    status: str
    reasons: list[str] = field(default_factory=list)
    blocked_fields: list[str] = field(default_factory=list)
    warning_fields: list[str] = field(default_factory=list)
    allowed_downstream: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reasons": list(self.reasons),
            "blocked_fields": list(self.blocked_fields),
            "warning_fields": list(self.warning_fields),
            "allowed_downstream": list(self.allowed_downstream),
        }


def _get(payload: Any, key: str, default: Any = None) -> Any:
    if isinstance(payload, dict):
        return payload.get(key, default)
    return getattr(payload, key, default)


def _flags(payload: Any) -> list[str]:
    values = _get(payload, "quality_flags", []) or []
    return [str(item) for item in values]


def _normalized_payload(payload: Any) -> dict[str, Any]:
    value = _get(payload, "normalized_payload", {}) or {}
    return dict(value) if isinstance(value, dict) else {}


def _has_zero_price_diff(payload: dict[str, Any]) -> bool:
    diffs = payload.get("price_diff_pct", {})
    if not isinstance(diffs, dict) or not diffs:
        return False
    price_fields = ("open", "high", "low", "close")
    values: list[float] = []
    for field in price_fields:
        if field in diffs:
            try:
                values.append(abs(float(diffs[field])))
            except (TypeError, ValueError):
                return False
    return bool(values) and all(value == 0 for value in values)


def _has_mismatch(payload: dict[str, Any], *keys: str) -> bool:
    for key in keys:
        values = payload.get(key, {})
        if not isinstance(values, dict):
            continue
        for value in values.values():
            try:
                if abs(float(value)) > 0:
                    return True
            except (TypeError, ValueError):
                continue
    return False


def _decision(
    *,
    status: str,
    reasons: list[str],
    blocked_fields: list[str] | None = None,
    warning_fields: list[str] | None = None,
    allowed_downstream: list[str] | None = None,
) -> DomainGateDecision:
    return DomainGateDecision(
        status=status,
        reasons=sorted(set(reasons)),
        blocked_fields=sorted(set(blocked_fields or [])),
        warning_fields=sorted(set(warning_fields or [])),
        allowed_downstream=sorted(set(allowed_downstream or [])),
    )


def evaluate_evidence_domain(evidence_payload: Any) -> DomainGateDecision:
    domain = str(_get(evidence_payload, "data_domain", ""))
    cross_source_status = str(_get(evidence_payload, "cross_source_status", "unchecked"))
    flags = _flags(evidence_payload)
    payload = _normalized_payload(evidence_payload)
    reasons: list[str] = []
    blocked_fields: list[str] = []
    warning_fields: list[str] = []

    if any(flag.startswith("pending_credentials") or flag.startswith("needs_credentials") for flag in flags):
        return _decision(status="pending_credentials", reasons=["credentials are pending"])

    if domain == "daily_bar":
        if any(flag == "provider_error" or flag.startswith("provider_error") for flag in flags):
            reasons.append("provider_error")
            blocked_fields.append("provider")
        for required in ("close", "date"):
            if f"missing_field:{required}" in flags or f"missing_field:{required}_parse" in flags:
                reasons.append(f"missing required daily_bar field: {required}")
                blocked_fields.append(required)
        if cross_source_status == "mismatch" or _has_mismatch(payload, "price_diff_pct"):
            reasons.append("cross-source price mismatch")
            blocked_fields.append("price")
        for flag in flags:
            if flag.startswith("unit_unverified:") or flag.startswith("adjustment_unverified:"):
                reasons.append(flag)
                warning_fields.append(flag.split(":", 1)[1])
        if blocked_fields:
            return _decision(
                status="block",
                reasons=reasons,
                blocked_fields=blocked_fields,
                warning_fields=warning_fields,
            )
        allowed = ["vectorbt"]
        if warning_fields:
            allowed.append("alphasift_exploratory")
            status = "warn"
        elif cross_source_status == "matched" or (
            cross_source_status == "partial_success" and _has_zero_price_diff(payload)
        ):
            allowed.append("alphasift_exploratory")
            status = "pass"
        else:
            status = "warn"
            reasons.append(f"cross_source_status:{cross_source_status}")
        return _decision(
            status=status,
            reasons=reasons,
            warning_fields=warning_fields,
            allowed_downstream=allowed,
        )

    if domain == "valuation":
        if any(flag == "provider_error" or flag.startswith("provider_error") for flag in flags):
            return _decision(
                status="block",
                reasons=["provider_error"],
                blocked_fields=["provider"],
                allowed_downstream=[],
            )
        for flag in flags:
            if flag.startswith("asof_mismatch:"):
                reasons.append(flag)
                warning_fields.append("asof_mismatch")
            elif flag.startswith("estimated_value:dividend_yield"):
                reasons.append(flag)
                warning_fields.append("dividend_yield")
            elif flag == "missing_field:fcf_yield" or flag.endswith(":fcf_yield"):
                reasons.append(flag)
                warning_fields.append("fcf_yield")
        return _decision(
            status="warn" if warning_fields else "pass",
            reasons=reasons,
            warning_fields=warning_fields,
            allowed_downstream=["research_evidence"],
        )

    if domain == "fundamentals":
        if any(flag.startswith("pending_credentials") for flag in flags):
            return _decision(status="pending_credentials", reasons=["credentials are pending"])
        if any(
            flag == "provider_error"
            or flag.startswith("provider_error")
            or "permission" in flag.lower()
            or "权限" in flag
            for flag in flags
        ):
            return _decision(
                status="block",
                reasons=["provider_error_or_permission_error"],
                blocked_fields=["provider"],
            )
        return _decision(status="pass", reasons=[], allowed_downstream=["research_evidence"])

    if domain in {"event", "news"}:
        return _decision(status="pending_credentials", reasons=[f"{domain} evidence not implemented"])

    return _decision(status="block", reasons=[f"unsupported data_domain:{domain}"], blocked_fields=["data_domain"])


def allowed_downstream_for_evidence(evidence: Any) -> list[str]:
    existing = _get(evidence, "allowed_downstream", None)
    if existing:
        return [str(item) for item in existing]
    return evaluate_evidence_domain(evidence).allowed_downstream
