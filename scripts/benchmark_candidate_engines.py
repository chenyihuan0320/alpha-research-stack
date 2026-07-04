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


EVIDENCE_PATH = Path("outputs/evidence/provider_evidence.jsonl")
REPORT_PATH = Path("outputs/reports/candidate_engine_benchmark.md")
BENCHMARK_ENGINE_NAMES = ["alphasift", "qlib", "vectorbt_event_baseline"]


def _allowed_evidence(rows: list[Any]) -> list[Any]:
    return [row for row in rows if row.allowed_downstream]


def _supported_inputs(engine_name: str) -> str:
    engine = get_candidate_engine(engine_name)
    return ", ".join(engine.required_inputs)


def _qlib_status_and_blocker(allowed_rows: list[Any]) -> tuple[str, str, str]:
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
            status, blocker, next_action = _qlib_status_and_blocker(allowed_rows)
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
