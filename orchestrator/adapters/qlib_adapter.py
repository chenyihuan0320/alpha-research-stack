"""Qlib data format feasibility adapter.

This module does not import or run Qlib. It only checks whether ProviderEvidence
contains enough daily_bar panel data to prepare a future Qlib runtime input.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable


REQUIRED_DAILY_BAR_FIELDS = ["date", "ticker", "open", "high", "low", "close", "volume"]
OPTIONAL_DAILY_BAR_FIELDS = [
    "amount",
    "factor",
    "vwap",
    "turnover",
    "adj_factor",
    "industry",
    "market_cap",
    "label",
]
QLIB_ALLOWED_DOWNSTREAM = {"vectorbt", "alphasift", "alphasift_exploratory"}


@dataclass(slots=True)
class QlibDataFormatInput:
    run_id: str
    market: str
    tickers: list[str]
    fields: list[str]
    frequency: str
    provider_evidence_ids: list[str]
    quality_gate_statuses: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class QlibDataFormatResult:
    status: str
    required_fields: list[str]
    available_fields: list[str]
    missing_fields: list[str]
    warnings: list[str]
    next_action: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _field(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _payload(value: Any) -> dict[str, Any]:
    payload = _field(value, "normalized_payload", {})
    return payload if isinstance(payload, dict) else {}


def _allowed_downstream(value: Any) -> set[str]:
    return {str(item) for item in (_field(value, "allowed_downstream", []) or [])}


def can_send_to_qlib(evidence: Any) -> bool:
    return (
        _field(evidence, "data_domain") == "daily_bar"
        and bool(_allowed_downstream(evidence) & QLIB_ALLOWED_DOWNSTREAM)
    )


def _eligible_rows(evidence_rows: Iterable[Any]) -> list[Any]:
    return [row for row in evidence_rows if can_send_to_qlib(row)]


def _daily_bars(row: Any) -> list[dict[str, Any]]:
    items = _payload(row).get("daily_bars", [])
    if not isinstance(items, list):
        return []
    return [dict(item) for item in items if isinstance(item, dict)]


def _available_fields(rows: list[Any]) -> list[str]:
    fields: set[str] = set()
    for row in rows:
        if _field(row, "ticker", ""):
            fields.add("ticker")
        if _field(row, "observed_at", None) or _field(row, "source_updated_at", None):
            fields.add("date")
        bars = _daily_bars(row)
        if bars:
            for bar in bars:
                fields.update(str(key) for key in bar)
        else:
            compared = _payload(row).get("compared_fields", [])
            if isinstance(compared, list):
                fields.update(str(item) for item in compared)
            raw_mapping = _field(row, "raw_field_mapping", {})
            if isinstance(raw_mapping, dict):
                for provider_mapping in raw_mapping.values():
                    if isinstance(provider_mapping, dict):
                        fields.update(str(key) for key in provider_mapping)
    return [field for field in REQUIRED_DAILY_BAR_FIELDS + OPTIONAL_DAILY_BAR_FIELDS if field in fields]


def _has_complete_panel(rows: list[Any]) -> bool:
    if not rows:
        return False
    tickers_with_panel = set()
    for row in rows:
        bars = _daily_bars(row)
        if not bars:
            return False
        if len(bars) < 2:
            return False
        for bar in bars:
            if any(field not in bar or bar.get(field) in (None, "") for field in REQUIRED_DAILY_BAR_FIELDS):
                return False
        tickers_with_panel.add(str(_field(row, "ticker", "")))
    return bool(tickers_with_panel)


def build_qlib_format_input(evidence_rows: Iterable[Any]) -> QlibDataFormatInput:
    rows = _eligible_rows(evidence_rows)
    if not rows:
        raise ValueError("No eligible daily_bar ProviderEvidence rows for Qlib feasibility.")
    return QlibDataFormatInput(
        run_id=str(_field(rows[0], "run_id", "")),
        market=str(_field(rows[0], "market", "")),
        tickers=sorted({str(_field(row, "ticker", "")) for row in rows if _field(row, "ticker", "")}),
        fields=_available_fields(rows),
        frequency="day",
        provider_evidence_ids=[str(_field(row, "evidence_id", "")) for row in rows],
        quality_gate_statuses=sorted({str(_field(row, "gate_status", "")) for row in rows if _field(row, "gate_status", "")}),
    )


def evaluate_qlib_data_format_feasibility(evidence_rows: Iterable[Any]) -> QlibDataFormatResult:
    rows = _eligible_rows(evidence_rows)
    if not rows:
        return QlibDataFormatResult(
            status="blocked",
            required_fields=list(REQUIRED_DAILY_BAR_FIELDS),
            available_fields=[],
            missing_fields=list(REQUIRED_DAILY_BAR_FIELDS),
            warnings=["no_eligible_daily_bar_evidence"],
            next_action="build verified daily_bar ProviderEvidence before Qlib feasibility.",
        )

    available = _available_fields(rows)
    missing = [field for field in REQUIRED_DAILY_BAR_FIELDS if field not in available]
    warnings: list[str] = []
    if not _has_complete_panel(rows):
        warnings.append("time_series_panel_missing")

    if not missing and not warnings:
        status = "feasible"
        next_action = "Proceed to Qlib minimal runtime validation without training models."
    elif "time_series_panel_missing" in warnings and not missing:
        status = "partial"
        next_action = "build verified daily_bar panel before Qlib runtime validation."
    else:
        status = "blocked"
        next_action = "build verified daily_bar panel with required OHLCV fields before Qlib runtime validation."

    return QlibDataFormatResult(
        status=status,
        required_fields=list(REQUIRED_DAILY_BAR_FIELDS),
        available_fields=available,
        missing_fields=missing,
        warnings=warnings,
        next_action=next_action,
    )
