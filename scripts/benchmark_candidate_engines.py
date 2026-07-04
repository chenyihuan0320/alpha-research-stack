#!/usr/bin/env python3
"""Generate a candidate engine benchmark design report without running engines."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.candidates.engine import compare_candidate_engines  # noqa: E402
from orchestrator.candidates.engine_registry import get_candidate_engine  # noqa: E402
from orchestrator.evidence.ledger import load_evidence  # noqa: E402
from orchestrator.adapters.qlib_adapter import evaluate_qlib_data_format_feasibility  # noqa: E402
from orchestrator.panels.daily_bar_panel import (  # noqa: E402
    REQUIRED_PANEL_FIELDS,
    load_daily_bar_panel_csv,
)


EVIDENCE_PATH = Path("outputs/evidence/provider_evidence.jsonl")
PANEL_PATH = Path("outputs/panels/cn_daily_bar_panel.csv")
QLIB_RUNTIME_REPORT_PATH = Path("outputs/reports/qlib_runtime_read_validation.md")
REPORT_PATH = Path("outputs/reports/candidate_engine_benchmark.md")
BENCHMARK_ENGINE_NAMES = ["alphasift", "qlib", "vectorbt_event_baseline"]


def _allowed_evidence(rows: list[Any]) -> list[Any]:
    return [row for row in rows if row.allowed_downstream]


def _supported_inputs(engine_name: str) -> str:
    engine = get_candidate_engine(engine_name)
    return ", ".join(engine.required_inputs)


def _panel_is_qlib_ready(panel_path: str | Path) -> bool:
    panel_rows = load_daily_bar_panel_csv(panel_path)
    if not panel_rows:
        return False
    if len({row.ticker for row in panel_rows}) < 2 or len({row.date for row in panel_rows}) < 2:
        return False
    for row in panel_rows:
        payload = row.to_dict()
        if any(payload.get(field) in (None, "") for field in REQUIRED_PANEL_FIELDS):
            return False
    return True


def _extract_runtime_read_status(report_path: str | Path) -> str | None:
    path = Path(report_path)
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("| qlib_runtime_read |"):
            parts = [part.strip() for part in line.strip("|").split("|")]
            if len(parts) >= 2:
                return parts[1]
    return None


def _qlib_status_and_blocker(
    allowed_rows: list[Any],
    panel_path: str | Path,
    runtime_report_path: str | Path,
) -> tuple[str, str, str]:
    use_default_runtime_report = (
        Path(panel_path) == PANEL_PATH
        and Path(runtime_report_path) == QLIB_RUNTIME_REPORT_PATH
    )
    runtime_status = (
        _extract_runtime_read_status(runtime_report_path)
        if use_default_runtime_report or Path(runtime_report_path) != QLIB_RUNTIME_REPORT_PATH
        else None
    )
    if runtime_status == "success":
        return (
            "ready_for_minimal_experiment_design",
            "Qlib runtime read validation succeeded; no model training or backtest executed.",
            "Design Qlib minimal experiment input without training models.",
        )
    if runtime_status == "dependency_missing":
        return (
            "dependency_missing_panel_ready",
            "Qlib dependency missing, but verified daily_bar panel is readable.",
            "Install Qlib only if approved, then rerun runtime read validation.",
        )
    if runtime_status == "format_error":
        return (
            "blocked_by_runtime_format",
            "Qlib runtime read validation found a panel format error.",
            "Fix DailyBarPanel schema before Qlib runtime validation.",
        )
    if _panel_is_qlib_ready(panel_path):
        return (
            "ready_for_runtime_validation",
            "Qlib-compatible daily_bar panel fields are present; runtime still not executed.",
            "Run Qlib minimal runtime validation without model training.",
        )
    feasibility = evaluate_qlib_data_format_feasibility(allowed_rows)
    if feasibility.status == "feasible":
        return (
            "ready_for_runtime_validation",
            "Qlib-compatible daily_bar panel fields are present; runtime still not executed.",
            "Run Qlib minimal runtime validation without model training.",
        )
    if "time_series_panel_missing" in feasibility.warnings:
        return (
            "blocked_by_panel_data",
            "Qlib requires panel daily_bars; current ProviderEvidence is summary-level.",
            "Build verified daily_bar panel before Qlib runtime validation.",
        )
    return (
        "blocked_by_panel_data",
        "Qlib data format feasibility is blocked by missing required fields or eligible evidence.",
        feasibility.next_action,
    )


def _write_report(result: dict[str, Any], report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Candidate Engine Benchmark",
        "",
        f"- run_id: {result['run_id']}",
        f"- generated_at: {result['generated_at']}",
        f"- allowed_evidence_count: {result['allowed_evidence_count']}",
        "",
        "This benchmark does not run AlphaSift, Qlib, vectorbt, LLMs, or trading workflows.",
        "",
        "| engine | role | status | supported_inputs | expected_output | integration_cost | accuracy_potential | current_blocker | next_action |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for row in result["rows"]:
        lines.append(
            "| {engine} | {role} | {status} | {supported_inputs} | {expected_output} | {integration_cost} | {accuracy_potential} | {current_blocker} | {next_action} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- Not run by this benchmark.",
            "- Does not generate CandidateEvidence.",
            "- Does not execute candidate discovery.",
            "- Does not execute validation or backtesting.",
            "- Does not use LLMs.",
            "- Does not provide investment advice or trading instructions.",
        ]
    )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def benchmark_candidate_engines(
    *,
    evidence_path: str | Path = EVIDENCE_PATH,
    panel_path: str | Path = PANEL_PATH,
    qlib_runtime_report_path: str | Path = QLIB_RUNTIME_REPORT_PATH,
    report_path: str | Path = REPORT_PATH,
) -> dict[str, Any]:
    evidence_rows = load_evidence(evidence_path)
    allowed_rows = _allowed_evidence(evidence_rows)
    benchmark = compare_candidate_engines(
        engine_names=BENCHMARK_ENGINE_NAMES,
        evidence_rows=allowed_rows,
    )
    rows: list[dict[str, str]] = []
    for readiness in benchmark.results:
        engine = get_candidate_engine(readiness.engine_name)
        status = readiness.status
        blocker = engine.current_blocker
        next_action = readiness.next_action
        if engine.engine_name == "qlib":
            status, blocker, next_action = _qlib_status_and_blocker(
                allowed_rows,
                panel_path,
                qlib_runtime_report_path,
            )
        rows.append(
            {
                "engine": engine.engine_name,
                "role": engine.role,
                "status": status,
                "supported_inputs": _supported_inputs(engine.engine_name),
                "expected_output": readiness.output_contract,
                "integration_cost": engine.integration_cost,
                "accuracy_potential": engine.accuracy_potential,
                "current_blocker": blocker,
                "next_action": next_action,
            }
        )
    result = {
        "run_id": benchmark.run_id,
        "generated_at": benchmark.generated_at,
        "engine_count": len(rows),
        "allowed_evidence_count": len(allowed_rows),
        "rows": rows,
    }
    _write_report(result, Path(report_path))
    return result


def main() -> int:
    result = benchmark_candidate_engines()
    print(f"engine_count: {result['engine_count']}")
    print(f"allowed_evidence_count: {result['allowed_evidence_count']}")
    print(f"report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
