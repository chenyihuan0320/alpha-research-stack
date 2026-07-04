#!/usr/bin/env python3
"""Build a small verified CN daily_bar panel from ProviderEvidence."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.evidence.ledger import load_evidence  # noqa: E402
from orchestrator.panels.daily_bar_panel import (  # noqa: E402
    REQUIRED_PANEL_FIELDS,
    build_daily_bar_panel_from_provider_evidence,
    write_daily_bar_panel_csv,
)


EVIDENCE_PATH = Path("outputs/evidence/provider_evidence.jsonl")
OUTPUT_PATH = Path("outputs/panels/cn_daily_bar_panel.csv")
REPORT_PATH = Path("outputs/reports/verified_daily_bar_panel.md")


def _status(pass_condition: bool, warn_condition: bool = False) -> str:
    if pass_condition:
        return "pass"
    if warn_condition:
        return "warn"
    return "block"


def _write_report(result: dict[str, Any], report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Verified Daily Bar Panel",
        "",
        f"- panel_build_status: {result['panel_build_status']}",
        f"- output_path: {result['output_path']}",
        f"- row_count: {result['row_count']}",
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
            "- ProviderEvidence is a traceability ledger, not a training dataset.",
            "- The panel is built only from real daily_bars or provider fetches.",
            "- Summary evidence is not expanded into fake daily_bars.",
            "- This is not a recommendation, not a candidate, not a signal, not confidence, not LLM output, and not trading.",
        ]
    )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_verified_daily_bar_panel(
    *,
    evidence_path: str | Path = EVIDENCE_PATH,
    output_path: str | Path = OUTPUT_PATH,
    report_path: str | Path = REPORT_PATH,
    fetch_missing_time_series: bool = True,
) -> dict[str, Any]:
    evidence_rows = load_evidence(evidence_path)
    cn_daily_rows = [
        row
        for row in evidence_rows
        if row.market == "CN" and row.data_domain == "daily_bar"
    ]
    build_result, panel_rows = build_daily_bar_panel_from_provider_evidence(
        cn_daily_rows,
        output_path=output_path,
        fetch_missing_time_series=fetch_missing_time_series,
    )
    if panel_rows:
        write_daily_bar_panel_csv(panel_rows, output_path)

    field_status = "pass" if panel_rows else "block"
    cross_source_values = sorted({row.cross_source_status for row in panel_rows})
    cross_source_status = "pass" if cross_source_values == ["matched"] else ("warn" if panel_rows else "block")
    rows = [
        {
            "item": "eligible_evidence",
            "status": _status(bool(cn_daily_rows)),
            "detail": f"count={len(cn_daily_rows)}",
        },
        {
            "item": "panel_build",
            "status": build_result.status,
            "detail": "; ".join(build_result.warnings) or "built from real daily_bars",
        },
        {
            "item": "tickers",
            "status": "-",
            "detail": f"count={len(build_result.tickers)}; {', '.join(build_result.tickers) or '-'}",
        },
        {
            "item": "date_range",
            "status": "-",
            "detail": f"{build_result.start_date or '-'} to {build_result.end_date or '-'}",
        },
        {
            "item": "row_count",
            "status": "-",
            "detail": str(build_result.row_count),
        },
        {
            "item": "qlib_minimum_fields",
            "status": field_status,
            "detail": ",".join(REQUIRED_PANEL_FIELDS),
        },
        {
            "item": "cross_source_status",
            "status": cross_source_status,
            "detail": ", ".join(cross_source_values) if cross_source_values else "unavailable",
        },
        {
            "item": "next_action",
            "status": "-",
            "detail": build_result.next_action,
        },
    ]
    result = {
        "panel_build_status": build_result.status,
        "output_path": str(output_path),
        "row_count": build_result.row_count,
        "tickers": build_result.tickers,
        "warnings": build_result.warnings,
        "rows": rows,
    }
    _write_report(result, Path(report_path))
    return result


def main() -> int:
    result = build_verified_daily_bar_panel()
    print(f"panel_build_status: {result['panel_build_status']}")
    print(f"row_count: {result['row_count']}")
    print(f"output_path: {result['output_path']}")
    print(f"report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
