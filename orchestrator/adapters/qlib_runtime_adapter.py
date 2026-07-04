"""Qlib runtime read validation adapter.

This module validates that the verified daily_bar panel is readable as a CSV
dataset and, when Qlib is already installed, records that the dependency can be
imported. It does not download data, initialize workflows, train models,
backtest, or generate signals.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from orchestrator.panels.daily_bar_panel import (
    PANEL_FIELDNAMES,
    REQUIRED_PANEL_FIELDS,
    load_daily_bar_panel_csv,
)


TRACEABILITY_FIELDS = ["provider_evidence_id", "quality_flags", "cross_source_status"]


@dataclass(slots=True)
class QlibRuntimeReadInput:
    panel_path: str
    market: str
    tickers: list[str]
    start_date: str
    end_date: str
    fields: list[str]
    row_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class QlibRuntimeReadResult:
    status: str
    qlib_available: bool
    panel_readable: bool
    rows_read: int
    tickers: list[str]
    date_range: tuple[str | None, str | None]
    warnings: list[str]
    next_action: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["date_range"] = tuple(self.date_range)
        return payload


def inspect_qlib_availability() -> dict[str, Any]:
    try:
        import qlib  # type: ignore[import-not-found]
    except ImportError as exc:
        return {"available": False, "version": None, "error": str(exc)}
    return {"available": True, "version": getattr(qlib, "__version__", "unknown"), "error": None}


def _header_fields(panel_path: Path) -> list[str]:
    if not panel_path.exists():
        return []
    with panel_path.open(encoding="utf-8", newline="") as handle:
        header = handle.readline().strip()
    return [field.strip() for field in header.split(",") if field.strip()]


def _missing_required_fields(panel_path: Path) -> list[str]:
    fields = set(_header_fields(panel_path))
    return [field for field in REQUIRED_PANEL_FIELDS if field not in fields]


def _missing_traceability_fields(panel_path: Path) -> list[str]:
    fields = set(_header_fields(panel_path))
    return [field for field in TRACEABILITY_FIELDS if field not in fields]


def _input_from_rows(panel_path: Path) -> QlibRuntimeReadInput | QlibRuntimeReadResult:
    if not panel_path.exists():
        return QlibRuntimeReadResult(
            status="blocked",
            qlib_available=False,
            panel_readable=False,
            rows_read=0,
            tickers=[],
            date_range=(None, None),
            warnings=["panel_missing"],
            next_action="build verified daily_bar panel before Qlib runtime read validation.",
        )
    missing = _missing_required_fields(panel_path)
    missing_traceability = _missing_traceability_fields(panel_path)
    if missing or missing_traceability:
        warnings = [f"missing_field:{field}" for field in missing]
        warnings.extend(f"missing_traceability_field:{field}" for field in missing_traceability)
        return QlibRuntimeReadResult(
            status="format_error",
            qlib_available=False,
            panel_readable=False,
            rows_read=0,
            tickers=[],
            date_range=(None, None),
            warnings=warnings,
            next_action="fix daily_bar panel schema before runtime validation.",
        )
    try:
        rows = load_daily_bar_panel_csv(panel_path)
    except Exception as exc:
        return QlibRuntimeReadResult(
            status="format_error",
            qlib_available=False,
            panel_readable=False,
            rows_read=0,
            tickers=[],
            date_range=(None, None),
            warnings=[f"panel_parse_error:{str(exc)[:240]}"],
            next_action="fix daily_bar panel CSV parse errors before runtime validation.",
        )
    if not rows:
        return QlibRuntimeReadResult(
            status="blocked",
            qlib_available=False,
            panel_readable=False,
            rows_read=0,
            tickers=[],
            date_range=(None, None),
            warnings=["panel_empty"],
            next_action="build non-empty verified daily_bar panel before runtime validation.",
        )
    dates = sorted({row.date for row in rows})
    tickers = sorted({row.ticker for row in rows})
    warnings: list[str] = []
    if len(tickers) < 2:
        warnings.append("single_ticker_panel")
    if len(dates) < 2:
        warnings.append("single_date_panel")
    return QlibRuntimeReadInput(
        panel_path=str(panel_path),
        market="CN",
        tickers=tickers,
        start_date=dates[0],
        end_date=dates[-1],
        fields=[field for field in PANEL_FIELDNAMES if field in _header_fields(panel_path)],
        row_count=len(rows),
    )


def build_qlib_runtime_read_input(panel_path: str | Path) -> QlibRuntimeReadInput | QlibRuntimeReadResult:
    return _input_from_rows(Path(panel_path))


def validate_panel_readable_without_qlib(panel_path: str | Path) -> QlibRuntimeReadResult:
    candidate = build_qlib_runtime_read_input(panel_path)
    if isinstance(candidate, QlibRuntimeReadResult):
        return candidate
    warnings: list[str] = []
    if len(candidate.tickers) < 2:
        warnings.append("single_ticker_panel")
    if candidate.start_date == candidate.end_date:
        warnings.append("single_date_panel")
    status = "success" if not warnings else "format_error"
    return QlibRuntimeReadResult(
        status=status,
        qlib_available=False,
        panel_readable=status == "success",
        rows_read=candidate.row_count,
        tickers=candidate.tickers,
        date_range=(candidate.start_date, candidate.end_date),
        warnings=warnings,
        next_action=(
            "install Qlib only if approved, then run minimal runtime read validation."
            if status == "success"
            else "complete multi-ticker, multi-date panel before runtime validation."
        ),
    )


def attempt_qlib_runtime_read(panel_path: str | Path) -> QlibRuntimeReadResult:
    csv_result = validate_panel_readable_without_qlib(panel_path)
    availability = inspect_qlib_availability()
    if not csv_result.panel_readable:
        return QlibRuntimeReadResult(
            status=csv_result.status,
            qlib_available=bool(availability["available"]),
            panel_readable=False,
            rows_read=csv_result.rows_read,
            tickers=csv_result.tickers,
            date_range=csv_result.date_range,
            warnings=csv_result.warnings,
            next_action=csv_result.next_action,
        )
    if not availability["available"]:
        return QlibRuntimeReadResult(
            status="dependency_missing",
            qlib_available=False,
            panel_readable=True,
            rows_read=csv_result.rows_read,
            tickers=csv_result.tickers,
            date_range=csv_result.date_range,
            warnings=csv_result.warnings + ["qlib_dependency_missing"],
            next_action="install Qlib only if explicitly approved; then rerun runtime read validation.",
        )
    return QlibRuntimeReadResult(
        status="success",
        qlib_available=True,
        panel_readable=True,
        rows_read=csv_result.rows_read,
        tickers=csv_result.tickers,
        date_range=csv_result.date_range,
        warnings=csv_result.warnings,
        next_action="design Qlib minimal experiment input; do not train models until separately approved.",
    )
