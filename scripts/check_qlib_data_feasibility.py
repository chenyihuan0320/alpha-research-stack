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
from orchestrator.panels.daily_bar_panel import (  # noqa: E402
    load_daily_bar_panel_csv,
    summarize_daily_bar_panel,
)


EVIDENCE_PATH = Path("outputs/evidence/provider_evidence.jsonl")
PANEL_PATH = Path("outputs/panels/cn_daily_bar_panel.csv")
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


def _has_complete_panel_csv(panel_path: Path) -> bool:
    rows = load_daily_bar_panel_csv(panel_path)
    if not rows:
        return False
    ticker_count = len({row.ticker for row in rows})
    date_count = len({row.date for row in rows})
    if ticker_count < 2 or date_count < 2:
        return False
    for row in rows:
        payload = row.to_dict()
        if any(payload.get(field) in (None, "") for field in REQUIRED_DAILY_BAR_FIELDS):
            return False
    return True


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
    panel_path: str | Path = PANEL_PATH,
    report_path: str | Path = REPORT_PATH,
) -> dict[str, Any]:
    evidence_rows = load_evidence(evidence_path)
    cn_daily_rows = [
        row
        for row in evidence_rows
        if row.market == "CN" and row.data_domain == "daily_bar" and can_send_to_qlib(row)
    ]
    feasibility = evaluate_qlib_data_format_feasibility(cn_daily_rows)
    panel_path = Path(panel_path)
    panel_rows = load_daily_bar_panel_csv(panel_path)
    panel_summary = summarize_daily_bar_panel(panel_rows)
    panel_complete = _has_complete_panel_csv(panel_path)
    full_panel = panel_complete or _has_complete_daily_bars(cn_daily_rows)
    multi_ticker = len({row.ticker for row in cn_daily_rows}) >= 2
    if panel_rows:
        multi_ticker = panel_summary["ticker_count"] >= 2
    try:
        adapter_input = build_qlib_format_input(cn_daily_rows)
        field_detail = ", ".join(adapter_input.fields)
    except ValueError:
        field_detail = "no eligible fields"
    if panel_rows:
        available_fields = [field for field in REQUIRED_DAILY_BAR_FIELDS if all(getattr(row, field) not in (None, "") for row in panel_rows)]
        missing_fields = [field for field in REQUIRED_DAILY_BAR_FIELDS if field not in available_fields]
        field_detail = ", ".join(available_fields)
        feasibility_status = "feasible" if panel_complete and not missing_fields else "partial"
        qlib_ready = panel_complete and not missing_fields
        next_action = (
            "Proceed to Qlib minimal runtime validation without training models."
            if qlib_ready
            else "complete verified daily_bar panel before Qlib runtime validation."
        )
        missing_detail = ",".join(missing_fields) or "none"
    else:
        feasibility_status = feasibility.status
        qlib_ready = feasibility.status == "feasible"
        next_action = feasibility.next_action
        missing_detail = ",".join(feasibility.missing_fields) or "none"
    rows = [
        {
            "item": "eligible_daily_bar_evidence",
            "status": _status(bool(cn_daily_rows)),
            "detail": f"count={len(cn_daily_rows)}",
        },
        {
            "item": "required_fields",
            "status": _status(missing_detail == "none", field_detail != "no eligible fields"),
            "detail": f"required={','.join(REQUIRED_DAILY_BAR_FIELDS)}; available={field_detail}; missing={missing_detail}",
        },
        {
            "item": "time_series_panel",
            "status": _status(full_panel, bool(cn_daily_rows)),
            "detail": f"complete daily_bar panel present at {panel_path}" if panel_complete else "complete daily_bars panel missing; current evidence is summary-level",
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
            "detail": next_action,
        },
    ]
    result = {
        "feasibility_status": feasibility_status,
        "qlib_runtime_ready": "yes" if qlib_ready else "no",
        "eligible_daily_bar_count": len(cn_daily_rows),
        "rows": rows,
        "warnings": feasibility.warnings,
        "missing_fields": [] if missing_detail == "none" else missing_detail.split(","),
        "panel_path": str(panel_path),
        "panel_row_count": len(panel_rows),
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
