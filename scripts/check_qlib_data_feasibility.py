#!/usr/bin/env python3
"""Check whether ProviderEvidence can feed a future Qlib panel dataset."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.adapters.qlib_adapter import (  # noqa: E402
    REQUIRED_DAILY_BAR_FIELDS,
    build_qlib_format_input,
    can_send_to_qlib,
    evaluate_qlib_data_format_feasibility,
)
from orchestrator.evidence.ledger import load_evidence  # noqa: E402


EVIDENCE_PATH = Path("outputs/evidence/provider_evidence.jsonl")
REPORT_PATH = Path("outputs/reports/qlib_data_feasibility.md")


def _status(pass_condition: bool, warn_condition: bool = False) -> str:
    if pass_condition:
        return "pass"
    if warn_condition:
        return "warn"
    return "block"


def _has_complete_daily_bars(evidence_rows: list[Any]) -> bool:
    for row in evidence_rows:
        payload = row.normalized_payload if hasattr(row, "normalized_payload") else row.get("normalized_payload", {})
        bars = payload.get("daily_bars", []) if isinstance(payload, dict) else []
        if not bars:
            return False
        if len(bars) < 2:
            return False
        for bar in bars:
            if any(field not in bar or bar.get(field) in (None, "") for field in REQUIRED_DAILY_BAR_FIELDS):
                return False
    return bool(evidence_rows)


def _write_report(result: dict[str, Any], report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Qlib Data Feasibility",
        "",
        f"- feasibility_status: {result['feasibility_status']}",
        f"- qlib_runtime_ready: {result['qlib_runtime_ready']}",
        f"- eligible_daily_bar_count: {result['eligible_daily_bar_count']}",
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
            "- Does not run Qlib.",
            "- Does not install Qlib.",
            "- Does not train models.",
            "- Does not generate CandidateEvidence.",
            "- Does not generate recommendations, final signals, confidence, LLM output, or trading actions.",
        ]
    )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_qlib_data_feasibility(
    *,
    evidence_path: str | Path = EVIDENCE_PATH,
    report_path: str | Path = REPORT_PATH,
) -> dict[str, Any]:
    evidence_rows = load_evidence(evidence_path)
    cn_daily_rows = [
        row
        for row in evidence_rows
        if row.market == "CN" and row.data_domain == "daily_bar" and can_send_to_qlib(row)
    ]
    feasibility = evaluate_qlib_data_format_feasibility(cn_daily_rows)
    full_panel = _has_complete_daily_bars(cn_daily_rows)
    multi_ticker = len({row.ticker for row in cn_daily_rows}) >= 2
    try:
        adapter_input = build_qlib_format_input(cn_daily_rows)
        field_detail = ", ".join(adapter_input.fields)
    except ValueError:
        field_detail = "no eligible fields"
    qlib_ready = feasibility.status == "feasible"
    rows = [
        {
            "item": "eligible_daily_bar_evidence",
            "status": _status(bool(cn_daily_rows)),
            "detail": f"count={len(cn_daily_rows)}",
        },
        {
            "item": "required_fields",
            "status": _status(not feasibility.missing_fields, bool(feasibility.available_fields)),
            "detail": f"required={','.join(REQUIRED_DAILY_BAR_FIELDS)}; available={field_detail}; missing={','.join(feasibility.missing_fields) or 'none'}",
        },
        {
            "item": "time_series_panel",
            "status": _status(full_panel, bool(cn_daily_rows)),
            "detail": "complete daily_bars panel present" if full_panel else "complete daily_bars panel missing; current evidence is summary-level",
        },
        {
            "item": "multi_ticker_panel",
            "status": _status(multi_ticker, bool(cn_daily_rows)),
            "detail": f"tickers={len({row.ticker for row in cn_daily_rows})}",
        },
        {
            "item": "qlib_runtime_ready",
            "status": "pass" if qlib_ready else "block",
            "detail": "yes" if qlib_ready else "no",
        },
        {
            "item": "next_action",
            "status": "-",
            "detail": feasibility.next_action,
        },
    ]
    result = {
        "feasibility_status": feasibility.status,
        "qlib_runtime_ready": "yes" if qlib_ready else "no",
        "eligible_daily_bar_count": len(cn_daily_rows),
        "rows": rows,
        "warnings": feasibility.warnings,
        "missing_fields": feasibility.missing_fields,
    }
    _write_report(result, Path(report_path))
    return result


def main() -> int:
    result = check_qlib_data_feasibility()
    print(f"feasibility_status: {result['feasibility_status']}")
    print(f"qlib_runtime_ready: {result['qlib_runtime_ready']}")
    print(f"eligible_daily_bar_count: {result['eligible_daily_bar_count']}")
    print(f"report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
