#!/usr/bin/env python3
"""Run a minimal event validation baseline from DailyBarPanel.

This script writes ValidationEvidence only. It does not generate signals,
recommendations, confidence, portfolio backtests, or trading instructions.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.adapters.vectorbt_event_adapter import (  # noqa: E402
    attempt_vectorbt_event_validation,
    build_event_inputs_from_panel,
    inspect_vectorbt_availability,
)
from orchestrator.panels.daily_bar_panel import load_daily_bar_panel_csv, summarize_daily_bar_panel  # noqa: E402
from orchestrator.validation.ledger import append_validation  # noqa: E402
from orchestrator.validation.models import ValidationEvidence  # noqa: E402


PANEL_PATH = Path("outputs/panels/cn_daily_bar_panel.csv")
LEDGER_PATH = Path("outputs/validation/validation_evidence.jsonl")
REPORT_PATH = Path("outputs/reports/vectorbt_event_baseline.md")


def _status(pass_condition: bool, warn_condition: bool = False) -> str:
    if pass_condition:
        return "pass"
    if warn_condition:
        return "warn"
    return "block"


def _write_report(result: dict[str, Any], report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# vectorbt Event Baseline",
        "",
        f"- validation_run_status: {result['status']}",
        f"- validations_written: {result['validations_written']}",
        f"- ledger_path: {result['ledger_path']}",
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
            "- ValidationEvidence only; not signal/recommendation.",
            "- Does not run portfolio backtests.",
            "- Does not model trading costs.",
            "- Does not optimize strategy parameters.",
            "- Does not generate final confidence, LLM output, or trading actions.",
        ]
    )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _validation_from_result(
    *,
    run_id: str,
    event_input: Any,
    result: Any,
) -> ValidationEvidence:
    source = str(result.raw_payload.get("validation_source") or "fallback_event_baseline")
    quality_flags = sorted(set(event_input.quality_flags + result.warnings))
    gate_status = "warn" if quality_flags else "pass"
    return ValidationEvidence(
        validation_id=f"{run_id}:{event_input.ticker}:{event_input.event_date}:hp{event_input.holding_period}",
        run_id=run_id,
        market=event_input.market,
        ticker=event_input.ticker,
        event_date=event_input.event_date,
        validation_source=source,
        holding_period=event_input.holding_period,
        forward_return=result.forward_return,
        max_favorable_excursion=result.max_favorable_excursion,
        max_adverse_excursion=result.max_adverse_excursion,
        hit_take_profit=None,
        hit_stop_loss=None,
        provider_evidence_ids=[event_input.provider_evidence_id] if event_input.provider_evidence_id else [],
        panel_rows_used=result.rows_used,
        quality_flags=quality_flags,
        raw_payload=result.raw_payload,
        gate_status=gate_status,
        allowed_next_steps=["research"],
        notes="ValidationEvidence only; not a signal or recommendation.",
    )


def run_vectorbt_event_baseline(
    *,
    panel_path: str | Path = PANEL_PATH,
    ledger_path: str | Path = LEDGER_PATH,
    report_path: str | Path = REPORT_PATH,
    holding_period: int = 1,
) -> dict[str, Any]:
    panel_path = Path(panel_path)
    ledger_path = Path(ledger_path)
    panel_rows = load_daily_bar_panel_csv(panel_path)
    summary = summarize_daily_bar_panel(panel_rows)
    vectorbt_status = inspect_vectorbt_availability()
    event_inputs = build_event_inputs_from_panel(panel_path, holding_period=holding_period)
    run_id = f"vectorbt-event-baseline-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    validations_written = 0
    statuses: list[str] = []
    if ledger_path.exists():
        ledger_path.unlink()
    for event_input in event_inputs:
        result = attempt_vectorbt_event_validation(event_input)
        statuses.append(result.status)
        if result.status == "success":
            append_validation(_validation_from_result(run_id=run_id, event_input=event_input, result=result), ledger_path)
            validations_written += 1

    result_status = "success" if validations_written else ("partial" if event_inputs else "blocked")
    rows = [
        {
            "item": "panel_read",
            "status": _status(bool(panel_rows)),
            "detail": f"rows={summary['row_count']}; tickers={summary['ticker_count']}; date_range={summary['start_date'] or '-'} to {summary['end_date'] or '-'}",
        },
        {
            "item": "vectorbt_dependency",
            "status": "pass" if vectorbt_status["available"] else "warn",
            "detail": f"installed={vectorbt_status['available']}; version={vectorbt_status.get('version') or '-'}",
        },
        {
            "item": "event_inputs",
            "status": _status(bool(event_inputs), bool(panel_rows)),
            "detail": f"count={len(event_inputs)}",
        },
        {
            "item": "validations_written",
            "status": _status(validations_written > 0, bool(event_inputs)),
            "detail": f"count={validations_written}",
        },
        {
            "item": "boundary",
            "status": "-",
            "detail": "not signal/recommendation; ValidationEvidence only",
        },
    ]
    payload = {
        "status": result_status,
        "validations_written": validations_written,
        "ledger_path": str(ledger_path),
        "event_input_count": len(event_inputs),
        "statuses": statuses,
        "rows": rows,
    }
    _write_report(payload, Path(report_path))
    return payload


def main() -> int:
    result = run_vectorbt_event_baseline()
    print(f"validation_run_status: {result['status']}")
    print(f"validations_written: {result['validations_written']}")
    print(f"ledger: {result['ledger_path']}")
    print(f"report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
