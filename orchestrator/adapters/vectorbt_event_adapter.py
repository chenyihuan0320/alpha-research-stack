"""vectorbt event validation baseline adapter.

This adapter optionally detects vectorbt, but the current baseline only computes
simple event-window forward return, MFE, and MAE. It does not run a portfolio
backtest, optimize parameters, model costs, produce signals, or rank stocks.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from orchestrator.panels.daily_bar_panel import DailyBarPanelRow, load_daily_bar_panel_csv


@dataclass(slots=True)
class EventValidationInput:
    panel_path: str
    market: str
    ticker: str
    event_date: str
    holding_period: int
    provider_evidence_id: str
    quality_flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class EventValidationResult:
    status: str
    forward_return: float | None
    max_favorable_excursion: float | None
    max_adverse_excursion: float | None
    rows_used: int
    warnings: list[str] = field(default_factory=list)
    raw_payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def inspect_vectorbt_availability() -> dict[str, Any]:
    try:
        import vectorbt as vbt  # type: ignore[import-not-found]
    except ImportError as exc:
        return {"available": False, "version": None, "error": str(exc)}
    return {"available": True, "version": getattr(vbt, "__version__", "unknown"), "error": None}


def _rows_for_ticker(panel_rows: list[DailyBarPanelRow], ticker: str) -> list[DailyBarPanelRow]:
    return sorted([row for row in panel_rows if row.ticker == ticker], key=lambda row: row.date)


def build_event_inputs_from_panel(
    panel_path: str | Path,
    *,
    holding_period: int = 1,
) -> list[EventValidationInput]:
    panel_path = Path(panel_path)
    rows = load_daily_bar_panel_csv(panel_path)
    inputs: list[EventValidationInput] = []
    for ticker in sorted({row.ticker for row in rows}):
        ticker_rows = _rows_for_ticker(rows, ticker)
        if len(ticker_rows) <= holding_period:
            continue
        event_row = ticker_rows[-(holding_period + 1)]
        quality_flags = sorted({flag for row in ticker_rows for flag in row.quality_flags})
        provider_evidence_ids = sorted({row.provider_evidence_id for row in ticker_rows if row.provider_evidence_id})
        inputs.append(
            EventValidationInput(
                panel_path=str(panel_path),
                market=event_row.market,
                ticker=ticker,
                event_date=event_row.date,
                holding_period=holding_period,
                provider_evidence_id=provider_evidence_ids[0] if provider_evidence_ids else "",
                quality_flags=quality_flags,
            )
        )
    return inputs


def validate_event_with_fallback(
    panel_rows: list[DailyBarPanelRow],
    event_date: str,
    holding_period: int,
) -> EventValidationResult:
    rows = sorted(panel_rows, key=lambda row: row.date)
    event_index = next((idx for idx, row in enumerate(rows) if row.date == event_date), None)
    if event_index is None:
        return EventValidationResult(
            status="format_error",
            forward_return=None,
            max_favorable_excursion=None,
            max_adverse_excursion=None,
            rows_used=0,
            warnings=["event_date_not_found"],
            raw_payload={"event_date": event_date},
        )
    end_index = event_index + holding_period
    if end_index >= len(rows):
        return EventValidationResult(
            status="insufficient_history",
            forward_return=None,
            max_favorable_excursion=None,
            max_adverse_excursion=None,
            rows_used=len(rows) - event_index,
            warnings=["insufficient_history"],
            raw_payload={"event_date": event_date, "holding_period": holding_period},
        )
    window = rows[event_index : end_index + 1]
    start_close = window[0].close
    end_close = window[-1].close
    if start_close == 0:
        return EventValidationResult(
            status="format_error",
            forward_return=None,
            max_favorable_excursion=None,
            max_adverse_excursion=None,
            rows_used=len(window),
            warnings=["zero_start_close"],
            raw_payload={"event_date": event_date, "holding_period": holding_period},
        )
    forward_return = (end_close / start_close) - 1.0
    mfe = max((row.high / start_close) - 1.0 for row in window[1:])
    mae = min((row.low / start_close) - 1.0 for row in window[1:])
    return EventValidationResult(
        status="success",
        forward_return=forward_return,
        max_favorable_excursion=mfe,
        max_adverse_excursion=mae,
        rows_used=len(window),
        warnings=[],
        raw_payload={
            "event_date": event_date,
            "holding_period": holding_period,
            "close_start": start_close,
            "close_end": end_close,
            "validation_source": "fallback_event_baseline",
        },
    )


def attempt_vectorbt_event_validation(event_input: EventValidationInput) -> EventValidationResult:
    availability = inspect_vectorbt_availability()
    rows = _rows_for_ticker(load_daily_bar_panel_csv(event_input.panel_path), event_input.ticker)
    result = validate_event_with_fallback(rows, event_input.event_date, event_input.holding_period)
    warnings = list(result.warnings)
    validation_source = "vectorbt" if availability["available"] else "fallback_event_baseline"
    if not availability["available"]:
        warnings.append("vectorbt_dependency_missing")
    raw_payload = dict(result.raw_payload)
    raw_payload["validation_source"] = validation_source
    raw_payload["vectorbt_available"] = availability["available"]
    return EventValidationResult(
        status=result.status,
        forward_return=result.forward_return,
        max_favorable_excursion=result.max_favorable_excursion,
        max_adverse_excursion=result.max_adverse_excursion,
        rows_used=result.rows_used,
        warnings=warnings,
        raw_payload=raw_payload,
    )
