#!/usr/bin/env python3
"""Validate the minimum AlphaSift reuse boundary without running screening."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.adapters.alphasift_adapter import (  # noqa: E402
    ALPHASIFT_DOWNSTREAM_NAMES,
    build_alphasift_input,
    can_send_to_alphasift,
)
from orchestrator.evidence.ledger import load_evidence  # noqa: E402


EVIDENCE_PATH = Path("outputs/evidence/provider_evidence.jsonl")
REPORT_PATH = Path("outputs/reports/alphasift_reuse_validation.md")
CANDIDATE_PATH = Path("outputs/candidates/candidate_evidence.jsonl")


def _default_alphasift_paths() -> list[Path]:
    paths: list[Path] = []
    env_path = os.environ.get("ALPHASIFT_PATH")
    if env_path:
        paths.append(Path(env_path))
    paths.extend([Path("vendors/alphasift"), Path("references/alphasift")])
    return paths


def _find_local_alphasift(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists() and path.is_dir():
            return path
    return None


def _read_text_if_exists(path: Path, limit: int = 6000) -> str:
    if not path.exists() or not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")[:limit]


def _inspect_local_alphasift(path: Path) -> dict[str, Any]:
    readme = _read_text_if_exists(path / "README.md")
    pyproject = _read_text_if_exists(path / "pyproject.toml")
    cli = _read_text_if_exists(path / "alphasift" / "cli.py")
    license_text = _read_text_if_exists(path / "LICENSE", limit=1200)
    no_llm_supported = "--no-llm" in readme or "--no-llm" in cli
    screen_cli_supported = "screen" in readme and "alphasift screen" in readme
    return {
        "path": str(path),
        "readme_found": bool(readme),
        "pyproject_found": bool(pyproject),
        "cli_found": bool(cli),
        "license_summary": "Apache-2.0" if "Apache License" in license_text or "Apache-2.0" in pyproject else "unknown",
        "console_script_found": "alphasift = \"alphasift.cli:main\"" in pyproject,
        "screen_cli_supported": screen_cli_supported,
        "no_llm_supported": no_llm_supported,
        "input_contract_status": (
            "needs_project_runtime_validation"
            if no_llm_supported and screen_cli_supported
            else "input_contract_unknown"
        ),
        "market_support_status": "cn_supported_likely_hk_us_unknown" if "A-share" in readme or "A股" in readme else "market_support_unknown",
    }


def _eligible_evidence(evidence_path: Path) -> list[Any]:
    rows = load_evidence(evidence_path)
    return [
        row
        for row in rows
        if row.market == "CN"
        and row.data_domain == "daily_bar"
        and bool(ALPHASIFT_DOWNSTREAM_NAMES & set(row.allowed_downstream))
        and can_send_to_alphasift(row)
    ]


def _adapter_input_preview(rows: list[Any]) -> list[dict[str, Any]]:
    preview: list[dict[str, Any]] = []
    for row in rows:
        adapter_input = build_alphasift_input(row)
        preview.append(
            {
                "run_id": adapter_input.run_id,
                "market": adapter_input.market,
                "ticker": adapter_input.ticker,
                "candidate_date": adapter_input.candidate_date,
                "provider_evidence_id": adapter_input.provider_evidence.get("evidence_id"),
                "data_domain": adapter_input.provider_evidence.get("data_domain"),
                "quality_gate_status": adapter_input.quality_gate_status,
            }
        )
    return preview


def _format_list(items: list[str]) -> str:
    if not items:
        return "- none\n"
    return "".join(f"- {item}\n" for item in items)


def _write_report(result: dict[str, Any], report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# AlphaSift Reuse Validation",
        "",
        f"- run_at: {result['run_at']}",
        f"- reuse_validation_status: {result['reuse_validation_status']}",
        f"- local_alphasift_found: {result['local_alphasift_found']}",
        f"- local_alphasift_path: {result.get('local_alphasift_path') or 'not found'}",
        f"- eligible_provider_evidence_count: {result['eligible_provider_evidence_count']}",
        f"- candidate_evidence_written: {result['candidate_evidence_written']}",
        "",
        "## Blocked Reasons",
        "",
        _format_list(result["blocked_reasons"]),
        "## Local AlphaSift Inspection",
        "",
    ]
    inspection = result.get("local_project_inspection") or {}
    if inspection:
        for key in sorted(inspection):
            lines.append(f"- {key}: {inspection[key]}")
    else:
        lines.append("- missing_repo: no ALPHASIFT_PATH, vendors/alphasift, or references/alphasift project was available")
    lines.extend(
        [
            "",
            "## adapter_input_preview",
            "",
            "| ticker | candidate_date | evidence_id | data_domain | gate_status |",
            "|---|---|---|---|---|",
        ]
    )
    for item in result["adapter_input_preview"]:
        lines.append(
            "| {ticker} | {candidate_date} | {provider_evidence_id} | {data_domain} | {quality_gate_status} |".format(
                **item
            )
        )
    if not result["adapter_input_preview"]:
        lines.append("| none | none | none | none | none |")
    lines.extend(
        [
            "",
            "## Next Required Action",
            "",
            result["next_required_action"],
            "",
            "## Boundary",
            "",
            "- This report is reuse validation evidence only.",
            "- It is not candidate discovery output.",
            "- It is not a stock recommendation, signal, confidence score, backtest, LLM output, or trading instruction.",
        ]
    )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_alphasift_reuse(
    *,
    evidence_path: str | Path = EVIDENCE_PATH,
    report_path: str | Path = REPORT_PATH,
    candidate_path: str | Path = CANDIDATE_PATH,
    local_project_paths: list[Path] | None = None,
) -> dict[str, Any]:
    evidence_path = Path(evidence_path)
    report_path = Path(report_path)
    candidate_path = Path(candidate_path)
    paths = local_project_paths if local_project_paths is not None else _default_alphasift_paths()
    local_project = _find_local_alphasift(paths)
    eligible_rows = _eligible_evidence(evidence_path)
    preview = _adapter_input_preview(eligible_rows)

    blocked_reasons: list[str] = []
    inspection: dict[str, Any] = {}
    status = "pending_external_project_validation"
    next_required_action = (
        "Provide ALPHASIFT_PATH or vendors/alphasift, then run the AlphaSift no-LLM quickstart in an isolated validation environment."
    )

    if not local_project:
        blocked_reasons.append("missing_repo")
    else:
        inspection = _inspect_local_alphasift(local_project)
        if inspection["input_contract_status"] == "input_contract_unknown":
            blocked_reasons.append("input_contract_unknown")
        if inspection["market_support_status"] == "market_support_unknown":
            blocked_reasons.append("market_support_unknown")
        if inspection["license_summary"] == "unknown":
            blocked_reasons.append("license_risk")
        status = "local_project_inspected_runtime_not_executed"
        next_required_action = (
            "Install or run the local AlphaSift project separately and execute `alphasift screen <strategy> --no-llm` only after input files are mapped from ProviderEvidence."
        )
        if not blocked_reasons:
            blocked_reasons.append("missing_runtime_validation")

    result = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "reuse_validation_status": status,
        "local_alphasift_found": bool(local_project),
        "local_alphasift_path": str(local_project) if local_project else None,
        "eligible_provider_evidence_count": len(eligible_rows),
        "adapter_input_preview": preview,
        "blocked_reasons": blocked_reasons,
        "local_project_inspection": inspection,
        "candidate_evidence_written": False,
        "candidate_path": str(candidate_path),
        "next_required_action": next_required_action,
    }
    _write_report(result, report_path)
    return result


def main() -> int:
    result = validate_alphasift_reuse()
    print(f"reuse_validation_status: {result['reuse_validation_status']}")
    print(f"local_alphasift_found: {result['local_alphasift_found']}")
    print(f"eligible_provider_evidence_count: {result['eligible_provider_evidence_count']}")
    print(f"candidate_evidence_written: {result['candidate_evidence_written']}")
    print(f"report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
