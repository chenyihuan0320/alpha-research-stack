#!/usr/bin/env python3
"""Run AlphaSift no-LLM runtime validation against ProviderEvidence inputs."""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.adapters.alphasift_adapter import ALPHASIFT_DOWNSTREAM_NAMES  # noqa: E402
from orchestrator.candidates.ledger import append_candidate  # noqa: E402
from orchestrator.candidates.models import CandidateEvidence  # noqa: E402
from orchestrator.evidence.ledger import load_evidence  # noqa: E402
from orchestrator.evidence.models import ProviderEvidence  # noqa: E402


EVIDENCE_PATH = Path("outputs/evidence/provider_evidence.jsonl")
RUNTIME_DIR = Path("outputs/alphasift_runtime")
REPORT_PATH = Path("outputs/reports/alphasift_runtime_validation.md")
CANDIDATE_PATH = Path("outputs/candidates/candidate_evidence.jsonl")
STRATEGY_NAME = "ars_provider_evidence"


@dataclass(slots=True)
class CommandResult:
    exit_code: int
    stdout: str
    stderr: str


CommandRunner = Callable[..., CommandResult]


def _default_alphasift_paths() -> list[Path]:
    paths: list[Path] = []
    env_path = os.environ.get("ALPHASIFT_PATH")
    if env_path:
        paths.append(Path(env_path))
    paths.extend([Path("references/alphasift"), Path("vendors/alphasift")])
    return paths


def _find_local_alphasift(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists() and path.is_dir():
            return path
    return None


def _cli_path(alphasift_path: Path) -> Path:
    return alphasift_path / "alphasift" / "cli.py"


def _ensure_runtime_dirs(runtime_dir: Path) -> dict[str, Path]:
    dirs = {
        "root": runtime_dir,
        "input": runtime_dir / "input",
        "output": runtime_dir / "output",
        "logs": runtime_dir / "logs",
    }
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs


def _eligible_evidence(evidence_path: Path) -> list[ProviderEvidence]:
    return [
        row
        for row in load_evidence(evidence_path)
        if row.market == "CN"
        and row.data_domain == "daily_bar"
        and bool(ALPHASIFT_DOWNSTREAM_NAMES & set(row.allowed_downstream))
    ]


def _ticker_code(ticker: str) -> str:
    return ticker.split(".", 1)[0].strip()


def _write_input_files(rows: list[ProviderEvidence], input_dir: Path) -> dict[str, Path]:
    universe_path = input_dir / "universe.csv"
    mapping_path = input_dir / "provider_evidence_mapping.json"
    strategy_path = input_dir / f"{STRATEGY_NAME}.yaml"

    with universe_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["market", "ticker", "code", "provider_evidence_id"])
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "market": row.market,
                    "ticker": row.ticker,
                    "code": _ticker_code(row.ticker),
                    "provider_evidence_id": row.evidence_id,
                }
            )

    mapping_payload = {
        row.ticker: {
            "evidence_id": row.evidence_id,
            "run_id": row.run_id,
            "market": row.market,
            "ticker": row.ticker,
            "data_domain": row.data_domain,
            "quality_flags": list(row.quality_flags),
            "gate_status": row.gate_status,
            "allowed_downstream": list(row.allowed_downstream),
        }
        for row in rows
    }
    mapping_path.write_text(json.dumps(mapping_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    strategy_path.write_text(
        """name: ars_provider_evidence
display_name: ARS Provider Evidence Runtime Validation
description: Runtime validation strategy generated from ProviderEvidence; not a recommendation.
version: "0.1"
category: validation
tags: [runtime_validation, no_llm]
style:
  risk_profile: exploratory
  holding_period: watchlist
  execution_style: validation
screening:
  enabled: true
  market_scope: [cn]
  hard_filters:
    exclude_st: true
    amount_min: 0
    price_min: 0
  tech_weight: 0.0
  factor_weights:
    activity: 1.0
  ranking_hints: "Runtime validation only. Do not treat output as recommendation."
  max_output: 3
""",
        encoding="utf-8",
    )
    return {
        "universe": universe_path,
        "provider_evidence_mapping": mapping_path,
        "strategy": strategy_path,
    }


def _build_command(alphasift_path: Path, dirs: dict[str, Path]) -> list[str]:
    output_path = dirs["output"] / "alphasift_screen.jsonl"
    return [
        sys.executable,
        "-m",
        "alphasift.cli",
        "screen",
        STRATEGY_NAME,
        "--market",
        "cn",
        "--max-output",
        "3",
        "--no-llm",
        "--no-post-analysis",
        "--no-daily-enrich",
        "--output",
        str(output_path),
        "--jsonl",
    ]


def _runtime_env(alphasift_path: Path, dirs: dict[str, Path]) -> dict[str, str]:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(alphasift_path) if not existing_pythonpath else f"{alphasift_path}{os.pathsep}{existing_pythonpath}"
    env["ALPHASIFT_DATA_DIR"] = str(dirs["output"] / "data")
    env["STRATEGIES_DIR"] = str(dirs["input"])
    env["POST_ANALYZERS"] = ""
    env["DAILY_ENRICH_ENABLED"] = "false"
    env["LLM_CANDIDATE_CONTEXT_ENABLED"] = "false"
    return env


def _default_command_runner(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    stdout_path: Path,
    stderr_path: Path,
) -> CommandResult:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)


def _classify_failure(command_result: CommandResult) -> tuple[str, str]:
    combined = "\n".join([command_result.stdout, command_result.stderr]).strip()
    summary = " ".join(combined.split())[:800]
    lowered = combined.lower()
    if "modulenotfounderror" in lowered or "no module named" in lowered:
        return "dependency_missing", summary
    if "unknown strategy" in lowered or "invalid strategy" in lowered or "strategy not found" in lowered:
        return "input_contract_mismatch", summary
    return "failed", summary


def _load_jsonl(path: Path) -> tuple[list[dict[str, Any]], str | None]:
    if not path.exists():
        return [], "raw_output_missing"
    rows: list[dict[str, Any]] = []
    try:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                item = json.loads(line)
                if isinstance(item, dict):
                    rows.append(item)
    except Exception as exc:
        return [], f"parse_failed:{exc}"
    return rows, None


def _score_from_payload(payload: dict[str, Any]) -> float | None:
    for key in ("candidate_score", "score", "final_score"):
        value = payload.get(key)
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                continue
    return None


def _reasons_from_payload(payload: dict[str, Any]) -> list[str]:
    reasons = payload.get("reasons")
    if isinstance(reasons, list) and reasons:
        return [str(item) for item in reasons]
    for key in ("reason", "explanation", "thesis"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return [value.strip()]
    return ["runtime_candidate_without_reason"]


def _direction_from_payload(payload: dict[str, Any]) -> str:
    value = str(payload.get("candidate_direction") or payload.get("direction") or payload.get("side") or "unknown")
    return value if value in {"long", "short"} else "unknown"


def _map_candidates(
    *,
    rows: list[dict[str, Any]],
    evidence_rows: list[ProviderEvidence],
    candidate_path: Path,
) -> tuple[int, list[str]]:
    evidence_by_code = {_ticker_code(row.ticker): row for row in evidence_rows}
    written = 0
    warnings: list[str] = []
    for payload in rows:
        if payload.get("type") != "pick":
            continue
        code = str(payload.get("ticker") or payload.get("code") or "").split(".", 1)[0].strip()
        evidence = evidence_by_code.get(code)
        if evidence is None:
            warnings.append(f"unmatched_candidate:{code or 'unknown'}")
            continue
        run_id = str(payload.get("run_id") or evidence.run_id)
        candidate = CandidateEvidence(
            candidate_id=f"alphasift-runtime:{run_id}:{evidence.ticker}",
            run_id=run_id,
            market=evidence.market,
            ticker=evidence.ticker,
            candidate_date=evidence.observed_at.date().isoformat(),
            candidate_source="alphasift",
            candidate_direction=_direction_from_payload(payload),
            candidate_score=_score_from_payload(payload),
            reasons=_reasons_from_payload(payload),
            provider_evidence_ids=[evidence.evidence_id],
            provider_evidence_domains=["daily_bar"],
            quality_flags=list(evidence.quality_flags),
            raw_payload=dict(payload),
            gate_status="warn",
            allowed_next_steps=["research", "vectorbt_validation"],
            notes="CandidateEvidence only; not a signal or recommendation.",
        )
        if candidate.reasons == ["runtime_candidate_without_reason"]:
            candidate.quality_flags.append("runtime_candidate_without_reason")
        append_candidate(candidate, candidate_path)
        written += 1
    return written, warnings


def _output_files(output_dir: Path) -> list[str]:
    if not output_dir.exists():
        return []
    return sorted(str(path) for path in output_dir.rglob("*") if path.is_file())


def _write_report(result: dict[str, Any], report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# AlphaSift Runtime Validation",
        "",
        f"- run_at: {result['run_at']}",
        f"- runtime_status: {result['runtime_status']}",
        f"- alphasift_path: {result.get('alphasift_path') or 'not found'}",
        f"- command_attempted: `{result.get('command_attempted') or 'none'}`",
        f"- exit_code: {result.get('exit_code')}",
        f"- stdout_path: {result.get('stdout_path')}",
        f"- stderr_path: {result.get('stderr_path')}",
        f"- raw_output_path: {result.get('raw_output_path')}",
        f"- candidate_evidence_written: {result['candidate_evidence_written']}",
        f"- candidates_written_count: {result['candidates_written_count']}",
        "",
        "## Input Files Generated",
        "",
    ]
    for label, path in result["input_files_generated"].items():
        lines.append(f"- {label}: {path}")
    if not result["input_files_generated"]:
        lines.append("- none")
    lines.extend(["", "## Output Files Detected", ""])
    for path in result["output_files_detected"]:
        lines.append(f"- {path}")
    if not result["output_files_detected"]:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Error Summary",
            "",
            result.get("error_summary") or "none",
            "",
            "## Parse Warnings",
            "",
        ]
    )
    for item in result["parse_warnings"]:
        lines.append(f"- {item}")
    if not result["parse_warnings"]:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- This is runtime reuse validation only.",
            "- It is not a stock recommendation.",
            "- It is not a final signal.",
            "- It does not produce final confidence.",
            "- It is not a backtest.",
            "- It does not use LLM ranking.",
            "- It is not automated trading.",
        ]
    )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_alphasift_no_llm_validation(
    *,
    evidence_path: str | Path = EVIDENCE_PATH,
    runtime_dir: str | Path = RUNTIME_DIR,
    report_path: str | Path = REPORT_PATH,
    candidate_path: str | Path = CANDIDATE_PATH,
    local_project_paths: list[Path] | None = None,
    command_runner: CommandRunner = _default_command_runner,
    execute_command: bool = True,
) -> dict[str, Any]:
    evidence_path = Path(evidence_path)
    runtime_dir = Path(runtime_dir)
    report_path = Path(report_path)
    candidate_path = Path(candidate_path)
    dirs = _ensure_runtime_dirs(runtime_dir)
    evidence_rows = _eligible_evidence(evidence_path)
    input_files = _write_input_files(evidence_rows, dirs["input"])
    local_project = _find_local_alphasift(local_project_paths or _default_alphasift_paths())

    result: dict[str, Any] = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "runtime_status": "failed",
        "alphasift_path": str(local_project) if local_project else None,
        "command_attempted": "",
        "exit_code": None,
        "stdout_path": str(dirs["logs"] / "alphasift_stdout.log"),
        "stderr_path": str(dirs["logs"] / "alphasift_stderr.log"),
        "raw_output_path": str(dirs["output"] / "alphasift_screen.jsonl"),
        "input_files_generated": {key: str(value) for key, value in input_files.items()},
        "output_files_detected": [],
        "error_summary": "",
        "parse_warnings": [],
        "candidate_evidence_written": False,
        "candidates_written_count": 0,
    }

    if local_project is None:
        result["runtime_status"] = "missing_repo"
        result["error_summary"] = "missing_repo: no ALPHASIFT_PATH, references/alphasift, or vendors/alphasift project found"
        _write_report(result, report_path)
        return result

    if not _cli_path(local_project).is_file():
        result["runtime_status"] = "cli_not_found"
        result["error_summary"] = f"cli_not_found: {_cli_path(local_project)}"
        _write_report(result, report_path)
        return result

    command = _build_command(local_project, dirs)
    result["command_attempted"] = " ".join(command)
    if not execute_command:
        result["runtime_status"] = "failed"
        result["error_summary"] = "runtime execution disabled by caller"
        _write_report(result, report_path)
        return result

    stdout_path = dirs["logs"] / "alphasift_stdout.log"
    stderr_path = dirs["logs"] / "alphasift_stderr.log"
    command_result = command_runner(
        command,
        cwd=local_project,
        env=_runtime_env(local_project, dirs),
        stdout_path=stdout_path,
        stderr_path=stderr_path,
    )
    result["exit_code"] = command_result.exit_code
    output_path = dirs["output"] / "alphasift_screen.jsonl"
    result["output_files_detected"] = _output_files(dirs["output"])

    if command_result.exit_code != 0:
        status, summary = _classify_failure(command_result)
        result["runtime_status"] = status
        result["error_summary"] = summary
        _write_report(result, report_path)
        return result

    raw_rows, parse_error = _load_jsonl(output_path)
    if parse_error is not None:
        result["runtime_status"] = "parse_failed"
        result["error_summary"] = parse_error
        _write_report(result, report_path)
        return result

    written, warnings = _map_candidates(
        rows=raw_rows,
        evidence_rows=evidence_rows,
        candidate_path=candidate_path,
    )
    result["parse_warnings"] = warnings
    result["candidates_written_count"] = written
    result["candidate_evidence_written"] = written > 0
    if written > 0:
        result["runtime_status"] = "success"
    else:
        result["runtime_status"] = "input_contract_mismatch"
        result["error_summary"] = "AlphaSift output parsed, but no pick matched ProviderEvidence tickers."
    _write_report(result, report_path)
    return result


def main() -> int:
    result = run_alphasift_no_llm_validation()
    print(f"runtime_status: {result['runtime_status']}")
    print(f"candidate_evidence_written: {result['candidate_evidence_written']}")
    print(f"candidates_written_count: {result['candidates_written_count']}")
    print(f"report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
