#!/usr/bin/env python3
"""Validate Qlib-compatible runtime read readiness for DailyBarPanel."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.adapters.qlib_runtime_adapter import (  # noqa: E402
    QlibRuntimeReadResult,
    TRACEABILITY_FIELDS,
    attempt_qlib_runtime_read,
    build_qlib_runtime_read_input,
    inspect_qlib_availability,
)
from orchestrator.panels.daily_bar_panel import REQUIRED_PANEL_FIELDS  # noqa: E402


PANEL_PATH = Path("outputs/panels/cn_daily_bar_panel.csv")
REPORT_PATH = Path("outputs/reports/qlib_runtime_read_validation.md")


def _status(pass_condition: bool, warn_condition: bool = False) -> str:
    if pass_condition:
        return "pass"
    if warn_condition:
        return "warn"
    return "block"


def _write_report(result: dict[str, Any], report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Qlib Runtime Read Validation",
        "",
        f"- qlib_runtime_read: {result['qlib_runtime_read']}",
        f"- qlib_available: {result['qlib_available']}",
        f"- panel_readable: {result['panel_readable']}",
        f"- rows_read: {result['rows_read']}",
        "",
        "| item | status | detail |",
        "|---|---|---|",
    ]
    for row in result["rows"]:
        lines.append("| {item} | {status} | {detail} |".format(**row))
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- Does not install Qlib.",
            "- Does not download Qlib data.",
            "- Does not initialize Qlib workflows.",
            "- Does not train models.",
            "- Does not run backtests.",
            "- Does not generate CandidateEvidence.",
            "- Does not generate recommendations, final signals, confidence, LLM output, or trading actions.",
        ]
    )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_qlib_runtime_read(
    *,
    panel_path: str | Path = PANEL_PATH,
    report_path: str | Path = REPORT_PATH,
) -> dict[str, Any]:
    panel_path = Path(panel_path)
    input_or_error = build_qlib_runtime_read_input(panel_path)
    result = attempt_qlib_runtime_read(panel_path)
    availability = inspect_qlib_availability()
    missing_required = [warning.split(":", 1)[1] for warning in result.warnings if warning.startswith("missing_field:")]
    missing_traceability = [
        warning.split(":", 1)[1] for warning in result.warnings if warning.startswith("missing_traceability_field:")
    ]
    if isinstance(input_or_error, QlibRuntimeReadResult):
        tickers = input_or_error.tickers
        date_range = input_or_error.date_range
    else:
        tickers = input_or_error.tickers
        date_range = (input_or_error.start_date, input_or_error.end_date)

    rows = [
        {
            "item": "panel_exists",
            "status": _status(panel_path.exists()),
            "detail": str(panel_path),
        },
        {
            "item": "panel_schema",
            "status": _status(not missing_required),
            "detail": f"required={','.join(REQUIRED_PANEL_FIELDS)}; missing={','.join(missing_required) or 'none'}",
        },
        {
            "item": "panel_shape",
            "status": _status(result.panel_readable, result.rows_read > 0),
            "detail": f"rows={result.rows_read}; tickers={len(tickers)}; date_range={date_range[0] or '-'} to {date_range[1] or '-'}",
        },
        {
            "item": "traceability_fields",
            "status": _status(not missing_traceability),
            "detail": f"required={','.join(TRACEABILITY_FIELDS)}; missing={','.join(missing_traceability) or 'none'}",
        },
        {
            "item": "qlib_dependency",
            "status": "pass" if availability["available"] else "warn",
            "detail": f"installed={availability['available']}; version={availability.get('version') or '-'}",
        },
        {
            "item": "qlib_runtime_read",
            "status": result.status,
            "detail": "; ".join(result.warnings) or "qlib import and panel read succeeded",
        },
        {
            "item": "next_action",
            "status": "-",
            "detail": result.next_action,
        },
    ]
    payload = {
        "qlib_runtime_read": result.status,
        "qlib_available": result.qlib_available,
        "panel_readable": result.panel_readable,
        "rows_read": result.rows_read,
        "tickers": result.tickers,
        "date_range": result.date_range,
        "warnings": result.warnings,
        "rows": rows,
    }
    _write_report(payload, Path(report_path))
    return payload


def main() -> int:
    result = validate_qlib_runtime_read()
    print(f"qlib_runtime_read: {result['qlib_runtime_read']}")
    print(f"qlib_available: {result['qlib_available']}")
    print(f"panel_readable: {result['panel_readable']}")
    print(f"rows_read: {result['rows_read']}")
    print(f"report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
